//! The provider router: Flock's multi-provider remote API/completions
//! subsystem, absorbing AstMatrix and nim-proxy behind Herd `:25100`.
//!
//! One [`ProviderRuntime`] per provider. Each runtime owns exactly the
//! machinery the old single-upstream proxy had — a [`Pool`] of key lanes
//! with 61-second sliding windows, a per-pool FIFO [`Dispatcher`] with 25 ms
//! grant spacing, and a model-pressure [`Governor`] — so NVIDIA's exact lane,
//! FIFO, and governor semantics are preserved while generalizing ownership
//! per provider. Nothing here is an alias, wrapper, or shim: the router
//! *is* the request path's provider layer.
//!
//! Strategy selection ports AstMatrix's eight strategies with two deliberate
//! corrections (documented in `MIGRATION.md`): every strategy consults the
//! circuit breaker (AstMatrix's race path bypassed it), and only genuinely
//! retryable failures (429/5xx, never 4xx) count against a provider.

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::{
    atomic::{AtomicBool, AtomicU64, Ordering},
    Arc, Mutex, RwLock,
};
use std::time::{Duration, Instant};

use bytes::Bytes;
use metrics::{counter, gauge};
use rand::Rng;

use crate::circuit::{CircuitBreaker, CircuitSnapshot, CircuitState};
use crate::coalescer::Coalescer;
use crate::config::StoredConfig;
use crate::dispatch::Dispatcher;
use crate::governor::{self, Governor, ModelPermit};
use crate::health::{
    self, HealthDb, LaneWindowRow, PersistHandle, PersistOp, ProviderHealthView, RestoredRuntime,
    StateWriter,
};
use crate::pool::{Pool, PoolHandle};
use crate::providers::{ProviderDef, RoutingCfg, Strategy, COALESCER_TTL};
use crate::ratelimit::ProviderRateLimiter;
use crate::unix_now;

/// How often the persistence loop flushes runtime state to SQLite.
const PERSIST_INTERVAL: Duration = Duration::from_secs(30);
/// How often the probe loop samples each usable provider's `/v1/models`.
const PROBE_INTERVAL_FALLBACK: Duration = Duration::from_secs(300);

/// One provider's full serving runtime: definition, key pool, FIFO
/// dispatcher, model governor, circuit breaker, coalescer, and caches.
pub struct ProviderRuntime {
    /// Provider definition; swapped on settings rebuild.
    pub def: RwLock<ProviderDef>,
    /// Key pool: 61 s sliding windows, sticky preference, least-loaded
    /// spillover, cooldown on 429/5xx, disabled state-carrier lanes.
    pub pool: PoolHandle,
    /// Per-pool FIFO dispatcher, 25 ms grant spacing.
    pub dispatcher: Dispatcher,
    /// Model-pressure governor (worker-concurrency, not RPM).
    pub governor: Arc<Governor>,
    /// Circuit breaker (5 failures / 30 s / 3 half-open successes).
    pub circuit: Mutex<CircuitBreaker>,
    /// Buffered-request coalescer (5 s TTL).
    pub coalescer: Coalescer,
    /// `/v1/models` cache for this provider's upstream.
    pub models_cache: Mutex<Option<(Instant, Bytes)>>,
    /// Routing counters.
    pub metrics: ProviderMetrics,
}

#[derive(Default)]
pub struct ProviderMetrics {
    pub requests: AtomicU64,
    pub errors: AtomicU64,
    pub retries: AtomicU64,
    pub coalesced: AtomicU64,
    pub rate_limited: AtomicU64,
    pub circuit_rejected: AtomicU64,
}

impl ProviderRuntime {
    fn build(def: ProviderDef) -> Arc<Self> {
        let pool: PoolHandle = Arc::new(RwLock::new(Arc::new(Pool::new(def.lane_specs()))));
        let dispatcher = Dispatcher::new(pool.clone());
        Arc::new(Self {
            def: RwLock::new(def),
            pool,
            dispatcher,
            governor: Arc::new(Governor::default()),
            circuit: Mutex::new(CircuitBreaker::astmatrix_defaults()),
            coalescer: Coalescer::new(COALESCER_TTL),
            models_cache: Mutex::new(None),
            metrics: ProviderMetrics::default(),
        })
    }

    pub fn name(&self) -> String {
        self.def.read().unwrap().name.clone()
    }

    /// Restore persisted runtime state after a restart: circuit, lane
    /// windows, cooldowns, and per-model governor snapshots.
    fn restore(&self, rt: &RestoredRuntime, now_unix: u64) {
        let name = self.name();
        if let Some(snap) = rt.circuits.get(&name) {
            *self.circuit.lock().unwrap() = CircuitBreaker::restore(*snap, now_unix);
        }
        if let Some(rows) = rt.lane_windows.get(&name) {
            let pool = self.pool.read().unwrap();
            for row in rows {
                pool.restore_lane_window(&row.key, &row.sent_ms, now_unix);
            }
        }
        for ((p, key), until_ms) in &rt.cooldowns {
            if *p == name {
                self.pool
                    .read()
                    .unwrap()
                    .restore_cooldown(key, *until_ms, now_unix);
            }
        }
        for ((p, model), snap) in &rt.governors {
            if *p == name {
                self.governor.restore(model, *snap);
            }
        }
    }

    /// Snapshot runtime state for the persistence loop.
    fn snapshot(&self, now_unix: u64) -> RuntimeSnapshot {
        let name = self.name();
        let pool = self.pool.read().unwrap();
        let lanes: Vec<LaneWindowRow> = pool
            .lane_window_rows(now_unix)
            .into_iter()
            .map(|(key, sent_ms)| LaneWindowRow { key, sent_ms })
            .collect();
        let cooldowns: Vec<(String, u64)> = pool.cooldown_rows(now_unix);
        let governors: Vec<(String, crate::governor::GovernorSnapshot)> = self.governor.snapshots();
        RuntimeSnapshot {
            provider: name,
            circuit: self.circuit.lock().unwrap().snapshot(),
            lanes,
            cooldowns,
            governors,
        }
    }

    /// Rebuild this runtime from a new definition, carrying rate state over
    /// via [`Pool::rebuild`] (a kept key can never be double-spent across a
    /// settings swap; a lowered rpm is honored immediately).
    fn reconfigure(&self, def: ProviderDef) {
        let specs = def.lane_specs();
        {
            let mut guard = self.pool.write().unwrap();
            let next = guard.rebuild(specs);
            *guard = Arc::new(next);
        }
        *self.def.write().unwrap() = def;
    }
}

struct RuntimeSnapshot {
    provider: String,
    circuit: CircuitSnapshot,
    lanes: Vec<LaneWindowRow>,
    cooldowns: Vec<(String, u64)>,
    governors: Vec<(String, crate::governor::GovernorSnapshot)>,
}

struct RouterInner {
    runtimes: RwLock<HashMap<String, Arc<ProviderRuntime>>>,
    /// Config order; the default strategy walks it.
    order: RwLock<Vec<String>>,
    health: HealthDb,
    persist: PersistHandle,
    limiter: Mutex<ProviderRateLimiter>,
    routing: RwLock<RoutingCfg>,
    governor_overrides: RwLock<std::collections::BTreeMap<String, usize>>,
    governor_enabled: AtomicBool,
    client: reqwest::Client,
    data_dir: PathBuf,
    /// Owns the SQLite writer thread. `None` in unit tests (persistence
    /// disabled); the persist handle is separately `PersistHandle::disabled`.
    _writer: Option<StateWriter>,
    /// Empty-completion strikes per (provider, model): incremented when a
    /// 2xx chat completion arrives with no content and no tool calls.
    /// Entries decay after EMPTY_STRIKE_DECAY; surfaced on /metrics.
    empty_strikes: Mutex<HashMap<(String, String), (u32, Instant)>>,
}

/// The router: cloneable handle to the multi-provider subsystem.
#[derive(Clone)]
pub struct RouterHandle {
    inner: Arc<RouterInner>,
}

