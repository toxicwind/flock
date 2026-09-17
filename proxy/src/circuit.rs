//! Circuit breaker — AstMatrix's `circuit.go` semantics, native Rust.
//!
//! The port is behavior-faithful: closed allows everything; `max_failures`
//! consecutive failures open the circuit for `timeout`; a half-open trial
//! needs `half_open_max` consecutive successes to close, and a single failure
//! re-opens. Defaults match AstMatrix exactly (5 failures, 30 s timeout,
//! 3 half-open successes).
//!
//! Deliberate correction vs AstMatrix: its race path never consulted the
//! breaker at all, and its hybrid path treated any status below 500 as
//! usable (including 4xx). Here every strategy consults the breaker, and
//! only genuinely retryable failures count — see `MIGRATION.md`.

use std::time::{Duration, Instant};

use serde::{Deserialize, Serialize};

/// Persisted circuit snapshot. Wall-clock unix seconds are stored (never
/// `Instant`) so a restart can reconstruct the timeout window.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, Default)]
pub struct CircuitSnapshot {
    pub state: u8, // 0 closed, 1 half-open, 2 open
    pub failures: u32,
    pub last_failure_unix: u64, // 0 = none
    pub consecutive_successes: u32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CircuitState {
    Closed,
    HalfOpen,
    Open,
}

pub struct CircuitBreaker {
    state: CircuitState,
    failures: u32,
    last_failure: Option<Instant>,
    last_failure_unix: u64,
    consecutive_successes: u32,
    max_failures: u32,
    timeout: Duration,
    half_open_max: u32,
}

impl CircuitBreaker {
    pub fn new(max_failures: u32, timeout: Duration, half_open_max: u32) -> Self {
        Self {
            state: CircuitState::Closed,
            failures: 0,
            last_failure: None,
            last_failure_unix: 0,
            consecutive_successes: 0,
            max_failures: max_failures.max(1),
            timeout,
            half_open_max: half_open_max.max(1),
        }
    }

    /// AstMatrix's defaults: open after 5 failures, 30 s open timeout,
    /// 3 half-open successes to close.
    pub fn astmatrix_defaults() -> Self {
        Self::new(5, Duration::from_secs(30), 3)
    }

    pub fn state(&self) -> CircuitState {
        self.state
    }

    pub fn failures(&self) -> u32 {
        self.failures
    }

    /// `Allow` from `circuit.go`: closed always allows; open allows only
    /// after the timeout has elapsed (transitioning to half-open); half-open
    /// allows.
    pub fn allow(&mut self) -> bool {
        match self.state {
            CircuitState::Closed | CircuitState::HalfOpen => true,
            CircuitState::Open => {
                if let Some(t) = self.last_failure {
                    if t.elapsed() >= self.timeout {
                        self.state = CircuitState::HalfOpen;
                        self.consecutive_successes = 0;
                        return true;
                    }
                }
                false
            }
        }
    }

    /// `RecordSuccess`: a half-open trial that reaches `half_open_max`
    /// consecutive successes closes the circuit and resets failures.
    pub fn record_success(&mut self) {
        match self.state {
            CircuitState::Closed => {
                self.failures = 0;
            }
            CircuitState::HalfOpen => {
                self.consecutive_successes += 1;
                if self.consecutive_successes >= self.half_open_max {
                    self.state = CircuitState::Closed;
                    self.failures = 0;
                    self.consecutive_successes = 0;
                }
            }
            CircuitState::Open => {}
        }
    }

    /// `RecordFailure`: increments the failure count; reaching
    /// `max_failures` opens the circuit. A half-open failure re-opens
    /// immediately.
    pub fn record_failure(&mut self, now_unix: u64) {
        match self.state {
            CircuitState::Closed => {
                self.failures += 1;
                if self.failures >= self.max_failures {
                    self.open(now_unix);
                }
            }
            CircuitState::HalfOpen => {
                self.open(now_unix);
            }
            CircuitState::Open => {}
        }
    }

    fn open(&mut self, now_unix: u64) {
        self.state = CircuitState::Open;
        self.last_failure = Some(Instant::now());
        self.last_failure_unix = now_unix;
        self.consecutive_successes = 0;
    }

