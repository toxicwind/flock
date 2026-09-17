//! Provider model — Flock's multi-provider core.
//!
//! This module genuinely absorbs AstMatrix's provider registry: its 13
//! built-in provider definitions, model lists, ELO scores, weights, free-tier
//! flags, and key-resolution rules are re-expressed here as native Rust, with
//! no adapter over the old Go code. Nothing is a wrapper, alias, shim, or
//! monkey-patch; there is one implementation and it lives here.
//!
//! Fidelity notes (see `MIGRATION.md` for the full account):
//! - AstMatrix's `Provider` carried `APIKey` resolved from `KeyEnv` at
//!   startup, `NoAuth`, `FreeTier`, `Models`, `ModelMap`, `Weight`, `ELO`.
//!   All of those are real fields here.
//! - AstMatrix's `MaxParallel` was declared but never enforced by its race
//!   path; here `max_parallel` is actually enforced in the router.

use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;

use serde::{Deserialize, Serialize};
use utoipa::ToSchema;

/// Buffered-request coalescing window. AstMatrix instantiated its
/// `RequestCoalescer` with a 5 s TTL but never called it; here the TTL is
/// real and the coalescer sits on the buffered request path.
pub const COALESCER_TTL: Duration = Duration::from_secs(5);

/// How a provider authenticates upstream requests.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum AuthScheme {
    /// Bearer API key(s) from [`ProviderKey`].
    #[default]
    ApiKey,
    /// No `Authorization` header is sent at all.
    None,
}

/// One upstream key for a provider. Mirrors AstMatrix's per-provider key
/// resolution: an explicit key wins, otherwise `key_env` is read from the
/// process environment.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderKey {
    #[serde(default)]
    pub key: String,
    #[serde(default)]
    pub key_env: String,
    #[serde(default = "default_owner")]
    pub owner: String,
    #[serde(default = "default_true")]
    pub enabled: bool,
    /// Requests-per-minute budget for this key's lane. Defaults to
    /// AstMatrix's 60 RPM for paid providers, 10 RPM for free-tier ones.
    #[serde(default)]
    pub rpm: usize,
}

fn default_owner() -> String {
    "default".to_string()
}
fn default_true() -> bool {
    true
}

impl Default for ProviderKey {
    fn default() -> Self {
        Self {
            key: String::new(),
            key_env: String::new(),
            owner: default_owner(),
            enabled: true,
            rpm: 0,
        }
    }
}

/// Resolve a key record to usable key material: the literal key, falling back
/// to the environment variable. Mirrors AstMatrix's `resolveAPIKey`.
pub fn resolve_key_material(key: &ProviderKey) -> Option<String> {
    if !key.key.is_empty() {
        return Some(key.key.clone());
    }
    if !key.key_env.is_empty() {
        if let Ok(v) = std::env::var(&key.key_env) {
            let v = v.trim().to_string();
            if !v.is_empty() {
                return Some(v);
            }
        }
    }
    None
}

/// The routing strategy for a model with more than one usable provider.
/// Names intentionally match AstMatrix's configured strategy identifiers so
/// existing Herd/router configs keep meaning them.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default, ToSchema)]
#[serde(rename_all = "snake_case")]
pub enum Strategy {
    /// Try candidates in order, with circuit/limiter/health gates per
    /// attempt (AstMatrix `hybrid` semantics, minus its 4xx-as-usable bug).
    #[default]
    Hybrid,
    /// Fan out to every candidate and take the first usable, non-empty,
    /// correct response (`ast_race`).
    AstRace,
    /// Prefer the session's pinned provider (`sticky_affinity`).
    StickyAffinity,
    /// ELO-weighted random choice (`weighted_elo`).
    WeightedElo,
    /// Lowest recent latency first (`least_latency`).
    LeastLatency,
    /// Simple rotation across candidates (`round_robin`).
    RoundRobin,
    /// Race only free-tier providers (`free`).
    Free,
    /// Walk candidates in order until one returns a usable response
    /// (`circuit_chain`).
    CircuitChain,
}