/// A routing failure the proxy turns into an HTTP status.
#[derive(Debug)]
pub enum RouteError {
    /// No provider could serve: every candidate failed or was gated.
    Unavailable(String),
    /// A provider was chosen but its token bucket was dry.
    RateLimited(String),
    /// The request waited past its deadline for a slot or permit.
    Deadline,
    /// The client went away while queued.
    ClientGone,
}

/// One selected attempt: the provider, the upstream model id (after
/// `model_map` rewrite), and the strategy that chose it.
#[derive(Debug, Clone)]
pub struct RouteCandidate {
    pub provider: String,
    pub model: String,
    pub strategy: Strategy,
}

/// A fully acquired attempt: gates passed, governor permit held (when the
/// path is gated), dispatcher slot granted. The proxy sends the upstream
/// request with `slot.key` as the bearer, then calls
/// [`RouterHandle::finish_success`] or [`RouterHandle::finish_failure`].
pub struct Acquired {
    pub provider: String,
    pub model: String,
    pub base_url: String,
    pub strategy: Strategy,
    pub slot: crate::dispatch::Slot,
    pub permit: Option<ModelPermit>,
    pub attempt_started: Instant,
    /// Session identity for sticky affinity; written on success.
    pub session: Option<String>,
}

/// True for chat-completion request paths (query string included): the
/// only paths the empty-completion substance guard inspects.
fn is_chat_completions_path(path_query: &str) -> bool {
    let path = path_query.split(['?', '#']).next().unwrap_or(path_query);
    path == "/v1/chat/completions" || path.ends_with("/chat/completions")
}

/// Live per-provider metadata for the /v1/models catalog enrichment.
pub struct ProviderMeta {
    pub provider: String,
    pub display_name: String,
    pub usable: bool,
    pub healthy: bool,
    pub latency_ms: Option<f64>,
    pub elo: i32,
    pub circuit: &'static str,
    pub models: Vec<String>,
}

impl RouterHandle {
    /// Build the router from a validated store: restore persisted state,
    /// run the one-time AstMatrix import when the state DB is fresh, build
    /// one runtime per enabled provider, and spawn the probe and persistence
    /// loops.
    pub fn build(stored: &StoredConfig, data_dir: &Path) -> Result<Self, String> {
        let now_unix = unix_now();
        let state_path = health::state_db_path(data_dir);
        if !state_path.exists() {
            // One-time import: a fresh state DB means this host ran AstMatrix
            // before. Import its provider/model health, latency, strikes and
            // session affinity. Credentials are never copied — the import
            // reads health tables only.
            let src = health::astmatrix_db_default();
            if src.exists() {
                match health::import_astmatrix(
                    &src,
                    data_dir,
                    now_unix,
                    stored.routing.sticky_ttl_secs,
                ) {
                    Ok(report) => tracing::info!(
                        provider_rows = report.provider_rows,
                        sticky_rows = report.sticky_rows,
                        model_rows = report.model_rows,
                        affinity_rows = report.affinity_rows,
                        affinity_stale = report.affinity_stale,
                        extra_tables = ?report.extra_tables,
                        "imported AstMatrix health state"
                    ),
                    Err(e) => tracing::warn!("AstMatrix import failed ({e}); starting clean"),
                }
            }
        }
        let (restored_providers, restored_runtime) = health::restore(data_dir, now_unix)?;
        let writer = health::spawn_writer(data_dir)?;
        let persist = writer.handle().clone();
        let health = HealthDb::new(persist.clone());
        health.apply_restored(&restored_providers);

        let mut runtimes = HashMap::new();
        let mut order = Vec::new();
        for def in stored.providers.iter().filter(|p| p.enabled) {
            let rt = ProviderRuntime::build(def.clone());
            rt.restore(&restored_runtime, now_unix);
            order.push(def.name.clone());
            runtimes.insert(def.name.clone(), rt);
        }

        let limiter = ProviderRateLimiter::build(&stored.providers);
        let inner = Arc::new(RouterInner {
            runtimes: RwLock::new(runtimes),
            order: RwLock::new(order),
            health,
            persist,
            limiter: Mutex::new(limiter),
            routing: RwLock::new(stored.routing.clone()),
            governor_overrides: RwLock::new(stored.governor.overrides.clone()),
            governor_enabled: AtomicBool::new(stored.governor.enabled),
            client: reqwest::Client::builder()
                .timeout(Duration::from_secs(15))
                .build()
                .map_err(|e| format!("cannot build HTTP client: {e}"))?,
            data_dir: data_dir.to_path_buf(),
            _writer: Some(writer),
            empty_strikes: Mutex::new(HashMap::new()),
        });
        let handle = Self { inner };
        handle.spawn_probe_loop();
        handle.spawn_persist_loop();
        Ok(handle)
    }

    /// Apply a new validated store: add/remove/reconfigure provider runtimes
    /// with rate-state carryover, and refresh routing + governor knobs.
    pub fn rebuild(&self, stored: &StoredConfig) {
        let mut runtimes = self.inner.runtimes.write().unwrap();
        let mut order = self.inner.order.write().unwrap();
        // Remove runtimes for providers that are gone or disabled.
        runtimes.retain(|name, _| {
            stored
                .providers
                .iter()
                .any(|p| &p.name == name && p.enabled)
        });
        // Reconfigure survivors, add newcomers.
        for def in stored.providers.iter().filter(|p| p.enabled) {
            match runtimes.get(&def.name) {
                Some(rt) => rt.reconfigure(def.clone()),
                None => {
                    runtimes.insert(def.name.clone(), ProviderRuntime::build(def.clone()));
                }
            }
        }
        *order = stored
            .providers
            .iter()
            .filter(|p| p.enabled)
            .map(|p| p.name.clone())
            .collect();
        drop(order);
        drop(runtimes);
        *self.inner.limiter.lock().unwrap() = ProviderRateLimiter::build(&stored.providers);
        *self.inner.routing.write().unwrap() = stored.routing.clone();
        *self.inner.governor_overrides.write().unwrap() = stored.governor.overrides.clone();
        self.inner
            .governor_enabled
            .store(stored.governor.enabled, Ordering::SeqCst);
    }

    pub fn runtime(&self, provider: &str) -> Option<Arc<ProviderRuntime>> {
        self.inner.runtimes.read().unwrap().get(provider).cloned()
    }

    pub fn provider_names(&self) -> Vec<String> {
        self.inner.order.read().unwrap().clone()
    }

    pub fn routing_config(&self) -> RoutingCfg {
        self.inner.routing.read().unwrap().clone()
    }

    /// Operator view: every known provider with definition, health, latency,
    /// ELO, circuit state, and routing counters.
    pub fn provider_views(&self) -> Vec<ProviderView> {
        let runtimes = self.inner.runtimes.read().unwrap();
        let health_rows: HashMap<String, ProviderHealthView> = self
            .inner
            .health
            .snapshot()
            .into_iter()
            .map(|v| (v.provider.clone(), v))
            .collect();
        let mut views: Vec<ProviderView> = runtimes
            .values()
            .map(|rt| {
                let def = rt.def.read().unwrap().clone();
                let hv = health_rows.get(&def.name);
                ProviderView {
                    name: def.name.clone(),
                    display_name: def.display_name.clone(),
                    base_url: def.base_url.clone(),
                    enabled: def.enabled,
                    usable: def.usable(),
                    healthy: hv.map(|v| v.healthy).unwrap_or(true),
                    latency_ms: hv.and_then(|v| v.latency_ms),
                    elo: hv.map(|v| v.elo).unwrap_or(1500),
                    circuit: rt.circuit.lock().unwrap().state(),
                    models: def.models.clone(),
                    free: def.free_tier,
                    weight: def.weight,
                    requests: rt.metrics.requests.load(Ordering::Relaxed),
                    errors: rt.metrics.errors.load(Ordering::Relaxed),
                    pool_lanes: rt.pool.read().unwrap().len(),
                    pool_capacity_rpm: rt.pool.read().unwrap().capacity_rpm(),
                }
            })
            .collect();
        views.sort_by(|a, b| a.name.cmp(&b.name));
        views
    }

