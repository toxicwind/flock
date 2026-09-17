//! Health, latency, ELO, and sticky-affinity state — AstMatrix's
//! `healthdb.go`, native Rust, with real persistence.
//!
//! Fidelity notes:
//! - AstMatrix's `HealthDB` kept `healthy`, `lastProbe`, `latencies` (EMA,
//!   0.7/0.3), and `stickies` in memory, claimed SQLite persistence, but the
//!   shipped code never hydrated its maps from SQLite on startup and never
//!   enforced sticky expiry. Here everything is write-behind persisted to
//!   `$DATA_DIR/flock_state.db` and restored on boot, with expiry enforced.
//! - AstMatrix's `metrics.go` (referenced by `router.go`) does not exist in
//!   the shipped tree. Metrics here are real: health/circuit/ELO/sticky state
//!   is exposed through `observation.rs`'s existing `flock_*` series.
//!
//! The writer owns its `rusqlite::Connection` on a single background thread;
//! the hot path never blocks on disk. Boot restore is synchronous and runs
//! before any provider runtime starts.

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::mpsc::{self, Sender};
use std::sync::{Arc, RwLock};
use std::time::Duration;

use serde::{Deserialize, Serialize};

use crate::circuit::CircuitSnapshot;
use crate::governor::GovernorSnapshot;

/// AstMatrix's env/config override for the legacy database location.
pub fn astmatrix_db_default() -> PathBuf {
    std::env::var("FLOCK_ASTMATRIX_DB")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("/home/toxic/sovereign/data/ast_matrix.db"))
}

pub fn state_db_path(data_dir: &Path) -> PathBuf {
    data_dir.join("flock_state.db")
}

// ---------------------------------------------------------------------------
// In-memory state
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Default)]
struct HealthInner {
    healthy: HashMap<String, bool>,
    last_probe_unix: HashMap<String, u64>,
    latencies_ms: HashMap<String, f64>,
    elos: HashMap<String, i32>,
    stickies: HashMap<String, (String, u64)>, // session -> (provider, expires_unix)
}

#[derive(Debug, Clone)]
pub struct HealthDb {
    inner: Arc<RwLock<HealthInner>>,
    persist: PersistHandle,
}

impl HealthDb {
    pub fn new(persist: PersistHandle) -> Self {
        Self {
            inner: Arc::new(RwLock::new(HealthInner::default())),
            persist,
        }
    }

    /// `RecordHealth`: healthy providers stay in rotation.
    pub fn record_health(&self, provider: &str, healthy: bool, now_unix: u64) {
        {
            let mut g = self.inner.write().unwrap();
            g.healthy.insert(provider.to_string(), healthy);
            g.last_probe_unix.insert(provider.to_string(), now_unix);
        }
        self.persist.op(PersistOp::ProviderHealthTouched {
            provider: provider.to_string(),
            healthy,
            now_unix,
        });
    }

    /// `RecordLatency`: exponential moving average, alpha 0.7 new / 0.3 old,
    /// exactly as AstMatrix computed it.
    pub fn record_latency(&self, provider: &str, latency: Duration) {
        let ms = latency.as_secs_f64() * 1000.0;
        {
            let mut g = self.inner.write().unwrap();
            let e = g.latencies_ms.entry(provider.to_string()).or_insert(ms);
            *e = 0.7 * ms + 0.3 * *e;
        }
        self.persist.op(PersistOp::ProviderLatency {
            provider: provider.to_string(),
            latency_ms: ms,
        });
    }

    /// Providers never probed are assumed healthy — same as AstMatrix, which
    /// initialized its map empty and treated missing entries as healthy in
    /// every routing path.
    pub fn is_healthy(&self, provider: &str) -> bool {
        self.inner
            .read()
            .unwrap()
            .healthy
            .get(provider)
            .copied()
            .unwrap_or(true)
    }

    pub fn latency_ms(&self, provider: &str) -> Option<f64> {
        self.inner.read().unwrap().latencies_ms.get(provider).copied()
    }

    pub fn get_elo(&self, provider: &str) -> i32 {
        self.inner.read().unwrap().elos.get(provider).copied().unwrap_or(1500)
    }

    pub fn set_elo(&self, provider: &str, elo: i32) {
        self.inner
            .write()
            .unwrap()
            .elos
            .insert(provider.to_string(), elo);
        self.persist.op(PersistOp::ProviderElo {
            provider: provider.to_string(),
            elo,
        });
    }

    /// `SetSticky` — AstMatrix declared this but never called it from the
    /// router. Here the router calls it on every successful response, and
    /// expiry is enforced (persisted).
    pub fn set_sticky(&self, session: &str, provider: &str, ttl: Duration, now_unix: u64) {
        let expires = now_unix + ttl.as_secs();
        {
            let mut g = self.inner.write().unwrap();
            g.stickies
                .insert(session.to_string(), (provider.to_string(), expires));
        }
        self.persist.op(PersistOp::Sticky {
            session: session.to_string(),
            provider: provider.to_string(),
            expires_unix: expires,
        });
    }

    /// `GetSticky` with expiry enforced — expired pins are gone, not honored.
    pub fn get_sticky(&self, session: &str, now_unix: u64) -> Option<String> {
        let g = self.inner.read().unwrap();
        match g.stickies.get(session) {
            Some((p, exp)) if *exp > now_unix => Some(p.clone()),
            _ => None,
        }
    }

    pub fn sweep_expired_stickies(&self, now_unix: u64) -> usize {
        let removed = {
            let mut g = self.inner.write().unwrap();
            let before = g.stickies.len();
            g.stickies.retain(|_, (_, exp)| *exp > now_unix);
            before - g.stickies.len()
        };
        if removed > 0 {
            self.persist.op(PersistOp::StickySweep { now_unix });
        }
        removed
    }