impl Strategy {
    /// Parse a strategy name the way Herd config files spell them.
    pub fn parse(name: &str) -> Option<Strategy> {
        match name {
            "hybrid" => Some(Strategy::Hybrid),
            "ast_race" => Some(Strategy::AstRace),
            "sticky_affinity" => Some(Strategy::StickyAffinity),
            "weighted_elo" => Some(Strategy::WeightedElo),
            "least_latency" => Some(Strategy::LeastLatency),
            "round_robin" => Some(Strategy::RoundRobin),
            "free" => Some(Strategy::Free),
            "circuit_chain" => Some(Strategy::CircuitChain),
            _ => None,
        }
    }
}

/// Provider-wide routing knobs. Serde defaults keep old configs loading.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoutingCfg {
    #[serde(default)]
    pub strategy: Strategy,
    /// Bounded fan-out for `ast_race` / `free`: the maximum number of
    /// concurrent upstream attempts. AstMatrix declared this but never
    /// enforced it; here it is enforced.
    #[serde(default = "default_max_parallel")]
    pub max_parallel: usize,
    /// Failover rounds across candidates before giving up.
    #[serde(default = "default_max_retries")]
    pub max_retries: usize,
    /// Sticky-affinity pin TTL, seconds.
    #[serde(default = "default_sticky_ttl")]
    pub sticky_ttl_secs: u64,
    /// Maximum coalesced buffered requests waiting (AstMatrix declared
    /// `FifoMax` but never used it; the router enforces this as the FIFO
    /// admission bound).
    #[serde(default = "default_fifo_max")]
    pub fifo_max: usize,
    /// Coalesce identical in-flight buffered requests into one upstream
    /// call. AstMatrix instantiated its coalescer but never invoked it; here
    /// it is on the request path.
    #[serde(default = "default_true")]
    pub enable_coalescing: bool,
    /// Health-probe interval, seconds. AstMatrix defaulted to 30.
    #[serde(default = "default_probe_interval")]
    pub probe_interval_secs: u64,
}

fn default_probe_interval() -> u64 {
    30
}

impl RoutingCfg {
    /// Sticky-affinity pin TTL as a `Duration`.
    pub fn sticky_ttl(&self) -> Duration {
        Duration::from_secs(self.sticky_ttl_secs.max(1))
    }

    /// Health-probe interval as a `Duration`. Zero disables probing (the
    /// router falls back to its own default).
    pub fn probe_interval(&self) -> Option<Duration> {
        if self.probe_interval_secs == 0 {
            None
        } else {
            Some(Duration::from_secs(self.probe_interval_secs))
        }
    }
}

fn default_max_parallel() -> usize {
    8
}
fn default_max_retries() -> usize {
    3
}
fn default_sticky_ttl() -> u64 {
    3600
}
fn default_fifo_max() -> usize {
    512
}

impl Default for RoutingCfg {
    fn default() -> Self {
        Self {
            strategy: Strategy::default(),
            max_parallel: default_max_parallel(),
            max_retries: default_max_retries(),
            sticky_ttl_secs: default_sticky_ttl(),
            fifo_max: default_fifo_max(),
            enable_coalescing: true,
            probe_interval_secs: default_probe_interval(),
        }
    }
}

/// One upstream provider. AstMatrix's `Provider` struct, natively.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderDef {
    /// Stable identifier: `nvidia`, `openrouter`, ... Matches AstMatrix IDs
    /// so Herd config references keep resolving.
    pub name: String,
    #[serde(default)]
    pub base_url: String,
    #[serde(default)]
    pub auth: AuthScheme,
    #[serde(default)]
    pub keys: Vec<ProviderKey>,
    #[serde(default)]
    pub no_auth: bool,
    #[serde(default)]
    pub free_tier: bool,
    #[serde(default)]
    pub models: Vec<String>,
    /// Upstream model id -> id to actually request. AstMatrix's `ModelMap`.
    #[serde(default)]
    pub model_map: HashMap<String, String>,
    /// ELO selection weight.
    #[serde(default = "default_weight")]
    pub weight: f64,
    /// Quality score, seeded from AstMatrix's registry values.
    #[serde(default = "default_elo")]
    pub elo: i32,
    /// Requests-per-minute budget applied when a key has `rpm == 0`.
    #[serde(default)]
    pub default_rpm: usize,
    /// Human label for the dashboard.
    #[serde(default)]
    pub display_name: String,
    /// Operational on/off switch independent of key material.
    #[serde(default = "default_true")]
    pub enabled: bool,
}