    /// Strategy selection: order the usable, healthy, circuit-allowing
    /// providers for `model` according to `strategy` (or the configured
    /// default). The session key (usually the client credential identity)
    /// drives sticky affinity.
    pub fn select(
        &self,
        model: &str,
        session: &str,
        strategy_override: Option<Strategy>,
    ) -> Vec<RouteCandidate> {
        let strategy = strategy_override.unwrap_or_else(|| self.routing_config().strategy);
        let now_unix = unix_now();
        // Sticky sessions always win when the pinned provider is still
        // usable: this is AstMatrix's sticky_affinity contract (its shipped
        // code looked the sticky up but never stored it; we store it, so the
        // strategy actually works as documented).
        if strategy == Strategy::StickyAffinity {
            if let Some(provider) = self.inner.health.get_sticky(session, now_unix) {
                if let Some(rt) = self.runtime(&provider) {
                    if self.candidate_ok(&rt) {
                        let m = rt.def.read().unwrap().rewrite_model(model);
                        return vec![RouteCandidate {
                            provider,
                            model: m,
                            strategy,
                        }];
                    }
                }
            }
        }
        let mut rts: Vec<Arc<ProviderRuntime>> = {
            let runtimes = self.inner.runtimes.read().unwrap();
            let order = self.inner.order.read().unwrap();
            order
                .iter()
                .filter_map(|n| runtimes.get(n).cloned())
                .filter(|rt| self.candidate_ok(rt))
                .collect()
        };
        // Model scoping: a provider serves the request only when it lists
        // the model (or a wildcard). This is the multi-provider analog of
        // the old proxy's pass-through — except now unknown models don't
        // fan out to providers that never heard of them.
        rts.retain(|rt| rt.def.read().unwrap().serves_model(model));
        if rts.is_empty() {
            return vec![];
        }
        let ordered: Vec<Arc<ProviderRuntime>> = match strategy {
            Strategy::Hybrid => self.order_hybrid(&rts, model),
            Strategy::AstRace => rts, // race wants the full candidate set
            Strategy::StickyAffinity => self.order_hybrid(&rts, model),
            Strategy::WeightedElo => self.order_elo(&rts),
            Strategy::LeastLatency => self.order_latency(&rts),
            Strategy::RoundRobin => self.order_round_robin(&rts),
            Strategy::Free => rts
                .into_iter()
                .filter(|rt| rt.def.read().unwrap().free_tier)
                .collect(),
            Strategy::CircuitChain => self.order_hybrid(&rts, model),
        };
        ordered
            .into_iter()
            .map(|rt| {
                let (provider, m) = {
                    let def = rt.def.read().unwrap();
                    (def.name.clone(), def.rewrite_model(model))
                };
                RouteCandidate {
                    provider,
                    model: m,
                    strategy,
                }
            })
            .collect()
    }

    /// A runtime is a selection candidate when its definition is usable, the
    /// health gate passes, and the circuit isn't open.
    fn candidate_ok(&self, rt: &ProviderRuntime) -> bool {
        if !rt.def.read().unwrap().usable() {
            return false;
        }
        let name = rt.name();
        if !self.inner.health.is_healthy(&name) {
            return false;
        }
        !matches!(rt.circuit.lock().unwrap().state(), CircuitState::Open)
    }