    /// Snapshot for the operator API and persistence tick.
    pub fn snapshot(&self) -> Vec<ProviderHealthView> {
        let g = self.inner.read().unwrap();
        let mut providers: Vec<String> = g
            .healthy
            .keys()
            .chain(g.latencies_ms.keys())
            .chain(g.elos.keys())
            .map(|s| s.clone())
            .collect();
        providers.sort();
        providers.dedup();
        providers
            .into_iter()
            .map(|p| ProviderHealthView {
                provider: p.clone(),
                healthy: g.healthy.get(&p).copied().unwrap_or(true),
                latency_ms: g.latencies_ms.get(&p).copied(),
                elo: g.elos.get(&p).copied().unwrap_or(1500),
                last_probe_unix: g.last_probe_unix.get(&p).copied().unwrap_or(0),
            })
            .collect()
    }

    /// Apply a boot-restore payload (synchronous, before runtimes start).
    pub fn apply_restored(&self, r: &RestoredProviders) {
        let mut g = self.inner.write().unwrap();
        for row in &r.rows {
            g.healthy.insert(row.provider.clone(), row.healthy);
            g.last_probe_unix.insert(row.provider.clone(), row.last_probe_unix);
            if let Some(ms) = row.latency_ms {
                g.latencies_ms.insert(row.provider.clone(), ms);
            }
            g.elos.insert(row.provider.clone(), row.elo);
        }
        for s in &r.stickies {
            g.stickies.insert(
                s.session.clone(),
                (s.provider.clone(), s.expires_unix),
            );
        }
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct ProviderHealthView {
    pub provider: String,
    pub healthy: bool,
    pub latency_ms: Option<f64>,
    pub elo: i32,
    pub last_probe_unix: u64,
}

// ---------------------------------------------------------------------------
// Persistence ops -> writer thread
// ---------------------------------------------------------------------------

/// Lane-window row for persistence: key -> sorted unix-millis send stamps.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LaneWindowRow {
    pub key: String,
    pub sent_ms: Vec<u64>,
}

#[derive(Debug, Clone)]
pub enum PersistOp {
    ProviderHealthTouched {
        provider: String,
        healthy: bool,
        now_unix: u64,
    },
    ProviderLatency {
        provider: String,
        latency_ms: f64,
    },
    ProviderElo {
        provider: String,
        elo: i32,
    },
    Sticky {
        session: String,
        provider: String,
        expires_unix: u64,
    },
    StickySweep {
        now_unix: u64,
    },
    Circuit {
        provider: String,
        snap: CircuitSnapshot,
    },
    Governor {
        provider: String,
        model: String,
        snap: GovernorSnapshot,
    },
    LaneWindows {
        provider: String,
        rows: Vec<LaneWindowRow>,
    },
    Cooldown {
        provider: String,
        key: String,
        until_unix_ms: u64,
    },
    /// Periodic full-resync of provider health rows (the 30 s tick).
    FlushProviders {
        rows: Vec<ProviderStateRow>,
    },
    Imported,
    Shutdown,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ProviderStateRow {
    pub provider: String,
    pub healthy: bool,
    pub latency_ms: Option<f64>,
    pub elo: i32,
    pub last_probe_unix: u64,
}

#[derive(Debug, Clone, Default)]
pub struct RestoredSticky {
    pub session: String,
    pub provider: String,
    pub expires_unix: u64,
}

#[derive(Debug, Clone, Default)]
pub struct RestoredProviders {
    pub rows: Vec<ProviderStateRow>,
    pub stickies: Vec<RestoredSticky>,
}

#[derive(Debug, Clone, Default)]
pub struct RestoredRuntime {
    pub circuits: HashMap<String, CircuitSnapshot>,
    pub governors: HashMap<(String, String), GovernorSnapshot>,
    pub lane_windows: HashMap<String, Vec<LaneWindowRow>>, // provider -> rows
    pub cooldowns: HashMap<(String, String), u64>,          // (provider, key) -> until ms
}

/// A cheap cloneable handle to the persistence writer. `None` sender means
/// persistence is disabled (unit tests).
#[derive(Debug, Clone, Default)]
pub struct PersistHandle {
    tx: Option<Sender<PersistOp>>,
}

impl PersistHandle {
    pub fn disabled() -> Self {
        Self { tx: None }
    }

    pub fn is_enabled(&self) -> bool {
        self.tx.is_some()
    }

    pub fn op(&self, op: PersistOp) {
        if let Some(tx) = &self.tx {
            // The writer dying must never take the request path down.
            let _ = tx.send(op);
        }
    }
}

/// Owns the writer thread. `shutdown` flushes every queued op, then joins.
pub struct StateWriter {
    handle: PersistHandle,
    join: Option<std::thread::JoinHandle<()>>,
}

impl StateWriter {
    pub fn handle(&self) -> &PersistHandle {
        &self.handle
    }