fn default_weight() -> f64 {
    1.0
}
fn default_elo() -> i32 {
    1500
}

impl Default for ProviderDef {
    fn default() -> Self {
        Self {
            name: String::new(),
            base_url: String::new(),
            auth: AuthScheme::ApiKey,
            keys: Vec::new(),
            no_auth: false,
            free_tier: false,
            models: Vec::new(),
            model_map: HashMap::new(),
            weight: 1.0,
            elo: 1500,
            default_rpm: 0,
            display_name: String::new(),
            enabled: true,
        }
    }
}

impl ProviderDef {
    /// Effective RPM for a key: explicit per-key rpm, else the provider
    /// default, else AstMatrix's 60/10 rule.
    pub fn rpm_for(&self, key: &ProviderKey) -> usize {
        if key.rpm > 0 {
            return key.rpm;
        }
        if self.default_rpm > 0 {
            return self.default_rpm;
        }
        if self.free_tier {
            10
        } else {
            60
        }
    }

    /// Whether this provider can serve traffic right now: enabled, and
    /// either no-auth or at least one enabled key with resolvable material.
    pub fn usable(&self) -> bool {
        if !self.enabled {
            return false;
        }
        if self.no_auth || self.auth == AuthScheme::None {
            return true;
        }
        self.keys
            .iter()
            .any(|k| k.enabled && resolve_key_material(k).is_some())
    }

    /// Enabled keys that currently resolve to key material.
    pub fn live_keys(&self) -> Vec<(String, usize)> {
        self.keys
            .iter()
            .filter(|k| k.enabled)
            .filter_map(|k| resolve_key_material(k).map(|m| (m, self.rpm_for(k))))
            .collect()
    }

    /// Rewrite the requested model id through this provider's model map.
    /// Returns the id to actually send upstream.
    pub fn map_model<'a>(&'a self, model: &'a str) -> &'a str {
        self.model_map
            .get(model)
            .map(|s| s.as_str())
            .unwrap_or(model)
    }

    /// Owned version of [`Self::map_model`] for the router's candidates.
    pub fn rewrite_model(&self, model: &str) -> String {
        self.map_model(model).to_owned()
    }

    /// Whether this provider serves `model`: listed in `models`, or the
    /// models list carries the `"*"` wildcard (the old NVIDIA proxy passed
    /// any requested model through, and migrated providers keep that).
    pub fn serves_model(&self, model: &str) -> bool {
        self.models.iter().any(|m| m == "*" || m == model)
    }

    /// The upstream id for `model` differs from the requested one.
    pub fn model_rewritten(&self, model: &str) -> bool {
        self.model_map.contains_key(model)
    }

    /// Lane specs for this provider's key pool: one lane per key with
    /// resolvable material (literal or `key_env`), deduplicated by material.
    /// Disabled keys ride along as state carriers so a disable→enable cycle
    /// can't reset their windows — exactly the old pool's contract.
    pub fn lane_specs(&self) -> Vec<crate::pool::LaneSpec> {
        let mut seen = std::collections::HashSet::new();
        self.keys
            .iter()
            .filter_map(|k| {
                let material = resolve_key_material(k)?;
                if material.is_empty() || !seen.insert(material.clone()) {
                    return None;
                }
                Some(crate::pool::LaneSpec {
                    key: material,
                    rpm: self.rpm_for(k),
                    enabled: k.enabled,
                })
            })
            .collect()
    }
}

/// The live provider registry with a by-model candidate index.
#[derive(Debug, Clone, Default)]
pub struct ProviderSet {
    pub providers: Vec<ProviderDef>,
    by_model: HashMap<String, Vec<usize>>,
}

