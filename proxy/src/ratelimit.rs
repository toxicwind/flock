//! Token-bucket rate limiting — AstMatrix's `ratelimit.go`, native Rust.
//!
//! Behavior-faithful port: a bucket holds `capacity` tokens, refills at
//! `rate` tokens/second, and `allow` consumes one token when available.
//! Per-provider defaults follow AstMatrix's rule — 10 RPM for free-tier
//! providers, 60 RPM for everything else — unless the operator set an
//! explicit per-key or per-provider RPM.

use std::collections::HashMap;
use std::time::{Duration, Instant};

use crate::providers::ProviderDef;

/// A single token bucket. The math mirrors `TokenBucket.Allow` exactly:
/// refill proportional to elapsed time, capped at capacity.
#[derive(Debug, Clone)]
pub struct TokenBucket {
    tokens: f64,
    capacity: f64,
    rate: f64, // tokens per second
    last_fill: Instant,
}

impl TokenBucket {
    pub fn new(rate_per_sec: f64, capacity: f64) -> Self {
        Self {
            tokens: capacity,
            capacity,
            rate: rate_per_sec,
            last_fill: Instant::now(),
        }
    }

    /// Requests-per-minute constructor, the unit AstMatrix configured in.
    pub fn per_minute(rpm: f64) -> Self {
        Self::new(rpm / 60.0, rpm.max(1.0))
    }

    pub fn allow(&mut self) -> bool {
        let now = Instant::now();
        let elapsed = now.duration_since(self.last_fill).as_secs_f64();
        self.tokens = (self.tokens + elapsed * self.rate).min(self.capacity);
        self.last_fill = now;
        if self.tokens >= 1.0 {
            self.tokens -= 1.0;
            true
        } else {
            false
        }
    }

    #[cfg(test)]
    pub fn tokens(&self) -> f64 {
        self.tokens
    }
}

/// One bucket per provider. Rebuilt from the provider registry whenever the
/// store changes; drained buckets simply deny until they refill.
#[derive(Debug, Default)]
pub struct ProviderRateLimiter {
    buckets: HashMap<String, TokenBucket>,
}

impl ProviderRateLimiter {
    pub fn build(providers: &[ProviderDef]) -> Self {
        let mut buckets = HashMap::with_capacity(providers.len());
        for p in providers {
            // The tightest explicit key RPM governs the provider bucket;
            // otherwise AstMatrix's 60/10 default rule.
            let tightest = p
                .keys
                .iter()
                .filter(|k| k.enabled && k.rpm > 0)
                .map(|k| k.rpm as f64)
                .reduce(f64::min);
            let rpm = match tightest {
                Some(r) => r,
                None if p.default_rpm > 0 => p.default_rpm as f64,
                None if p.free_tier => 10.0,
                None => 60.0,
            };
            buckets.insert(p.name.clone(), TokenBucket::per_minute(rpm));
        }
        Self { buckets }
    }

    /// `Allow(provider)` from `ratelimit.go`. Unknown providers are denied:
    /// a provider the registry does not know must not serve traffic.
    pub fn allow(&mut self, provider: &str) -> bool {
        match self.buckets.get_mut(provider) {
            Some(b) => b.allow(),
            None => false,
        }
    }

    /// Test/operator hook: replace a provider's bucket wholesale.
    #[cfg(test)]
    pub fn set_bucket(&mut self, provider: &str, bucket: TokenBucket) {
        self.buckets.insert(provider.to_string(), bucket);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::providers::ProviderKey;

    #[test]
    fn bucket_starts_full_and_refills() {
        let mut b = TokenBucket::per_minute(60.0);
        assert!(b.allow());
        assert!((b.tokens() - 59.0).abs() < 1e-9);
        std::thread::sleep(Duration::from_millis(1100));
        // ~1 token refilled in ~1.1 s at 1 tok/s
        assert!(b.allow());
        assert!(b.tokens() < 60.0);
    }

    #[test]
    fn exhausted_bucket_denies() {
        let mut b = TokenBucket::new(0.0, 2.0);
        assert!(b.allow());
        assert!(b.allow());
        assert!(!b.allow());
    }

    #[test]
    fn free_tier_defaults_to_10_rpm_paid_to_60() {
        let mk = |name: &str, free: bool| ProviderDef {
            name: name.into(),
            free_tier: free,
            keys: vec![ProviderKey {
                key: "k".into(),
                enabled: true,
                ..ProviderKey::default()
            }],
            ..ProviderDef::default()
        };
        let mut lim = ProviderRateLimiter::build(&[mk("a", true), mk("b", false)]);
        // free: capacity 10
        for _ in 0..10 {
            assert!(lim.allow("a"));
        }
        assert!(!lim.allow("a"));
        // paid: capacity 60
        for _ in 0..60 {
            assert!(lim.allow("b"));
        }
        assert!(!lim.allow("b"));
    }

    #[test]
    fn unknown_provider_denied() {
        let mut lim = ProviderRateLimiter::build(&[]);
        assert!(!lim.allow("ghost"));
    }

    #[test]
    fn tightest_key_rpm_governs() {
        let p = ProviderDef {
            name: "x".into(),
            keys: vec![
                ProviderKey {
                    key: "k1".into(),
                    rpm: 30,
                    enabled: true,
                    ..ProviderKey::default()
                },
                ProviderKey {
                    key: "k2".into(),
                    rpm: 120,
                    enabled: true,
                    ..ProviderKey::default()
                },
            ],
            ..ProviderDef::default()
        };
        let mut lim = ProviderRateLimiter::build(&[p]);
        for _ in 0..30 {
            assert!(lim.allow("x"));
        }
        assert!(!lim.allow("x"));
    }
}