    pub fn shutdown(mut self) {
        self.handle.op(PersistOp::Shutdown);
        if let Some(j) = self.join.take() {
            let _ = j.join();
        }
    }
}

// ---------------------------------------------------------------------------
// SQLite schema
// ---------------------------------------------------------------------------

const SCHEMA: &str = r#"
CREATE TABLE IF NOT EXISTS schema_meta (k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS provider_state (
    provider TEXT PRIMARY KEY,
    healthy INTEGER NOT NULL DEFAULT 1,
    latency_ms REAL,
    elo INTEGER NOT NULL DEFAULT 1500,
    last_probe_unix INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS sticky_sessions (
    session TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    expires_unix INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sticky_expires ON sticky_sessions(expires_unix);
CREATE TABLE IF NOT EXISTS circuits (
    provider TEXT PRIMARY KEY,
    state INTEGER NOT NULL DEFAULT 0,
    failures INTEGER NOT NULL DEFAULT 0,
    last_failure_unix INTEGER NOT NULL DEFAULT 0,
    consecutive_successes INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS governors (
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    worker_limit INTEGER NOT NULL,
    last_exhausted_unix INTEGER NOT NULL DEFAULT 0,
    last_adjusted_unix INTEGER NOT NULL DEFAULT 0,
    blocked_until_unix INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (provider, model)
);
CREATE TABLE IF NOT EXISTS lane_windows (
    provider TEXT NOT NULL,
    key TEXT NOT NULL,
    sent_ms TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (provider, key)
);
CREATE TABLE IF NOT EXISTS cooldowns (
    provider TEXT NOT NULL,
    key TEXT NOT NULL,
    until_unix_ms INTEGER NOT NULL,
    PRIMARY KEY (provider, key)
);
"#;

fn open_state_db(data_dir: &Path) -> Result<rusqlite::Connection, String> {
    std::fs::create_dir_all(data_dir)
        .map_err(|e| format!("cannot create data dir {}: {e}", data_dir.display()))?;
    let path = state_db_path(data_dir);
    let conn = rusqlite::Connection::open(&path)
        .map_err(|e| format!("cannot open {}: {e}", path.display()))?;
    conn.execute_batch("PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;")
        .map_err(|e| format!("pragma failed: {e}"))?;
    conn.execute_batch(SCHEMA)
        .map_err(|e| format!("schema failed: {e}"))?;
    conn.execute(
        "INSERT OR IGNORE INTO schema_meta (k, v) VALUES ('schema_version', '1')",
        [],
    )
    .map_err(|e| format!("meta failed: {e}"))?;
    Ok(conn)
}

/// Spawn the persistence writer thread. Returns the owner; the hot path uses
/// `writer.handle()`.
pub fn spawn_writer(data_dir: &Path) -> Result<StateWriter, String> {
    let conn = open_state_db(data_dir)?;
    let (tx, rx) = mpsc::channel::<PersistOp>();
    let join = std::thread::Builder::new()
        .name("flock-state-writer".into())
        .spawn(move || writer_loop(conn, rx))
        .map_err(|e| format!("cannot spawn state writer: {e}"))?;
    Ok(StateWriter {
        handle: PersistHandle { tx: Some(tx) },
        join: Some(join),
    })
}

fn writer_loop(conn: rusqlite::Connection, rx: mpsc::Receiver<PersistOp>) {
    for op in rx {
        if matches!(op, PersistOp::Shutdown) {
            break;
        }
        if let Err(e) = apply_op(&conn, op) {
            eprintln!("[flock-state] write failed: {e}");
        }
    }
}

fn apply_op(conn: &rusqlite::Connection, op: PersistOp) -> Result<(), String> {
    let err = |e: rusqlite::Error| e.to_string();
    match op {
        PersistOp::ProviderHealthTouched {
            provider,
            healthy,
            now_unix,
        } => {
            conn.execute(
                "INSERT INTO provider_state (provider, healthy, last_probe_unix)
                 VALUES (?1, ?2, ?3)
                 ON CONFLICT(provider) DO UPDATE SET healthy=excluded.healthy, last_probe_unix=excluded.last_probe_unix",
                rusqlite::params![provider, healthy as i32, now_unix as i64],
            )
            .map_err(err)?;
        }
        PersistOp::ProviderLatency {
            provider,
            latency_ms,
        } => {
            conn.execute(
                "INSERT INTO provider_state (provider, latency_ms) VALUES (?1, ?2)
                 ON CONFLICT(provider) DO UPDATE SET latency_ms=excluded.latency_ms",
                rusqlite::params![provider, latency_ms],
            )
            .map_err(err)?;
        }
        PersistOp::ProviderElo { provider, elo } => {
            conn.execute(
                "INSERT INTO provider_state (provider, elo) VALUES (?1, ?2)
                 ON CONFLICT(provider) DO UPDATE SET elo=excluded.elo",
                rusqlite::params![provider, elo],
            )
            .map_err(err)?;
        }
        PersistOp::Sticky {
            session,
            provider,
            expires_unix,
        } => {
            conn.execute(
                "INSERT INTO sticky_sessions (session, provider, expires_unix)
                 VALUES (?1, ?2, ?3)
                 ON CONFLICT(session) DO UPDATE SET provider=excluded.provider, expires_unix=excluded.expires_unix",
                rusqlite::params![session, provider, expires_unix as i64],
            )
            .map_err(err)?;
        }
        PersistOp::StickySweep { now_unix } => {
            conn.execute(
                "DELETE FROM sticky_sessions WHERE expires_unix <= ?1",
                rusqlite::params![now_unix as i64],
            )
            .map_err(err)?;
        }
        PersistOp::Circuit { provider, snap } => {
            conn.execute(
                "INSERT INTO circuits (provider, state, failures, last_failure_unix, consecutive_successes)
                 VALUES (?1, ?2, ?3, ?4, ?5)
                 ON CONFLICT(provider) DO UPDATE SET state=excluded.state, failures=excluded.failures,
                     last_failure_unix=excluded.last_failure_unix, consecutive_successes=excluded.consecutive_successes",
                rusqlite::params![
                    provider,
                    snap.state as i32,
                    snap.failures as i64,
                    snap.last_failure_unix as i64,
                    snap.consecutive_successes as i64
                ],
            )
            .map_err(err)?;
        }
        PersistOp::Governor {
            provider,
            model,
            snap,
        } => {
            conn.execute(
                "INSERT INTO governors (provider, model, worker_limit, last_exhausted_unix, last_adjusted_unix, blocked_until_unix)
                 VALUES (?1, ?2, ?3, ?4, ?5, ?6)
                 ON CONFLICT(provider, model) DO UPDATE SET worker_limit=excluded.worker_limit,
                     last_exhausted_unix=excluded.last_exhausted_unix, last_adjusted_unix=excluded.last_adjusted_unix,
                     blocked_until_unix=excluded.blocked_until_unix",
                rusqlite::params![
                    provider,
                    model,
                    snap.worker_limit as i64,
                    snap.last_exhausted_unix as i64,
                    snap.last_adjusted_unix as i64,
                    snap.blocked_until_unix as i64,
                ],
            )
            .map_err(err)?;
        }
        PersistOp::LaneWindows { provider, rows } => {
            let tx = conn.unchecked_transaction().map_err(err)?;
            {
                let mut stmt = tx
                    .prepare(
                        "INSERT INTO lane_windows (provider, key, sent_ms) VALUES (?1, ?2, ?3)
                         ON CONFLICT(provider, key) DO UPDATE SET sent_ms=excluded.sent_ms",
                    )
                    .map_err(err)?;
                for row in &rows {
                    let json = serde_json::to_string(&row.sent_ms).map_err(|e| e.to_string())?;
                    stmt.execute(rusqlite::params![provider, row.key, json])
                        .map_err(err)?;
                }
            }
            tx.commit().map_err(err)?;
        }
        PersistOp::Cooldown {
            provider,
            key,
            until_unix_ms,
        } => {
            conn.execute(
                "INSERT INTO cooldowns (provider, key, until_unix_ms) VALUES (?1, ?2, ?3)
                 ON CONFLICT(provider, key) DO UPDATE SET until_unix_ms=excluded.until_unix_ms",
                rusqlite::params![provider, key, until_unix_ms as i64],
            )
            .map_err(err)?;
        }
        PersistOp::FlushProviders { rows } => {
            let tx = conn.unchecked_transaction().map_err(err)?;
            {
                let mut stmt = tx
                    .prepare(
                        "INSERT INTO provider_state (provider, healthy, latency_ms, elo, last_probe_unix)
                         VALUES (?1, ?2, ?3, ?4, ?5)
                         ON CONFLICT(provider) DO UPDATE SET healthy=excluded.healthy, latency_ms=excluded.latency_ms,
                             elo=excluded.elo, last_probe_unix=excluded.last_probe_unix",
                    )
                    .map_err(err)?;
                for r in &rows {
                    stmt.execute(rusqlite::params![
                        r.provider,
                        r.healthy as i32,
                        r.latency_ms,
                        r.elo,
                        r.last_probe_unix as i64,
                    ])
                    .map_err(err)?;
                }
            }
            tx.commit().map_err(err)?;
        }
        PersistOp::Imported | PersistOp::Shutdown => {}
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Boot restore
// ---------------------------------------------------------------------------

/// Synchronous boot restore. Runs before any provider runtime starts.
/// Missing database = first boot: attempts the one-time AstMatrix import.
pub fn restore(data_dir: &Path, now_unix: u64) -> Result<(RestoredProviders, RestoredRuntime), String> {
    let path = state_db_path(data_dir);
    if !path.exists() {
        // First boot: try the one-time legacy import, then open fresh.
        let report = import_astmatrix(&astmatrix_db_default(), data_dir, now_unix).unwrap_or_default();
        if report.imported_anything() {
            eprintln!("[flock-state] imported AstMatrix state: {report:?}");
        }
    }
    let conn = open_state_db(data_dir)?;
    let err = |e: rusqlite::Error| e.to_string();

    let mut providers = RestoredProviders::default();
    {
        let mut stmt = conn
            .prepare("SELECT provider, healthy, latency_ms, elo, last_probe_unix FROM provider_state")
            .map_err(err)?;
        let rows = stmt
            .query_map([], |r| {
                Ok(ProviderStateRow {
                    provider: r.get(0)?,
                    healthy: r.get::<_, i32>(1)? != 0,
                    latency_ms: r.get(2)?,
                    elo: r.get(3)?,
                    last_probe_unix: r.get::<_, i64>(4)? as u64,
                })
            })
            .map_err(err)?;
        for r in rows {
            providers.rows.push(r.map_err(err)?);
        }
    }
    {
        // Expired stickies are dropped at restore: AstMatrix never enforced
        // expiry, so stale pins must not resurrect.
        let mut stmt = conn
            .prepare("SELECT session, provider, expires_unix FROM sticky_sessions WHERE expires_unix > ?1")
            .map_err(err)?;
        let rows = stmt
            .query_map([now_unix as i64], |r| {
                Ok(RestoredSticky {
                    session: r.get(0)?,
                    provider: r.get(1)?,
                    expires_unix: r.get::<_, i64>(2)? as u64,
                })
            })
            .map_err(err)?;
        for r in rows {
            providers.stickies.push(r.map_err(err)?);
        }
        conn.execute(
            "DELETE FROM sticky_sessions WHERE expires_unix <= ?1",
            [now_unix as i64],
        )
        .map_err(err)?;
    }

    let mut rt = RestoredRuntime::default();
    {
        let mut stmt = conn
            .prepare("SELECT provider, state, failures, last_failure_unix, consecutive_successes FROM circuits")
            .map_err(err)?;
        let rows = stmt
            .query_map([], |r| {
                Ok((
                    r.get::<_, String>(0)?,
                    CircuitSnapshot {
                        state: r.get::<_, i32>(1)? as u8,
                        failures: r.get::<_, i64>(2)? as u32,
                        last_failure_unix: r.get::<_, i64>(3)? as u64,
                        consecutive_successes: r.get::<_, i64>(4)? as u32,
                    },
                ))
            })
            .map_err(err)?;
        for r in rows {
            let (k, v) = r.map_err(err)?;
            rt.circuits.insert(k, v);
        }
    }
    {
        let mut stmt = conn
            .prepare("SELECT provider, model, worker_limit, last_exhausted_unix, last_adjusted_unix, blocked_until_unix FROM governors")
            .map_err(err)?;
        let rows = stmt
            .query_map([], |r| {
                Ok((
                    (r.get::<_, String>(0)?, r.get::<_, String>(1)?),
                    GovernorSnapshot {
                        worker_limit: r.get::<_, i64>(2)? as usize,
                        last_exhausted_unix: r.get::<_, i64>(3)? as u64,
                        last_adjusted_unix: r.get::<_, i64>(4)? as u64,
                        blocked_until_unix: r.get::<_, i64>(5)? as u64,
                    },
                ))
            })
            .map_err(err)?;
        for r in rows {
            let (k, v) = r.map_err(err)?;
            rt.governors.insert(k, v);
        }
    }
    {
        let mut stmt = conn
            .prepare("SELECT provider, key, sent_ms FROM lane_windows")
            .map_err(err)?;
        let rows = stmt
            .query_map([], |r| {
                Ok((
                    r.get::<_, String>(0)?,
                    LaneWindowRow {
                        key: r.get(1)?,
                        sent_ms: serde_json::from_str(&r.get::<_, String>(2)?).unwrap_or_default(),
                    },
                ))
            })
            .map_err(err)?;
        for r in rows {
            let (provider, row) = r.map_err(err)?;
            // Drop stale stamps: anything older than the 61 s window + grace
            // is dead weight. Keeping them would over-throttle after restart.
            let cutoff = now_unix.saturating_sub(120).saturating_mul(1000);
            let mut row = row;
            row.sent_ms.retain(|&ms| ms >= cutoff);
            rt.lane_windows.entry(provider).or_default().push(row);
        }
    }
    {
        let mut stmt = conn
            .prepare("SELECT provider, key, until_unix_ms FROM cooldowns WHERE until_unix_ms > ?1")
            .map_err(err)?;
        let rows = stmt
            .query_map([now_unix.saturating_mul(1000) as i64], |r| {
                Ok((
                    (r.get::<_, String>(0)?, r.get::<_, String>(1)?),
                    r.get::<_, i64>(2)? as u64,
                ))
            })
            .map_err(err)?;
        for r in rows {
            let (k, v) = r.map_err(err)?;
            rt.cooldowns.insert(k, v);
        }
        conn.execute(
            "DELETE FROM cooldowns WHERE until_unix_ms <= ?1",
            [now_unix.saturating_mul(1000) as i64],
        )
        .map_err(err)?;
    }
    Ok((providers, rt))
}

// ---------------------------------------------------------------------------
// One-time AstMatrix import
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Default)]
pub struct ImportReport {
    pub provider_rows: usize,
    pub sticky_rows: usize,
    pub extra_tables: Vec<String>,
}

impl ImportReport {
    pub fn imported_anything(&self) -> bool {
        self.provider_rows > 0 || self.sticky_rows > 0 || !self.extra_tables.is_empty()
    }
}

/// One-time migration from the legacy AstMatrix SQLite database into
/// `flock_state.db`. Credential values are never copied — only health,
/// latency, failure counts, ELO-relevant signals, and session affinity.
/// Extra AstMatrix tables (requests, model_health, healing_events,
/// rate_limit_events, session_affinity) are carried over verbatim for
/// continuity of the operator's history.
pub fn import_astmatrix(
    ast_path: &Path,
    data_dir: &Path,
    now_unix: u64,
) -> Result<ImportReport, String> {
    if !ast_path.exists() {
        return Ok(ImportReport::default());
    }
    let mut report = ImportReport::default();
    let conn = open_state_db(data_dir)?;
    let err = |e: rusqlite::Error| e.to_string();

    // ATTACH the legacy DB read-only under a fixed alias. Table names come
    // from our own constant list, never from the legacy file.
    let ast_uri = format!(
        "file:{}?mode=ro",
        ast_path.display().to_string().replace('\'', "''")
    );
    conn.execute_batch(&format!("ATTACH DATABASE '{ast_uri}' AS legacy;"))
        .map_err(err)?;

    let legacy_tables: Vec<String> = {
        let mut stmt = conn
            .prepare("SELECT name FROM legacy.sqlite_master WHERE type='table'")
            .map_err(err)?;
        let rows = stmt.query_map([], |r| r.get(0)).map_err(err)?;
        let x: Vec<String> = rows.collect::<Result<Vec<String>, _>>().map_err(err)?;
        x
    };

    // provider_health -> provider_state. AstMatrix's provider_health columns
    // (observed 2026-09-17): provider, healthy, latency_ms, failures,
    // last_probe, ... Map defensively by probing the actual columns.
    if legacy_tables.iter().any(|t| t == "provider_health") {
        let cols: Vec<String> = {
            let mut stmt = conn
                .prepare("SELECT name FROM pragma_table_info('provider_health', 'legacy')")
                .map_err(err)?;
            let rows = stmt.query_map([], |r| r.get(0)).map_err(err)?;
            let x: Vec<String> = rows.collect::<Result<Vec<String>, _>>().map_err(err)?;
            x
        };
        let has = |c: &str| cols.iter().any(|x| x == c);
        // Build a SELECT over the columns that exist.
        let mut select_cols: Vec<String> = vec!["provider".to_string()];
        for c in ["healthy", "latency_ms", "failures", "last_probe"] {
            if has(c) {
                select_cols.push(c.to_string());
            }
        }
        let sql = format!(
            "SELECT {} FROM legacy.provider_health",
            select_cols.join(", ")
        );
        let mut stmt = conn.prepare(&sql).map_err(err)?;
        let rows = stmt
            .query_map([], |r| {
                let provider: String = r.get(0)?;
                let mut idx = 1;
                let mut healthy = true;
                let mut latency_ms: Option<f64> = None;
                let mut failures: i64 = 0;
                let mut last_probe_unix: u64 = 0;
                for c in &select_cols[1..] {
                    match c.as_str() {
                        "healthy" => {
                            healthy = r.get::<_, i64>(idx)? != 0;
                            idx += 1;
                        }
                        "latency_ms" => {
                            latency_ms = r.get(idx)?;
                            idx += 1;
                        }
                        "failures" => {
                            failures = r.get(idx)?;
                            idx += 1;
                        }
                        "last_probe" => {
                            let s: Option<String> = r.get(idx)?;
                            if let Some(s) = s {
                                last_probe_unix = parse_rfc3339_unix(&s).unwrap_or(0);
                            }
                            idx += 1;
                        }
                        _ => {}
                    }
                }
                Ok((provider, healthy, latency_ms, failures, last_probe_unix))
            })
            .map_err(err)?;
        for r in rows {
            let (provider, healthy, latency_ms, failures, last_probe_unix) =
                r.map_err(err)?;
            // Repeated failure strikes depress the seeded ELO slightly, so
            // the weighted strategies don't prefer a historically flaky
            // provider on first boot.
            let elo = 1500 - (failures.min(20) as i32) * 5;
            conn.execute(
                "INSERT INTO provider_state (provider, healthy, latency_ms, elo, last_probe_unix)
                 VALUES (?1, ?2, ?3, ?4, ?5)
                 ON CONFLICT(provider) DO UPDATE SET healthy=excluded.healthy, latency_ms=excluded.latency_ms,
                     elo=excluded.elo, last_probe_unix=excluded.last_probe_unix",
                rusqlite::params![
                    provider,
                    healthy as i32,
                    latency_ms,
                    elo,
                    last_probe_unix as i64
                ],
            )
            .map_err(err)?;
            report.provider_rows += 1;
        }
    }

    // sticky_sessions -> sticky_sessions (expired rows dropped).
    if legacy_tables.iter().any(|t| t == "sticky_sessions") {
        let cols: Vec<String> = {
            let mut stmt = conn
                .prepare("SELECT name FROM pragma_table_info('sticky_sessions', 'legacy')")
                .map_err(err)?;
            let rows = stmt.query_map([], |r| r.get(0)).map_err(err)?;
            let x: Vec<String> = rows.collect::<Result<Vec<String>, _>>().map_err(err)?;
            x
        };
        let has = |c: &str| cols.iter().any(|x| x == c);
        // AstMatrix's sticky_sessions (observed): session_id, provider,
        // model, expires_at (RFC3339), created_at. Accept common variants.
        let sess_col = ["session_id", "session", "id"]
            .iter()
            .find(|c| has(c))
            .copied();
        let exp_col = ["expires_at", "expires_unix", "expires"]
            .iter()
            .find(|c| has(c))
            .copied();
        if let (Some(sc), Some(ec)) = (sess_col, exp_col) {
            let sql = format!(
                "SELECT {sc}, provider, {ec} FROM legacy.sticky_sessions"
            );
            let mut stmt = conn.prepare(&sql).map_err(err)?;
            let rows = stmt
                .query_map([], |r| {
                    let session: String = r.get(0)?;
                    let provider: String = r.get(1)?;
                    // expires may be RFC3339 text or unix int.
                    let as_int: Option<i64> = r.get(2).ok().flatten();
                    let as_text: Option<String> = r.get(2).ok().flatten();
                    let expires_unix = as_int
                        .map(|v| v as u64)
                        .or_else(|| as_text.as_deref().and_then(parse_rfc3339_unix))
                        .unwrap_or(0);
                    Ok((session, provider, expires_unix))
                })
                .map_err(err)?;
            for r in rows {
                let (session, provider, expires_unix) = r.map_err(err)?;
                if expires_unix <= now_unix {
                    continue;
                }
                conn.execute(
                    "INSERT OR IGNORE INTO sticky_sessions (session, provider, expires_unix)
                     VALUES (?1, ?2, ?3)",
                    rusqlite::params![session, provider, expires_unix as i64],
                )
                .map_err(err)?;
                report.sticky_rows += 1;
            }
        }
    }

    // Carry over the remaining AstMatrix history tables verbatim for the
    // operator's continuity. Table names are our constants, never input.
    for t in [
        "requests",
        "model_health",
        "healing_events",
        "rate_limit_events",
        "session_affinity",
    ] {
        if legacy_tables.iter().any(|x| x == t) {
            let target = format!("ast_{t}");
            conn.execute_batch(&format!(
                "DROP TABLE IF EXISTS {target}; CREATE TABLE {target} AS SELECT * FROM legacy.{t};"
            ))
            .map_err(err)?;
            report.extra_tables.push(t.to_string());
        }
    }

    conn.execute_batch("DETACH DATABASE legacy;").map_err(err)?;
    conn.execute(
        "INSERT OR IGNORE INTO schema_meta (k, v) VALUES ('astmatrix_imported_unix', ?1)",
        [now_unix as i64],
    )
    .map_err(err)?;
    Ok(report)
}

/// Minimal RFC3339 parser (no extra deps): "2026-09-17T13:18:13-06:00".
/// Accepts a space separator and fractional seconds leniently.
fn parse_rfc3339_unix(s: &str) -> Option<u64> {
    let s = s.trim();
    let (date, time) = s.split_once('T').or_else(|| s.split_once(' '))?;
    let (y, md) = date.split_once('-')?;
    let (mo, d) = md.split_once('-')?;
    if time.len() < 8 {
        return None;
    }
    let (time_part, tz_part) = time.split_at(8); // "13:18:13" | "-06:00" / ".123-06:00" / "Z" / ""
    // Strip fractional seconds from the zone designator.
    let tz_part = match tz_part.find(|c| c == '+' || c == '-' || c == 'Z') {
        Some(i) => &tz_part[i..],
        None => "",
    };
    let y: i64 = y.parse().ok()?;
    let mo: i64 = mo.parse().ok()?;
    let d: i64 = d.parse().ok()?;
    let mut ti = time_part.split(':');
    let hh: i64 = ti.next()?.parse().ok()?;
    let mm: i64 = ti.next()?.parse().ok()?;
    let ss: i64 = ti.next()?.parse().ok()?;
    let off_secs: i64 = parse_tz_offset(tz_part)?;
    let days: i64 = days_from_civil(y, mo, d)? as i64;
    Some((days * 86400 + hh * 3600 + mm * 60 + ss - off_secs) as u64)
}

fn parse_tz_offset(off: &str) -> Option<i64> {
    if off.is_empty() || off == "Z" {
        return Some(0);
    }
    let sign = match off.chars().next()? {
        '+' => 1,
        '-' => -1,
        _ => return None,
    };
    let rest = &off[1..].replace(':', "");
    if rest.len() != 4 {
        return None;
    }
    let hh: i64 = rest[..2].parse().ok()?;
    let mm: i64 = rest[2..].parse().ok()?;
    Some(sign * (hh * 3600 + mm * 60))
}

fn days_from_civil(y: i64, m: i64, d: i64) -> Option<u64> {
    if !(2000..=2100).contains(&y) || !(1..=12).contains(&m) || !(1..=31).contains(&d) {
        return None;
    }
    let y = if m <= 2 { y - 1 } else { y };
    let era = y.div_euclid(400);
    let yoe = y.rem_euclid(400);
    let mp = (m + 9).rem_euclid(12);
    let doy = (153 * mp + 2) / 5 + d - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    let days = era * 146097 + doe - 719468;
    Some(days as u64)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    fn test_db(dir: &Path) -> (HealthDb, StateWriter) {
        let w = spawn_writer(dir).expect("spawn writer");
        let h = HealthDb::new(w.handle().clone());
        (h, w)
    }

    #[test]
    fn ema_latency_matches_astmatrix_math() {
        let dir = tempfile_like();
        let (h, _p) = test_db(&dir);
        h.record_latency("openrouter", Duration::from_millis(100));
        assert_eq!(h.latency_ms("openrouter"), Some(100.0));
        h.record_latency("openrouter", Duration::from_millis(200));
        // 0.7*200 + 0.3*100 = 170
        assert!((h.latency_ms("openrouter").unwrap() - 170.0).abs() < 1e-9);
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn unknown_provider_assumed_healthy() {
        let dir = tempfile_like();
        let (h, _p) = test_db(&dir);
        assert!(h.is_healthy("never-seen"));
        h.record_health("x", false, 1);
        assert!(!h.is_healthy("x"));
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn sticky_expiry_enforced() {
        let dir = tempfile_like();
        let (h, _p) = test_db(&dir);
        h.set_sticky("sess", "openrouter", Duration::from_secs(60), 1000);
        assert_eq!(h.get_sticky("sess", 1059).as_deref(), Some("openrouter"));
        assert_eq!(h.get_sticky("sess", 1060), None);
        assert_eq!(h.get_sticky("sess", 1061), None);
        assert_eq!(h.sweep_expired_stickies(2000), 1);
        assert_eq!(h.sweep_expired_stickies(2000), 0);
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn provider_state_round_trips_through_sqlite() {
        let dir = tempfile_like();
        let (h, w) = test_db(&dir);
        let p = w.handle().clone();
        h.record_health("groq", false, 4242);
        h.record_latency("groq", Duration::from_millis(64));
        h.set_elo("groq", 1580);
        h.set_sticky("s1", "groq", Duration::from_secs(3600), 4242);
        // Also exercise direct ops for circuit/governor/lane/cooldown rows.
        p.op(PersistOp::Circuit {
            provider: "groq".into(),
            snap: CircuitSnapshot {
                state: 2,
                failures: 5,
                last_failure_unix: 4242,
                consecutive_successes: 0,
            },
        });
        p.op(PersistOp::Governor {
            provider: "groq".into(),
            model: "m".into(),
            snap: crate::governor::GovernorSnapshot {
                worker_limit: 4,
                last_exhausted_unix: 4200,
                last_adjusted_unix: 4200,
                blocked_until_unix: 4300,
            },
        });
        p.op(PersistOp::LaneWindows {
            provider: "groq".into(),
            rows: vec![LaneWindowRow {
                key: "k".into(),
                sent_ms: vec![4242000],
            }],
        });
        p.op(PersistOp::Cooldown {
            provider: "groq".into(),
            key: "k".into(),
            until_unix_ms: 9999999999999,
        });
        drop(p);
        drop(h);
        // Shutdown flushes every queued op before joining, so restore()
        // below observes exactly what was written.
        w.shutdown();
        // Reopen synchronously and verify everything survived.
        let (prov, rt) = restore(&dir, 5000).expect("restore");
        let row = prov.rows.iter().find(|r| r.provider == "groq").expect("row");
        assert!(!row.healthy);
        assert!(row.latency_ms.is_some());
        assert_eq!(row.elo, 1580);
        assert_eq!(row.last_probe_unix, 4242);
        assert_eq!(prov.stickies.len(), 1);
        assert_eq!(prov.stickies[0].session, "s1");
        let snap = rt.circuits.get("groq").expect("circuit");
        assert_eq!(snap.state, 2);
        assert_eq!(snap.failures, 5);
        let gov = rt.governors.get(&("groq".to_string(), "m".to_string())).expect("gov");
        assert_eq!(gov.worker_limit, 4);
        assert_eq!(gov.blocked_until_unix, 4300);
        let lanes = rt.lane_windows.get("groq").expect("lanes");
        assert_eq!(lanes[0].key, "k");
        // The 4242000 ms stamp is older than now-120s cutoff (5000-120)*1000
        // = 4880000, so it was correctly pruned as stale.
        assert!(lanes[0].sent_ms.is_empty());
        assert_eq!(
            rt.cooldowns.get(&("groq".to_string(), "k".to_string())),
            Some(&9999999999999)
        );
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn expired_stickies_dropped_at_restore() {
        let dir = tempfile_like();
        let w = spawn_writer(&dir).expect("spawn");
        w.handle().op(PersistOp::Sticky {
            session: "old".into(),
            provider: "x".into(),
            expires_unix: 100,
        });
        w.shutdown();
        let (prov, _) = restore(&dir, 9999).expect("restore");
        assert!(prov.stickies.is_empty());
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn astmatrix_import_maps_provider_health_and_drops_expired_sticky() {
        let dir = tempfile_like();
        let ast_dir = tempfile_like();
        let ast_path = ast_dir.join("ast_matrix.db");
        // Build a synthetic legacy DB with AstMatrix's observed shape.
        {
            let conn = rusqlite::Connection::open(&ast_path).unwrap();
            conn.execute_batch(
                "CREATE TABLE provider_health (provider TEXT PRIMARY KEY, healthy INTEGER, latency_ms REAL, failures INTEGER, last_probe TEXT);
                 CREATE TABLE sticky_sessions (session_id TEXT PRIMARY KEY, provider TEXT, model TEXT, expires_at TEXT, created_at TEXT);
                 CREATE TABLE requests (id INTEGER PRIMARY KEY, provider TEXT);
                 CREATE TABLE model_health (provider TEXT, model TEXT);",
            )
            .unwrap();
            conn.execute(
                "INSERT INTO provider_health VALUES ('nvidia', 1, 133.0, 0, '2026-09-17T13:18:13-06:00')",
                [],
            )
            .unwrap();
            conn.execute(
                "INSERT INTO provider_health VALUES ('github', 0, NULL, 12, '2026-09-17T13:18:14-06:00')",
                [],
            )
            .unwrap();
            conn.execute(
                "INSERT INTO sticky_sessions VALUES ('live', 'nvidia', 'm', '2026-09-17T14:18:13-06:00', '2026-09-17T13:18:13-06:00')",
                [],
            )
            .unwrap();
            conn.execute(
                "INSERT INTO sticky_sessions VALUES ('dead', 'groq', 'm', '2026-09-17T12:00:00-06:00', '2026-09-17T11:00:00-06:00')",
                [],
            )
            .unwrap();
            conn.execute("INSERT INTO requests (provider) VALUES ('nvidia')", [])
                .unwrap();
            conn.execute(
                "INSERT INTO model_health VALUES ('nvidia', 'm')",
                [],
            )
            .unwrap();
        }
        // now_unix chosen between the two sticky expiries:
        // 'live' expires 14:18:13-06:00 = 20:18:13Z; 'dead' 12:00-06:00 = 18:00Z.
        // 2026-09-17T19:00:00Z = ?
        let now_unix = days_from_civil(2026, 9, 17).unwrap() * 86400 + 19 * 3600;
        let report = import_astmatrix(&ast_path, &dir, now_unix).expect("import");
        assert_eq!(report.provider_rows, 2);
        assert_eq!(report.sticky_rows, 1);
        assert!(report.extra_tables.contains(&"requests".to_string()));
        assert!(report.extra_tables.contains(&"model_health".to_string()));

        let (prov, _) = restore(&dir, now_unix).expect("restore");
        let nv = prov.rows.iter().find(|r| r.provider == "nvidia").unwrap();
        assert!(nv.healthy);
        assert_eq!(nv.latency_ms, Some(133.0));
        assert_eq!(nv.elo, 1500); // 0 failures: no depression
        let gh = prov.rows.iter().find(|r| r.provider == "github").unwrap();
        assert!(!gh.healthy);
        assert_eq!(gh.elo, 1500 - 12 * 5); // strikes depress the seed
        assert_eq!(prov.stickies.len(), 1);
        assert_eq!(prov.stickies[0].session, "live");
        // The verbatim history tables exist under the ast_ prefix.
        let conn = rusqlite::Connection::open(state_db_path(&dir)).unwrap();
        let n: i64 = conn
            .query_row("SELECT COUNT(*) FROM ast_requests", [], |r| r.get(0))
            .unwrap();
        assert_eq!(n, 1);
        std::fs::remove_dir_all(&dir).ok();
        std::fs::remove_dir_all(&ast_dir).ok();
    }

    #[test]
    fn missing_legacy_db_imports_nothing() {
        let dir = tempfile_like();
        let report = import_astmatrix(
            &dir.join("nope.db"),
            &dir,
            1_000_000,
        )
        .expect("import");
        assert!(!report.imported_anything());
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn rfc3339_parses_with_offset() {
        // 2026-09-17T13:18:13-06:00 == 2026-09-17T19:18:13Z
        let a = parse_rfc3339_unix("2026-09-17T13:18:13-06:00").unwrap();
        let b = parse_rfc3339_unix("2026-09-17T19:18:13Z").unwrap();
        assert_eq!(a, b);
        assert!(parse_rfc3339_unix("not-a-date").is_none());
    }

    fn tempfile_like() -> PathBuf {
        let d = std::env::temp_dir().join(format!(
            "flock-health-test-{}-{}",
            std::process::id(),
            rand_suffix()
        ));
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    fn rand_suffix() -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        let mut h = DefaultHasher::new();
        std::time::SystemTime::now().hash(&mut h);
        std::thread::current().id().hash(&mut h);
        h.finish()
    }
}