impl ProviderSet {
    pub fn new(mut providers: Vec<ProviderDef>) -> Self {
        // The store author decides provider precedence; within a provider,
        // AstMatrix semantics are preserved.
        let mut by_model: HashMap<String, Vec<usize>> = HashMap::new();
        for (i, p) in providers.iter().enumerate() {
            for m in &p.models {
                by_model.entry(m.clone()).or_default().push(i);
            }
        }
        // Wildcard entries ("" or "*") catch models no provider lists.
        let wildcards: Vec<usize> = providers
            .iter()
            .enumerate()
            .filter(|(_, p)| p.models.iter().any(|m| m == "*" || m == ""))
            .map(|(i, _)| i)
            .collect();
        if !wildcards.is_empty() {
            // stored under a sentinel; for_model merges them in
            by_model.insert(String::new(), wildcards);
        }
        let _ = &mut providers;
        Self {
            providers,
            by_model,
        }
    }

    pub fn get(&self, name: &str) -> Option<&ProviderDef> {
        self.providers.iter().find(|p| p.name == name)
    }

    /// All providers that list `model`, in registry order, plus wildcard
    /// providers. Empty when nothing claims the model.
    pub fn candidates<'a>(&'a self, model: &str) -> Vec<&'a ProviderDef> {
        let mut out: Vec<&'a ProviderDef> = Vec::new();
        if let Some(idxs) = self.by_model.get(model) {
            for &i in idxs {
                out.push(&self.providers[i]);
            }
        }
        if let Some(wild) = self.by_model.get("") {
            for &i in wild {
                let p = &self.providers[i];
                if !out.iter().any(|q| q.name == p.name) {
                    out.push(p);
                }
            }
        }
        out
    }

    /// Candidates that can actually serve right now.
    pub fn usable_candidates<'a>(&'a self, model: &str) -> Vec<&'a ProviderDef> {
        self.candidates(model)
            .into_iter()
            .filter(|p| p.usable())
            .collect()
    }
}

/// AstMatrix's 13 built-in providers, with their upstream base URLs, key
/// environment variables, model lists, weights, and ELO seeds — exactly as
/// `providers.go` declares them. Key material is never stored here; each
/// entry names the env var AstMatrix resolved.
pub fn default_providers() -> Vec<ProviderDef> {
    let mut v = Vec::with_capacity(13);
    let mut p = |name: &str,
                 base_url: &str,
                 key_env: &str,
                 no_auth: bool,
                 free_tier: bool,
                 models: &[&str],
                 weight: f64,
                 elo: i32| {
        v.push(ProviderDef {
            name: name.to_string(),
            base_url: base_url.to_string(),
            auth: if no_auth {
                AuthScheme::None
            } else {
                AuthScheme::ApiKey
            },
            keys: if key_env.is_empty() {
                Vec::new()
            } else {
                vec![ProviderKey {
                    key_env: key_env.to_string(),
                    ..ProviderKey::default()
                }]
            },
            no_auth,
            free_tier,
            models: models.iter().map(|s| s.to_string()).collect(),
            weight,
            elo,
            display_name: name.to_string(),
            enabled: true,
            ..ProviderDef::default()
        });
    };

    // Canonical defaults, line-for-line from
    // projects/herd/internal/astmatrix/providers.go (defaultProviders).
    p(
        "llama-swap",
        "http://127.0.0.1:25100/v1",
        "",
        true,
        false,
        &["local-fast", "local-quality", "local-longctx"],
        1.0,
        1600,
    );
    p(
        "openrouter",
        "https://openrouter.ai/api/v1",
        "OPENROUTER_API_KEY",
        false,
        false,
        &["openrouter/auto", "openrouter/optimus-alpha"],
        1.0,
        1500,
    );
    p(
        "nvidia",
        "https://integrate.api.nvidia.com/v1",
        "NVIDIA_API_KEY",
        false,
        true,
        &[
            "nvidia/llama-3.1-nemotron-70b",
            "nvidia/mistral-7b-instruct",
        ],
        1.2,
        1550,
    );
    p(
        "groq",
        "https://api.groq.com/openai/v1",
        "GROQ_API_KEY",
        false,
        true,
        &["groq/llama-3.1-70b-versatile", "groq/mixtral-8x7b"],
        1.5,
        1580,
    );
    p(
        "together",
        "https://api.together.xyz/v1",
        "TOGETHER_API_KEY",
        false,
        false,
        &["together/llama-3.1-70b", "together/mixtral-8x22b"],
        1.0,
        1520,
    );
    p(
        "cerebras",
        "https://api.cerebras.ai/v1",
        "CEREBRAS_API_KEY",
        false,
        true,
        &["cerebras/llama-3.1-70b"],
        1.3,
        1560,
    );
    p(
        "fireworks",
        "https://api.fireworks.ai/inference/v1",
        "FIREWORKS_API_KEY",
        false,
        false,
        &["fireworks/llama-3.1-70b", "fireworks/mixtral-8x22b"],
        1.0,
        1510,
    );
    p(
        "hyperbolic",
        "https://api.hyperbolic.xyz/v1",
        "HYPERBOLIC_API_KEY",
        false,
        true,
        &["hyperbolic/llama-3.1-70b"],
        1.0,
        1490,
    );
    p(
        "github",
        "https://models.inference.ai.azure.com",
        "GITHUB_TOKEN",
        false,
        true,
        &["github/Phi-4", "github/gpt-4o-mini"],
        1.0,
        1500,
    );
    p(
        "mistral",
        "https://api.mistral.ai/v1",
        "MISTRAL_API_KEY",
        false,
        false,
        &["mistral/mistral-large-2"],
        1.0,
        1530,
    );
    p(
        "openai",
        "https://api.openai.com/v1",
        "OPENAI_API_KEY",
        false,
        false,
        &["gpt-4o", "gpt-4o-mini", "o1-preview"],
        1.0,
        1650,
    );
    p(
        "perplexity",
        "https://api.perplexity.ai",
        "PERPLEXITY_API_KEY",
        false,
        false,
        &["perplexity/sonar"],
        1.0,
        1480,
    );
    p(
        "siliconflow",
        "https://api.siliconflow.cn/v1",
        "SILICONFLOW_API_KEY",
        false,
        true,
        &["siliconflow/deepseek-v2"],
        1.0,
        1470,
    );
    v
}