    /// Force-open for operator intervention (not in AstMatrix; additive).
    pub fn force_open(&mut self, now_unix: u64) {
        self.open(now_unix);
    }

    /// Snapshot for the persistence writer.
    pub fn snapshot(&self) -> CircuitSnapshot {
        CircuitSnapshot {
            state: match self.state {
                CircuitState::Closed => 0,
                CircuitState::HalfOpen => 1,
                CircuitState::Open => 2,
            },
            failures: self.failures,
            last_failure_unix: self.last_failure_unix,
            consecutive_successes: self.consecutive_successes,
        }
    }

    /// Restore from a persisted snapshot. An open circuit whose timeout has
    /// already elapsed while the process was down becomes half-open on the
    /// next `allow()` — same behavior as if the timeout had elapsed live.
    pub fn restore(snap: CircuitSnapshot, now_unix: u64) -> Self {
        let mut cb = Self::astmatrix_defaults();
        cb.failures = snap.failures;
        cb.consecutive_successes = snap.consecutive_successes;
        cb.last_failure_unix = snap.last_failure_unix;
        if snap.last_failure_unix > 0 {
            let age = now_unix.saturating_sub(snap.last_failure_unix);
            cb.last_failure = Some(Instant::now() - Duration::from_secs(age));
        }
        cb.state = match snap.state {
            1 => CircuitState::HalfOpen,
            2 => CircuitState::Open,
            _ => CircuitState::Closed,
        };
        cb
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn closed_allows_and_resets_on_success() {
        let mut cb = CircuitBreaker::astmatrix_defaults();
        assert!(cb.allow());
        cb.record_failure(1000);
        cb.record_failure(1000);
        assert_eq!(cb.failures(), 2);
        cb.record_success();
        assert_eq!(cb.failures(), 0);
        assert_eq!(cb.state(), CircuitState::Closed);
    }

    #[test]
    fn five_failures_open_and_timeout_half_opens() {
        let mut cb = CircuitBreaker::new(5, Duration::from_millis(50), 3);
        for _ in 0..5 {
            cb.record_failure(1000);
        }
        assert_eq!(cb.state(), CircuitState::Open);
        assert!(!cb.allow());
        std::thread::sleep(Duration::from_millis(60));
        assert!(cb.allow());
        assert_eq!(cb.state(), CircuitState::HalfOpen);
    }

    #[test]
    fn half_open_needs_three_successes_and_failure_reopens() {
        let mut cb = CircuitBreaker::new(5, Duration::from_millis(10), 3);
        for _ in 0..5 {
            cb.record_failure(1000);
        }
        std::thread::sleep(Duration::from_millis(20));
        assert!(cb.allow()); // -> half-open
        cb.record_success();
        cb.record_success();
        assert_eq!(cb.state(), CircuitState::HalfOpen);
        cb.record_failure(1001); // re-opens immediately
        assert_eq!(cb.state(), CircuitState::Open);
        assert!(!cb.allow());
    }

    #[test]
    fn half_open_three_successes_close() {
        let mut cb = CircuitBreaker::new(5, Duration::from_millis(10), 3);
        for _ in 0..5 {
            cb.record_failure(1000);
        }
        std::thread::sleep(Duration::from_millis(20));
        assert!(cb.allow());
        for _ in 0..3 {
            cb.record_success();
        }
        assert_eq!(cb.state(), CircuitState::Closed);
        assert_eq!(cb.failures(), 0);
    }

    #[test]
    fn snapshot_restore_round_trip() {
        let mut cb = CircuitBreaker::astmatrix_defaults();
        for _ in 0..5 {
            cb.record_failure(5000);
        }
        let snap = cb.snapshot();
        assert_eq!(snap.state, 2);
        assert_eq!(snap.failures, 5);
        assert_eq!(snap.last_failure_unix, 5000);
        let mut restored = CircuitBreaker::restore(snap, 5000 + 10);
        assert_eq!(restored.state(), CircuitState::Open);
        // 10 s < 30 s timeout: still blocked
        assert!(!restored.allow());
        let mut restored2 = CircuitBreaker::restore(snap, 5000 + 31);
        // timeout elapsed while down: half-opens on next allow
        assert!(restored2.allow());
        assert_eq!(restored2.state(), CircuitState::HalfOpen);
    }
}