    /// Hybrid order: healthy providers first by ascending latency (measured
    /// beats unknown, exactly AstMatrix's least-latency tiebreak), then
    /// unknown-latency providers by ELO.
    fn order_hybrid(
        &self,
        rts: &[Arc<ProviderRuntime>],
        _model: &str,
    ) -> Vec<Arc<ProviderRuntime>> {
        let mut with_lat: Vec<(f64, Arc<ProviderRuntime>)> = vec![];
        let mut unknown: Vec<Arc<ProviderRuntime>> = vec![];
        for rt in rts {
            match self.inner.health.latency_ms(&rt.name()) {
                Some(ms) => with_lat.push((ms, rt.clone())),
                None => unknown.push(rt.clone()),
            }
        }
        with_lat.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));
        unknown.sort_by_key(|rt| -self.inner.health.get_elo(&rt.name()));
        with_lat
            .into_iter()
            .map(|(_, rt)| rt)
            .chain(unknown)
            .collect()
    }

    /// Weighted ELO: pick providers with probability proportional to ELO
    /// (nonpositive ELO counts as 1500, exactly AstMatrix's rule), highest
    /// weight first, without replacement.
    fn order_elo(&self, rts: &[Arc<ProviderRuntime>]) -> Vec<Arc<ProviderRuntime>> {
        let mut remaining: Vec<Arc<ProviderRuntime>> = rts.to_vec();
        let mut out = vec![];
        let mut rng = rand::thread_rng();
        while !remaining.is_empty() {
            let total: f64 = remaining
                .iter()
                .map(|rt| {
                    let elo = self.inner.health.get_elo(&rt.name());
                    let w = if elo <= 0 { 1500.0 } else { elo as f64 };
                    w * rt.def.read().unwrap().weight.max(0.0)
                })
                .sum();
            let pick = if total <= 0.0 {
                0
            } else {
                let mut roll: f64 = rng.gen_range(0.0..total);
                let mut idx = 0;
                for (i, rt) in remaining.iter().enumerate() {
                    let elo = self.inner.health.get_elo(&rt.name());
                    let w = if elo <= 0 { 1500.0 } else { elo as f64 };
                    roll -= w * rt.def.read().unwrap().weight.max(0.0);
                    if roll <= 0.0 {
                        idx = i;
                        break;
                    }
                }
                idx
            };
            out.push(remaining.remove(pick));
        }
        out
    }

    fn order_latency(&self, rts: &[Arc<ProviderRuntime>]) -> Vec<Arc<ProviderRuntime>> {
        let mut rts = rts.to_vec();
        rts.sort_by(|a, b| {
            match (
                self.inner.health.latency_ms(&a.name()),
                self.inner.health.latency_ms(&b.name()),
            ) {
                (Some(x), Some(y)) => x.partial_cmp(&y).unwrap_or(std::cmp::Ordering::Equal),
                // Any measured latency beats unknown latency (AstMatrix).
                (Some(_), None) => std::cmp::Ordering::Less,
                (None, Some(_)) => std::cmp::Ordering::Greater,
                (None, None) => std::cmp::Ordering::Equal,
            }
        });
        rts
    }

    /// Round-robin: a single atomic counter incremented before the modulo,
    /// exactly AstMatrix's `nextServer` semantics, rotated over the current
    /// candidate set.
    fn order_round_robin(&self, rts: &[Arc<ProviderRuntime>]) -> Vec<Arc<ProviderRuntime>> {
        static RR: AtomicU64 = AtomicU64::new(0);
        let start = RR.fetch_add(1, Ordering::SeqCst) as usize;
        let n = rts.len();
        (0..n).map(|i| rts[(start + i) % n].clone()).collect()
    }

    /// Acquire one attempt on a candidate: circuit gate, provider token
    /// bucket, governor permit (when the path is gated), then the FIFO
    /// dispatcher slot. Every strategy — including race — goes through the
    /// gates; AstMatrix's race path did not, which is the corrected
    /// behavior documented in `MIGRATION.md`.
    pub async fn acquire(
        &self,
        candidate: &RouteCandidate,
        ctx: &AcquireCtx,
    ) -> Result<Acquired, RouteError> {
        let rt = self.runtime(&candidate.provider).ok_or_else(|| {
            RouteError::Unavailable(format!("unknown provider {}", candidate.provider))
        })?;
        rt.metrics.requests.fetch_add(1, Ordering::Relaxed);
        counter!("flock_route_requests_total", "provider" => candidate.provider.clone())
            .increment(1);

        // Circuit gate (mutating: a half-open trial consumes the trial).
        {
            let mut cb = rt.circuit.lock().unwrap();
            if !cb.allow() {
                rt.metrics.circuit_rejected.fetch_add(1, Ordering::Relaxed);
                counter!("flock_route_circuit_rejected_total", "provider" => candidate.provider.clone())
                    .increment(1);
                return Err(RouteError::Unavailable(format!(
                    "circuit open for {}",
                    candidate.provider
                )));
            }
        }
        // Provider token bucket.
        if !self
            .inner
            .limiter
            .lock()
            .unwrap()
            .allow(&candidate.provider)
        {
            rt.metrics.rate_limited.fetch_add(1, Ordering::Relaxed);
            counter!("flock_route_rate_limited_total", "provider" => candidate.provider.clone())
                .increment(1);
            return Err(RouteError::RateLimited(candidate.provider.clone()));
        }
        // Governor permit for generation paths.
        let permit = self
            .admit_model(&rt, &candidate.model, ctx, candidate)
            .await?;
        // FIFO dispatcher slot.
        let prefer = ctx.prefer_lane;
        let slot = {
            let rx = rt.dispatcher.acquire(ctx.deadline, prefer);
            tokio::select! {
                s = rx => s.map_err(|_| RouteError::Deadline)?,
                _ = ctx.client_gone() => return Err(RouteError::ClientGone),
            }
        };
        let base_url = rt.def.read().unwrap().base_url.clone();
        Ok(Acquired {
            provider: candidate.provider.clone(),
            model: candidate.model.clone(),
            base_url,
            strategy: candidate.strategy,
            slot,
            permit,
            attempt_started: Instant::now(),
            session: ctx.session.clone(),
        })
    }

    /// Wait for a model-pressure permit on this provider's governor, polling
    /// exactly like the old single-upstream path. `Ok(None)` = not gated.
    async fn admit_model(
        &self,
        rt: &ProviderRuntime,
        model: &str,
        ctx: &AcquireCtx,
        candidate: &RouteCandidate,
    ) -> Result<Option<ModelPermit>, RouteError> {
        let gated =
            self.inner.governor_enabled.load(Ordering::SeqCst) && model != "none" && ctx.gated_path;
        if !gated {
            return Ok(None);
        }
        let pinned = self
            .inner
            .governor_overrides
            .read()
            .unwrap()
            .get(model)
            .copied();
        let mut next_heartbeat = Instant::now() + ctx.heartbeat;
        loop {
            if let Some(p) = rt.governor.admit(model, pinned) {
                return Ok(Some(p));
            }
            if Instant::now() + governor::POLL > ctx.deadline {
                rt.metrics.errors.fetch_add(1, Ordering::Relaxed);
                counter!("flock_route_errors_total", "provider" => candidate.provider.clone())
                    .increment(1);
                return Err(RouteError::Deadline);
            }
            tokio::time::sleep(governor::POLL).await;
            if Instant::now() >= next_heartbeat {
                if ctx.client_gone_now() {
                    return Err(RouteError::ClientGone);
                }
                next_heartbeat = Instant::now() + ctx.heartbeat;
            }
        }
    }

    /// Record a successful attempt: circuit success, latency EMA, health,
    /// sticky session, and request counters.
    pub fn finish_success(&self, acq: &Acquired, status: u16) {
        let now_unix = unix_now();
        let Some(rt) = self.runtime(&acq.provider) else {
            return;
        };
        rt.circuit.lock().unwrap().record_success();
        let latency = acq.attempt_started.elapsed();
        self.inner.health.record_latency(&acq.provider, latency);
        self.inner
            .health
            .record_health(&acq.provider, true, now_unix);
        if acq.strategy == Strategy::StickyAffinity {
            if let Some(session) = acq.session.as_deref() {
                self.inner.health.set_sticky(
                    session,
                    &acq.provider,
                    self.routing_config().sticky_ttl(),
                    now_unix,
                );
            }
        }
        counter!("flock_route_success_total",
            "provider" => acq.provider.clone(),
            "status" => status.to_string())
        .increment(1);
    }

    /// Record a failed attempt: circuit failure on 429/5xx (never on 4xx —
    /// a client error is not provider failure), health mark, lane cooldown
    /// via the granting slot's own pool.
    pub fn finish_failure(
        &self,
        acq: &Acquired,
        status: u16,
        worker_exhausted: bool,
        retry_after: Option<Duration>,
    ) {
        let now_unix = unix_now();
        let Some(rt) = self.runtime(&acq.provider) else {
            return;
        };
        rt.metrics.errors.fetch_add(1, Ordering::Relaxed);
        // Lane cooldown, exactly the old serving path: a connection-level
        // failure cools the lane 5 s with the connect label; an HTTP
        // 429/5xx cools it for the upstream Retry-After header (default
        // 10 s). A 4xx never cools the lane and never touches the circuit.
        // Worker exhaustion is model-scoped: the governor drains instead
        // of burning a lane cooldown on a failover that cannot help. The
        // lane is spared, but the circuit still sees the failure.
        let cooldown: Option<(String, Duration)> = if worker_exhausted {
            None
        } else if status == 0 {
            Some(("connect".to_string(), Duration::from_secs(5)))
        } else if status == 429 || status >= 500 {
            Some((
                status.to_string(),
                retry_after.unwrap_or(Duration::from_secs(10)),
            ))
        } else {
            None
        };
        if status == 0 || status == 429 || status >= 500 {
            rt.circuit.lock().unwrap().record_failure(now_unix);
            self.inner
                .health
                .record_health(&acq.provider, false, now_unix);
        }
        if let Some((label, backoff)) = cooldown {
            counter!("flock_lane_cooldown_total",
                "lane" => acq.slot.lane.to_string(),
                "status" => label.clone())
            .increment(1);
            acq.slot.pool.penalize(acq.slot.lane, backoff);
            self.inner.persist.op(PersistOp::Cooldown {
                provider: acq.provider.clone(),
                key: acq.slot.pool.lane_key(acq.slot.lane).unwrap_or_default(),
                until_unix_ms: now_unix * 1000 + backoff.as_millis() as u64,
            });
        }
        if worker_exhausted {
            let pinned = self
                .inner
                .governor_overrides
                .read()
                .unwrap()
                .get(&acq.model)
                .copied();
            rt.governor.note_exhausted(&acq.model, pinned);
        }
        counter!("flock_route_errors_total",
            "provider" => acq.provider.clone(),
            "status" => status.to_string())
        .increment(1);
    }

    /// Record one upstream attempt from the serving path without the full
    /// [`Acquired`] ceremony. The serving path owns lane cooldown itself
    /// (the legacy retry loop), so this only feeds the router's shared
    /// health view: circuit breaker, latency, and provider counters.
    /// `status` is the HTTP status, or 0 for a connection-level failure.
    pub fn record_attempt(
        &self,
        provider: &str,
        model: &str,
        status: u16,
        latency: std::time::Duration,
        worker_exhausted: bool,
    ) {
        let now_unix = unix_now();
        let Some(rt) = self.runtime(provider) else {
            return;
        };
        let failed = status == 0 || status == 429 || status >= 500;
        if failed {
            rt.circuit.lock().unwrap().record_failure(now_unix);
            self.inner.health.record_health(provider, false, now_unix);
            rt.metrics.errors.fetch_add(1, Ordering::Relaxed);
        } else {
            rt.circuit.lock().unwrap().record_success();
            self.inner.health.record_health(provider, true, now_unix);
        }
        self.inner.health.record_latency(provider, latency);
        if worker_exhausted {
            let pinned = self
                .inner
                .governor_overrides
                .read()
                .unwrap()
                .get(model)
                .copied();
            rt.governor.note_exhausted(model, pinned);
        }
        rt.metrics.requests.fetch_add(1, Ordering::Relaxed);
        counter!("flock_route_attempt_total",
            "provider" => provider.to_string(),
            "status" => status.to_string())
        .increment(1);
    }

    /// Aggregate `/v1/models` across providers: each provider's cached
    /// upstream listing, tagged with its source provider. Used by the
    /// models endpoint; the proxy's per-request model cache semantics
    /// (TTL, single-flight refresh) live on each runtime's `models_cache`.
    /// Empty-completion strikes decay after this long without a new strike.
    pub const EMPTY_STRIKE_DECAY: Duration = Duration::from_secs(600);

    /// Record an empty completion (2xx, no content, no tool calls) against a
    /// provider/model pair. Surfaced as the flock_model_empty_strikes gauge.
    pub fn record_empty_strike(&self, provider: &str, model: &str) {
        let mut strikes = self.inner.empty_strikes.lock().unwrap();
        let entry = strikes
            .entry((provider.to_owned(), model.to_owned()))
            .or_insert((0, Instant::now()));
        entry.0 += 1;
        entry.1 = Instant::now();
        gauge!(
            "flock_model_empty_strikes",
            "provider" => provider.to_owned(),
            "model" => model.to_owned(),
        )
        .set(entry.0 as f64);
    }

    /// Current strike count for a provider/model pair (0 when decayed).
    pub fn empty_strike_count(&self, provider: &str, model: &str) -> u32 {
        let mut strikes = self.inner.empty_strikes.lock().unwrap();
        let key = (provider.to_owned(), model.to_owned());
        match strikes.get(&key) {
            Some((n, at)) if at.elapsed() < Self::EMPTY_STRIKE_DECAY => *n,
            _ => {
                strikes.remove(&key);
                0
            }
        }
    }

    /// One live metadata record per provider runtime: usability (keys
    /// present), health-probe state, circuit state, ELO, and model list.
    /// Backs the /v1/models live-metadata enrichment.
    pub fn provider_metadata(&self) -> Vec<ProviderMeta> {
        let runtimes = self.inner.runtimes.read().unwrap();
        runtimes
            .values()
            .map(|rt| {
                let def = rt.def.read().unwrap();
                let circuit = match rt.circuit.lock().unwrap().state() {
                    CircuitState::Closed => "closed",
                    CircuitState::HalfOpen => "half_open",
                    CircuitState::Open => "open",
                };
                ProviderMeta {
                    provider: def.name.clone(),
                    display_name: def.display_name.clone(),
                    usable: def.usable(),
                    healthy: self.inner.health.is_healthy(&def.name),
                    latency_ms: self.inner.health.latency_ms(&def.name),
                    elo: self.inner.health.get_elo(&def.name),
                    circuit,
                    models: def.models.clone(),
                }
            })
            .collect()
    }

    pub fn models_snapshot(&self) -> Vec<ProviderModels> {
        self.inner
            .runtimes
            .read()
            .unwrap()
            .values()
            .map(|rt| {
                let def = rt.def.read().unwrap();
                ProviderModels {
                    provider: def.name.clone(),
                    models: def.models.clone(),
                    cached: rt.models_cache.lock().unwrap().is_some(),
                }
            })
            .collect()
    }

    // -- background loops -------------------------------------------------

    fn spawn_probe_loop(&self) {
        let this = self.clone();
        tokio::spawn(async move {
            loop {
                let interval = this
                    .routing_config()
                    .probe_interval()
                    .unwrap_or(PROBE_INTERVAL_FALLBACK);
                tokio::time::sleep(interval).await;
                this.probe_once().await;
            }
        });
    }

    /// Probe every usable provider's `/v1/models`: success refreshes the
    /// provider's models cache and records health + latency; failure marks
    /// the provider unhealthy (but never evicts its models cache — a probe
    /// failure is not proof the models vanished).
    async fn probe_once(&self) {
        let now_unix = unix_now();
        let rts: Vec<Arc<ProviderRuntime>> = {
            self.inner
                .runtimes
                .read()
                .unwrap()
                .values()
                .filter(|rt| rt.def.read().unwrap().usable())
                .cloned()
                .collect()
        };
        for rt in rts {
            let (name, base_url) = {
                let def = rt.def.read().unwrap();
                (def.name.clone(), def.base_url.clone())
            };
            let url = format!("{}/v1/models", base_url.trim_end_matches('/'));
            let started = Instant::now();
            let resp = self.inner.client.get(&url).send().await;
            match resp {
                Ok(r) if r.status().is_success() => {
                    if let Ok(bytes) = r.bytes().await {
                        *rt.models_cache.lock().unwrap() = Some((Instant::now(), bytes));
                    }
                    let latency = started.elapsed();
                    self.inner.health.record_latency(&name, latency);
                    self.inner.health.record_health(&name, true, now_unix);
                    gauge!("flock_provider_latency_ms", "provider" => name.clone())
                        .set(latency.as_secs_f64() * 1000.0);
                }
                Ok(r) => {
                    self.inner.health.record_health(&name, false, now_unix);
                    tracing::warn!(provider = %name, status = %r.status(), "provider probe failed");
                }
                Err(e) => {
                    self.inner.health.record_health(&name, false, now_unix);
                    tracing::warn!(provider = %name, error = %e, "provider probe error");
                }
            }
        }
    }

    fn spawn_persist_loop(&self) {
        let this = self.clone();
        tokio::spawn(async move {
            loop {
                tokio::time::sleep(PERSIST_INTERVAL).await;
                this.persist_once();
            }
        });
    }

    /// Flush runtime state: circuits, lane windows, cooldowns, governor
    /// snapshots. Provider health/latency/ELO/sticky are write-through on
    /// record, so the tick only carries the in-memory runtime state.
    fn persist_once(&self) {
        let now_unix = unix_now();
        let rts: Vec<Arc<ProviderRuntime>> = self
            .inner
            .runtimes
            .read()
            .unwrap()
            .values()
            .cloned()
            .collect();
        for rt in rts {
            let snap = rt.snapshot(now_unix);
            self.inner.persist.op(PersistOp::Circuit {
                provider: snap.provider.clone(),
                snap: snap.circuit,
            });
            self.inner.persist.op(PersistOp::LaneWindows {
                provider: snap.provider.clone(),
                rows: snap.lanes,
            });
            for (key, until_unix_ms) in snap.cooldowns {
                self.inner.persist.op(PersistOp::Cooldown {
                    provider: snap.provider.clone(),
                    key,
                    until_unix_ms,
                });
            }
            for (model, gsnap) in snap.governors {
                self.inner.persist.op(PersistOp::Governor {
                    provider: snap.provider.clone(),
                    model,
                    snap: gsnap,
                });
            }
        }
        let swept = self.inner.health.sweep_expired_stickies(now_unix);
        if swept > 0 {
            self.inner.persist.op(PersistOp::StickySweep { now_unix });
        }
    }
}