/// A generation of provider runtimes shared with request handlers.
pub type SharedSet = Arc<ProviderSet>;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn thirteen_builtin_providers() {
        let defs = default_providers();
        assert_eq!(defs.len(), 13);
        let names: Vec<&str> = defs.iter().map(|p| p.name.as_str()).collect();
        for expected in [
            "llama-swap",
            "openrouter",
            "nvidia",
            "groq",
            "together",
            "cerebras",
            "fireworks",
            "hyperbolic",
            "github",
            "mistral",
            "openai",
            "perplexity",
            "siliconflow",
        ] {
            assert!(names.contains(&expected), "missing {expected}");
        }
    }

    #[test]
    fn key_resolution_prefers_literal_then_env() {
        std::env::set_var("FLOCK_TEST_KEY_ENV_X", "env-secret");
        let k = ProviderKey {
            key: "literal".into(),
            key_env: "FLOCK_TEST_KEY_ENV_X".into(),
            ..ProviderKey::default()
        };
        assert_eq!(resolve_key_material(&k).as_deref(), Some("literal"));
        let k2 = ProviderKey {
            key_env: "FLOCK_TEST_KEY_ENV_X".into(),
            ..ProviderKey::default()
        };
        assert_eq!(resolve_key_material(&k2).as_deref(), Some("env-secret"));
        let k3 = ProviderKey {
            key_env: "FLOCK_TEST_KEY_ENV_MISSING".into(),
            ..ProviderKey::default()
        };
        assert_eq!(resolve_key_material(&k3), None);
        std::env::remove_var("FLOCK_TEST_KEY_ENV_X");
    }

    #[test]
    fn rpm_falls_back_through_provider_default_to_astmatrix_rule() {
        let mut p = ProviderDef {
            free_tier: true,
            ..ProviderDef::default()
        };
        let k = ProviderKey::default();
        assert_eq!(p.rpm_for(&k), 10);
        p.free_tier = false;
        assert_eq!(p.rpm_for(&k), 60);
        p.default_rpm = 120;
        assert_eq!(p.rpm_for(&k), 120);
        let k2 = ProviderKey {
            rpm: 7,
            ..ProviderKey::default()
        };
        assert_eq!(p.rpm_for(&k2), 7);
    }

    #[test]
    fn no_auth_provider_is_usable_without_keys() {
        let p = ProviderDef {
            no_auth: true,
            auth: AuthScheme::None,
            enabled: true,
            ..ProviderDef::default()
        };
        assert!(p.usable());
        let p2 = ProviderDef {
            enabled: true,
            ..ProviderDef::default()
        };
        assert!(!p2.usable());
    }

    #[test]
    fn model_map_rewrites() {
        let p = ProviderDef {
            model_map: [("a".to_string(), "b".to_string())].into(),
            ..ProviderDef::default()
        };
        assert_eq!(p.map_model("a"), "b");
        assert_eq!(p.map_model("c"), "c");
        assert!(p.model_rewritten("a"));
        assert!(!p.model_rewritten("c"));
    }

    #[test]
    fn candidates_index_and_wildcard() {
        let defs = default_providers();
        let set = ProviderSet::new(defs);
        let c: Vec<&str> = set
            .candidates("openrouter/auto")
            .iter()
            .map(|p| p.name.as_str())
            .collect();
        assert_eq!(c, vec!["openrouter"]);
        // No builtin declares "*", so an unlisted model resolves to nobody.
        let c2: Vec<&str> = set
            .candidates("some/unknown-model")
            .iter()
            .map(|p| p.name.as_str())
            .collect();
        assert!(c2.is_empty());
    }

    #[test]
    fn wildcard_claims_everything_when_configured() {
        let mut defs = default_providers();
        defs.iter_mut().find(|p| p.name == "nvidia").unwrap().models = vec!["*".to_string()];
        let set = ProviderSet::new(defs);
        let c: Vec<&str> = set
            .candidates("some/unknown-model")
            .iter()
            .map(|p| p.name.as_str())
            .collect();
        assert_eq!(c, vec!["nvidia"]);
    }

    #[test]
    fn builtin_defaults_match_astmatrix() {
        // Line-for-line against defaultProviders in
        // projects/herd/internal/astmatrix/providers.go.
        let defs = default_providers();
        let by_name = |n: &str| defs.iter().find(|p| p.name == n).unwrap();
        let ls = by_name("llama-swap");
        assert_eq!(ls.base_url, "http://127.0.0.1:25100/v1");
        assert!(ls.no_auth);
        assert_eq!(ls.elo, 1600);
        assert_eq!(
            ls.models,
            vec!["local-fast", "local-quality", "local-longctx"]
        );
        let nv = by_name("nvidia");
        assert_eq!(nv.base_url, "https://integrate.api.nvidia.com/v1");
        assert!(nv.free_tier);
        assert_eq!(nv.weight, 1.2);
        assert_eq!(nv.elo, 1550);
        let or = by_name("openrouter");
        assert!(!or.free_tier);
        assert_eq!(or.elo, 1500);
        assert_eq!(
            or.models,
            vec!["openrouter/auto", "openrouter/optimus-alpha"]
        );
        let gh = by_name("github");
        assert_eq!(gh.base_url, "https://models.inference.ai.azure.com");
        assert_eq!(gh.models, vec!["github/Phi-4", "github/gpt-4o-mini"]);
        let oai = by_name("openai");
        assert_eq!(oai.elo, 1650);
        assert_eq!(oai.models, vec!["gpt-4o", "gpt-4o-mini", "o1-preview"]);
        let sf = by_name("siliconflow");
        assert!(sf.free_tier);
        assert_eq!(sf.elo, 1470);
    }

    #[test]
    fn strategy_names_parse() {
        assert_eq!(Strategy::parse("hybrid"), Some(Strategy::Hybrid));
        assert_eq!(Strategy::parse("ast_race"), Some(Strategy::AstRace));
        assert_eq!(
            Strategy::parse("sticky_affinity"),
            Some(Strategy::StickyAffinity)
        );
        assert_eq!(Strategy::parse("weighted_elo"), Some(Strategy::WeightedElo));
        assert_eq!(
            Strategy::parse("least_latency"),
            Some(Strategy::LeastLatency)
        );
        assert_eq!(Strategy::parse("round_robin"), Some(Strategy::RoundRobin));
        assert_eq!(Strategy::parse("free"), Some(Strategy::Free));
        assert_eq!(
            Strategy::parse("circuit_chain"),
            Some(Strategy::CircuitChain)
        );
        assert_eq!(Strategy::parse("bogus"), None);
    }
}