/// Context for one acquire: deadline, heartbeat, and the governor-gating
/// decision the proxy already made for this path.
pub struct AcquireCtx {
    pub deadline: Instant,
    pub heartbeat: Duration,
    /// Whether this path is governor-gated (generation endpoints only).
    pub gated_path: bool,
    /// Preferred pool lane (conversation affinity), if any.
    pub prefer_lane: Option<usize>,
    /// Session identity for sticky affinity (set on success).
    pub session: Option<String>,
    /// Poll this to notice a gone client without holding the borrow.
    pub client_gone: Box<dyn Fn() -> bool + Send + Sync>,
}

impl AcquireCtx {
    pub fn client_gone_now(&self) -> bool {
        (self.client_gone)()
    }

    /// Await the client-gone signal as a future for select!.
    pub async fn client_gone(&self) {
        // Poll-based: the proxy's heartbeat loop already watches the client;
        // the flag is flipped there. A short poll keeps this future honest
        // without another channel.
        loop {
            if (self.client_gone)() {
                return;
            }
            tokio::time::sleep(Duration::from_millis(100)).await;
        }
    }
}

/// Operator view of one provider.
#[derive(Debug, Clone)]
pub struct ProviderView {
    pub name: String,
    pub display_name: String,
    pub base_url: String,
    pub enabled: bool,
    pub usable: bool,
    pub healthy: bool,
    pub latency_ms: Option<f64>,
    pub elo: i32,
    pub circuit: CircuitState,
    pub models: Vec<String>,
    pub free: bool,
    pub weight: f64,
    pub requests: u64,
    pub errors: u64,
    pub pool_lanes: usize,
    pub pool_capacity_rpm: usize,
}

/// One provider's model listing for the aggregated `/v1/models`.
#[derive(Debug, Clone)]
pub struct ProviderModels {
    pub provider: String,
    pub models: Vec<String>,
    pub cached: bool,
}

/// Retryable upstream statuses: 429 and 5xx. A 4xx is the client's error,
/// never the provider's: it is relayed verbatim, never retried, never
/// failed over, and never counted against the provider's circuit.
pub(crate) fn retryable_status(status: u16) -> bool {
    matches!(status, 429 | 500 | 502 | 503 | 504)
}

/// Rewrite the request body's `model` field to the provider's upstream id.
/// Non-JSON bodies, or bodies already carrying the right id, pass through
/// untouched (zero-copy when nothing changes).
fn rewrite_body_model(body: &Bytes, model: &str) -> Bytes {
    let mut v: serde_json::Value = match serde_json::from_slice(body) {
        Ok(v) => v,
        Err(_) => return body.clone(),
    };
    if !v.is_object() {
        return body.clone();
    }
    if v.get("model").and_then(|m| m.as_str()) == Some(model) {
        return body.clone();
    }
    v["model"] = serde_json::Value::String(model.to_owned());
    serde_json::to_vec(&v)
        .map(Bytes::from)
        .unwrap_or_else(|_| body.clone())
}

/// One routed buffered execution: everything the proxy knows about the
/// request, minus proxy-specific response shaping.
pub struct ExecuteCtx {
    pub http: reqwest::Client,
    pub method: reqwest::Method,
    pub path_query: String,
    pub content_type: Option<String>,
    pub accept: Option<String>,
    pub body: Bytes,
    /// Requested model label (pre-rewrite); used for selection.
    pub model: String,
    /// Session identity for sticky affinity.
    pub session: Option<String>,
    pub deadline: Instant,
    pub heartbeat: Duration,
    pub request_timeout: Duration,
    /// Conversation-affinity lane hint.
    pub prefer_lane: Option<usize>,
    /// Whether generation endpoints gate on the model governor.
    pub gated_path: bool,
    pub client_gone: Box<dyn Fn() -> bool + Send + Sync>,
}

/// Outcome of [`RouterHandle::execute_buffered`].
pub enum ExecuteOutcome {
    /// Upstream response; relay the body stream verbatim (coalescing off).
    Response(reqwest::Response),
    /// Buffered upstream response: the router read the body to apply the
    /// empty-completion substance guard; relay these bytes verbatim.
    Buffered {
        status: u16,
        content_type: String,
        body: bytes::Bytes,
    },
    /// Shared buffered response (coalescing on): the leader read the full
    /// body and published it; followers receive the same bytes.
    Coalesced(std::sync::Arc<crate::coalescer::SharedResponse>),
}

impl RouterHandle {
    /// Execute one buffered (non-streaming) request across providers.
    ///
    /// Selection orders candidates by the configured strategy; each attempt
    /// passes the provider's full admission stack (circuit gate, token
    /// bucket, governor permit, FIFO slot) via [`RouterHandle::acquire`],
    /// rewrites the model to the provider's upstream id, and sends. On a
    /// connection error or a retryable status the attempt is recorded via
    /// [`RouterHandle::finish_failure`] (circuit, lane cooldown, worker
    /// exhaustion) and the loop fails over to the next candidate, up to
    /// `max_retries` total attempts. Non-retryable statuses (including 4xx)
    /// are recorded as successes and returned to the client verbatim.
    ///
    /// When `enable_coalescing`, identical in-flight requests collapse onto
    /// the leader's single upstream call (AstMatrix instantiated its
    /// coalescer but never invoked it; here it is on the request path).
    pub async fn execute_buffered(&self, ctx: ExecuteCtx) -> Result<ExecuteOutcome, RouteError> {
        use crate::coalescer::{coalesce_key, Coalesce};
        let ExecuteCtx {
            http,
            method,
            path_query,
            content_type,
            accept,
            body,
            model,
            session,
            deadline,
            heartbeat,
            request_timeout,
            prefer_lane,
            gated_path,
            client_gone,
        } = ctx;
        let routing = self.routing_config();
        let candidates = self.select(&model, session.as_deref().unwrap_or(""), None);
        if candidates.is_empty() {
            return Err(RouteError::Unavailable(format!(
                "no provider serves model '{model}'"
            )));
        }
        // Coalescing is keyed on request identity and owned by the first
        // candidate's runtime (the preferred provider for this request).
        let mut lead: Option<crate::coalescer::Lead> = if routing.enable_coalescing {
            match self.runtime(&candidates[0].provider) {
                Some(rt) => {
                    let key = coalesce_key(method.as_str(), &path_query, &body);
                    match rt.coalescer.register(key) {
                        Coalesce::Follow(rx) => {
                            if let Some(shared) = rt.coalescer.wait(rx).await {
                                return Ok(ExecuteOutcome::Coalesced(shared));
                            }
                            None // leader died unpublished; proceed alone
                        }
                        Coalesce::Lead(lead) => Some(lead),
                    }
                }
                None => None,
            }
        } else {
            None
        };
        let acquire_ctx = AcquireCtx {
            deadline,
            heartbeat,
            gated_path,
            prefer_lane,
            session,
            client_gone,
        };
        // A lone candidate retries until the deadline (exactly the old
        // single-upstream loop); several candidates bound the failover
        // rounds by max_retries.
        let max_attempts = if candidates.len() == 1 {
            usize::MAX
        } else {
            routing.max_retries.max(1)
        };
        let mut last_error = RouteError::Unavailable("no candidate attempted".to_owned());
        let mut attempts = 0usize;
        let mut empty_count = 0usize;
        for candidate in candidates.iter().cycle() {
            // The deadline is the arbiter: saturation and stubborn
            // upstreams surface as 504, never as a failover 502.
            if Instant::now() >= deadline {
                return Err(RouteError::Deadline);
            }
            if attempts >= max_attempts {
                break;
            }
            attempts += 1;
            let acq = match self.acquire(candidate, &acquire_ctx).await {
                Ok(a) => a,
                Err(RouteError::RateLimited(p)) => {
                    // Fail over to the next candidate; when every
                    // candidate is dry the cycle repeats until the
                    // deadline above, preserving "saturation waits".
                    // Yield briefly so a lone dry candidate does not
                    // hot-spin the bucket.
                    last_error = RouteError::RateLimited(p);
                    tokio::time::sleep(Duration::from_millis(50)).await;
                    continue;
                }
                Err(RouteError::Unavailable(p)) => {
                    last_error = RouteError::Unavailable(p);
                    continue;
                }
                Err(e) => return Err(e),
            };
            let req_body = rewrite_body_model(&body, &acq.model);
            let url = format!("{}{}", acq.base_url, path_query);
            let mut req = http.request(method.clone(), &url).header(
                reqwest::header::AUTHORIZATION,
                format!("Bearer {}", acq.slot.key),
            );
            if let Some(ct) = &content_type {
                req = req.header(reqwest::header::CONTENT_TYPE, ct.as_str());
            }
            if let Some(a) = &accept {
                req = req.header(reqwest::header::ACCEPT, a.as_str());
            }
            let resp = req.body(req_body).timeout(request_timeout).send().await;
            match resp {
                Err(e) => {
                    // Connection-level failure: no status to classify.
                    // finish_failure(0) feeds the circuit and cools the
                    // lane 5 s with the "connect" label, exactly the old
                    // serving path.
                    self.finish_failure(&acq, 0, false, None);
                    last_error = RouteError::Unavailable(format!("{}: {e}", candidate.provider));
                }
                Ok(r) => {
                    let status = r.status().as_u16();
                    if retryable_status(status) {
                        // Sniff the error body: worker exhaustion is
                        // model-scoped (shared across every key), so the
                        // governor drains instead of burning lane cooldowns
                        // on failovers that cannot help.
                        let retry_after = r
                            .headers()
                            .get(reqwest::header::RETRY_AFTER)
                            .and_then(|v| v.to_str().ok())
                            .and_then(|s| s.parse::<u64>().ok())
                            .map(Duration::from_secs);
                        let detail = r.text().await.unwrap_or_default();
                        let exhausted = governor::is_worker_exhausted(&detail);
                        self.finish_failure(&acq, status, exhausted, retry_after);
                        last_error = RouteError::Unavailable(format!(
                            "{}: upstream {status}",
                            candidate.provider
                        ));
                    } else {
                        // Empty-completion substance guard: a 2xx chat
                        // completion with no content and no tool calls is a
                        // failure, not a success. Read the body, strike the
                        // provider/model pair, and fail over; when every
                        // candidate comes back empty the loop exits with an
                        // honest 502. Non-chat-completion paths keep the
                        // zero-copy relay below.
                        if status >= 200
                            && status < 300
                            && is_chat_completions_path(&path_query)
                        {
                            let content_type = r
                                .headers()
                                .get(reqwest::header::CONTENT_TYPE)
                                .and_then(|v| v.to_str().ok())
                                .unwrap_or("application/json")
                                .to_owned();
                            // A stalled body is a gateway failure, never an empty
                            // 200: the old relay() mapped body-read errors to
                            // 502, and failover cannot help a body that already
                            // sent 200 headers.
                            let bytes = match r.bytes().await {
                                Ok(b) => b,
                                Err(_) => {
                                    drop(lead.take());
                                    return Err(RouteError::Unavailable(
                                        "upstream body stalled".to_owned(),
                                    ));
                                }
                            };
                            if !crate::observation::has_substance(&bytes) {
                                // Never publish an empty body to coalesced
                                // followers: drop the lead so they proceed
                                // alone.
                                drop(lead.take());
                                self.finish_failure(&acq, status, false, None);
                                self.record_empty_strike(&candidate.provider, &model);
                                empty_count += 1;
                                if empty_count >= candidates.len() {
                                    // Every candidate came back empty: an
                                    // honest gateway failure, never a blank
                                    // 200 and never a deadline spin.
                                    return Err(RouteError::Unavailable(format!(
                                        "all candidates returned empty completions for model '{model}'",
                                    )));
                                }
                                tracing::warn!(
                                    provider = %candidate.provider,
                                    model = %model,
                                    "empty completion guarded: failing over",
                                );
                                last_error = RouteError::Unavailable(format!(
                                    "empty completion from {} for model '{model}'",
                                    candidate.provider
                                ));
                                continue;
                            }
                            self.finish_success(&acq, status);
                            if let Some(lead) = lead.take() {
                                let shared = std::sync::Arc::new(
                                    crate::coalescer::SharedResponse {
                                        status,
                                        content_type: content_type.clone(),
                                        body: bytes,
                                    },
                                );
                                lead.complete(crate::coalescer::SharedResponse {
                                    status: shared.status,
                                    content_type: shared.content_type.clone(),
                                    body: shared.body.clone(),
                                });
                                return Ok(ExecuteOutcome::Coalesced(shared));
                            }
                            return Ok(ExecuteOutcome::Buffered {
                                status,
                                content_type,
                                body: bytes,
                            });
                        }
                        self.finish_success(&acq, status);
                        if let Some(lead) = lead.take() {
                            let ct = r
                                .headers()
                                .get(reqwest::header::CONTENT_TYPE)
                                .and_then(|v| v.to_str().ok())
                                .unwrap_or("")
                                .to_owned();
                            // A stalled body is a gateway failure, never an empty
                            // 200: the old relay() mapped body-read errors to
                            // 502. The 200 headers already counted the
                            // circuit success above (exactly the old
                            // record-then-relay order); drop the lead so
                            // followers proceed alone.
                            let bytes = match r.bytes().await {
                                Ok(b) => b,
                                Err(_) => {
                                    drop(lead);
                                    return Err(RouteError::Unavailable(
                                        "upstream body stalled".to_owned(),
                                    ));
                                }
                            };
                            let shared = std::sync::Arc::new(crate::coalescer::SharedResponse {
                                status,
                                content_type: ct,
                                body: bytes,
                            });
                            lead.complete(crate::coalescer::SharedResponse {
                                status: shared.status,
                                content_type: shared.content_type.clone(),
                                body: shared.body.clone(),
                            });
                            return Ok(ExecuteOutcome::Coalesced(shared));
                        }
                        return Ok(ExecuteOutcome::Response(r));
                    }
                }
            }
        }
        // Dropping an uncompleted Lead releases followers to proceed alone.
        drop(lead);
        Err(last_error)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_def(name: &str) -> ProviderDef {
        ProviderDef {
            name: name.into(),
            base_url: "https://example.com".into(),
            keys: vec![crate::providers::ProviderKey {
                key: "k".into(),
                key_env: String::new(),
                owner: "root".into(),
                enabled: true,
                rpm: 60,
            }],
            models: vec!["*".into()],
            display_name: name.into(),
            enabled: true,
            ..ProviderDef::default()
        }
    }

    fn test_router(defs: Vec<ProviderDef>) -> RouterHandle {
        // Bypass build() (which needs a data dir and spawns loops): assemble
        // the inner state directly with persistence disabled.
        let health = HealthDb::new(PersistHandle::disabled());
        let mut runtimes = HashMap::new();
        let mut order = vec![];
        for def in &defs {
            runtimes.insert(def.name.clone(), ProviderRuntime::build(def.clone()));
            order.push(def.name.clone());
        }
        let limiter = ProviderRateLimiter::build(&defs);
        let inner = Arc::new(RouterInner {
            runtimes: RwLock::new(runtimes),
            order: RwLock::new(order),
            health,
            persist: PersistHandle::disabled(),
            limiter: Mutex::new(limiter),
            routing: RwLock::new(RoutingCfg::default()),
            governor_overrides: RwLock::new(Default::default()),
            governor_enabled: AtomicBool::new(true),
            client: reqwest::Client::new(),
            data_dir: PathBuf::from("/tmp/flock-router-test"),
            _writer: None,
            empty_strikes: Mutex::new(HashMap::new()),
        });
        RouterHandle { inner }
    }

    #[tokio::test]
    async fn hybrid_orders_by_latency_then_elo() {
        let r = test_router(vec![test_def("a"), test_def("b"), test_def("c")]);
        let now = unix_now();
        r.inner
            .health
            .record_latency("a", Duration::from_millis(200));
        r.inner
            .health
            .record_latency("b", Duration::from_millis(50));
        r.inner.health.set_elo("c", 1800);
        let cands = r.select("m", "s", Some(Strategy::Hybrid));
        let names: Vec<_> = cands.iter().map(|c| c.provider.as_str()).collect();
        assert_eq!(names, vec!["b", "a", "c"]);
        let _ = now;
    }

    #[tokio::test]
    async fn unhealthy_providers_are_excluded() {
        let r = test_router(vec![test_def("a"), test_def("b")]);
        r.inner.health.record_health("a", false, unix_now());
        let cands = r.select("m", "s", Some(Strategy::Hybrid));
        assert_eq!(cands.len(), 1);
        assert_eq!(cands[0].provider, "b");
    }

    #[tokio::test]
    async fn open_circuit_excludes_provider() {
        let r = test_router(vec![test_def("a"), test_def("b")]);
        {
            let rt = r.runtime("a").unwrap();
            let mut cb = rt.circuit.lock().unwrap();
            for _ in 0..5 {
                cb.record_failure(unix_now());
            }
            assert_eq!(cb.state(), CircuitState::Open);
        }
        let cands = r.select("m", "s", Some(Strategy::Hybrid));
        assert_eq!(cands.len(), 1);
        assert_eq!(cands[0].provider, "b");
    }

    #[tokio::test]
    async fn sticky_affinity_pins_session() {
        let r = test_router(vec![test_def("a"), test_def("b")]);
        // Make b the clear hybrid winner so the sticky choice is visible.
        r.inner.health.record_latency("b", Duration::from_millis(1));
        r.inner
            .health
            .set_sticky("sess-1", "a", Duration::from_secs(60), unix_now());
        let cands = r.select("m", "sess-1", Some(Strategy::StickyAffinity));
        assert_eq!(cands.len(), 1);
        assert_eq!(cands[0].provider, "a");
    }

    #[tokio::test]
    async fn sticky_affinity_falls_back_when_pinned_provider_fails() {
        let r = test_router(vec![test_def("a"), test_def("b")]);
        r.inner.health.record_health("a", false, unix_now());
        r.inner
            .health
            .set_sticky("sess-1", "a", Duration::from_secs(60), unix_now());
        let cands = r.select("m", "sess-1", Some(Strategy::StickyAffinity));
        assert_eq!(cands.len(), 1);
        assert_eq!(cands[0].provider, "b");
    }

    #[tokio::test]
    async fn free_strategy_only_lists_free_providers() {
        let mut paid = test_def("paid");
        paid.free_tier = false;
        let mut free = test_def("free");
        free.free_tier = true;
        let r = test_router(vec![paid, free]);
        let cands = r.select("m", "s", Some(Strategy::Free));
        assert_eq!(cands.len(), 1);
        assert_eq!(cands[0].provider, "free");
    }

    #[tokio::test]
    async fn model_map_rewrites_upstream_model() {
        let mut def = test_def("a");
        def.model_map.insert("alias".into(), "real-model".into());
        let r = test_router(vec![def]);
        let cands = r.select("alias", "s", Some(Strategy::Hybrid));
        assert_eq!(cands.len(), 1);
        assert_eq!(cands[0].model, "real-model");
    }

    #[tokio::test]
    async fn round_robin_rotates_start() {
        let r = test_router(vec![test_def("a"), test_def("b"), test_def("c")]);
        let first: Vec<_> = r
            .select("m", "s", Some(Strategy::RoundRobin))
            .iter()
            .map(|c| c.provider.clone())
            .collect();
        let second: Vec<_> = r
            .select("m", "s", Some(Strategy::RoundRobin))
            .iter()
            .map(|c| c.provider.clone())
            .collect();
        assert_ne!(first, second, "round-robin must rotate");
        assert_eq!(first.len(), 3);
    }

    #[tokio::test]
    async fn weighted_elo_eventually_covers_all() {
        let r = test_router(vec![test_def("a"), test_def("b")]);
        r.inner.health.set_elo("a", 2000);
        r.inner.health.set_elo("b", 1000);
        // Over many draws the weaker provider must still be picked first
        // sometimes (probability-proportional, not argmax).
        let mut b_first = 0;
        for _ in 0..50 {
            let cands = r.select("m", "s", Some(Strategy::WeightedElo));
            if cands[0].provider == "b" {
                b_first += 1;
            }
        }
        assert!(b_first > 0, "weighted ELO never picked the weaker provider");
    }

    #[tokio::test]
    async fn rebuild_adds_and_removes_runtimes() {
        let r = test_router(vec![test_def("a")]);
        assert!(r.runtime("a").is_some());
        assert!(r.runtime("b").is_none());
        let mut stored = StoredConfig::default();
        stored.providers = vec![test_def("b")];
        r.rebuild(&stored);
        assert!(r.runtime("a").is_none());
        assert!(r.runtime("b").is_some());
    }
    #[tokio::test]
    async fn serving_handles_share_nvidia_runtime() {
        // The serving path must reuse the router's nvidia handles, not
        // copies: one pool, one governor (Arc ptr equality), one FIFO.
        let r = test_router(vec![test_def("nvidia")]);
        let (pool, _dispatch, governor) = crate::nvidia_serving_handles(&r);
        let rt = r.runtime("nvidia").expect("nvidia runtime");
        assert!(
            std::sync::Arc::ptr_eq(&pool, &rt.pool),
            "serving pool is not the router nvidia pool"
        );
        assert!(
            std::sync::Arc::ptr_eq(&governor, &rt.governor),
            "serving governor is not the router nvidia governor"
        );
    }

    #[tokio::test]
    async fn dispatcher_clone_shares_single_fifo() {
        // Cloning a Dispatcher must share its queue: grants from the clone
        // are paced by the same 25 ms GRANT_GAP as the original. Two
        // independently constructed Dispatchers would grant concurrently.
        use crate::pool::LaneSpec;
        let pool: PoolHandle = std::sync::Arc::new(std::sync::RwLock::new(std::sync::Arc::new(
            Pool::new(vec![LaneSpec {
                key: "k".into(),
                rpm: 1000,
                enabled: true,
            }]),
        )));
        let d1 = Dispatcher::new(pool);
        let d2 = d1.clone();
        let deadline = std::time::Instant::now() + std::time::Duration::from_secs(5);
        let _s1 = d1.acquire(deadline, None).await.expect("slot 1");
        let mid = std::time::Instant::now();
        let _s2 = d2.acquire(deadline, None).await.expect("slot 2");
        let gap = mid.elapsed();
        assert!(
            gap >= std::time::Duration::from_millis(20),
            "clone granted {gap:?} after the original: not the shared FIFO"
        );
    }

    #[tokio::test]
    async fn rebuild_preserves_nvidia_lane_windows() {
        // Settings rebuild must carry 61 s sliding-window state across: a
        // request recorded before rebuild still counts toward RPM after.
        let r = test_router(vec![test_def("nvidia")]);
        let rt = r.runtime("nvidia").expect("nvidia runtime");
        {
            let pool = rt.pool.read().unwrap();
            match pool.reserve(None) {
                crate::pool::Reservation::Ready { .. } => {}
                w => panic!("expected Ready, got {w:?}"),
            }
            let stats = pool.lane_stats();
            assert!(stats.iter().any(|s| s.in_window >= 1), "window not filled");
        }
        let mut stored = StoredConfig::default();
        let mut def = test_def("nvidia");
        def.display_name = "renamed".into(); // non-pool knob changes only
        stored.providers = vec![def];
        r.rebuild(&stored);
        let rt2 = r.runtime("nvidia").expect("nvidia runtime after rebuild");
        assert!(
            std::sync::Arc::ptr_eq(&rt, &rt2),
            "rebuild replaced the nvidia runtime object"
        );
        let stats = rt2.pool.read().unwrap().lane_stats();
        assert!(
            stats.iter().any(|s| s.in_window >= 1),
            "lane window state lost across rebuild: {stats:?}"
        );
    }

    #[tokio::test]
    async fn rebuild_applies_provider_url_and_key_changes() {
        // Base URL / key edits must take effect on the live runtime without
        // replacing the runtime object (state above is preserved).
        let r = test_router(vec![test_def("nvidia")]);
        let mut stored = StoredConfig::default();
        let mut def = test_def("nvidia");
        def.base_url = "https://new.example.com".into();
        def.keys.push(crate::providers::ProviderKey {
            key: "k2".into(),
            key_env: String::new(),
            owner: "root".into(),
            enabled: true,
            rpm: 60,
        });
        stored.providers = vec![def];
        r.rebuild(&stored);
        let rt = r.runtime("nvidia").expect("nvidia runtime");
        assert_eq!(rt.def.read().unwrap().base_url, "https://new.example.com");
        let stats = rt.pool.read().unwrap().lane_stats();
        assert!(
            stats.iter().any(|s| s.key == "k2"),
            "new key lane missing after rebuild: {stats:?}"
        );
    }
}
