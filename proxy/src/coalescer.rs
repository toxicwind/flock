//! Request coalescer — AstMatrix's `RequestCoalescer`, actually wired in.
//!
//! AstMatrix instantiated its coalescer with a 5-second TTL but never
//! invoked it on any request path. Here it sits on the buffered (non-
//! streaming) request path: identical in-flight POSTs share one upstream
//! call, and every waiter receives the same response. This is the thundering-
//! herd fix AstMatrix declared but never shipped.
//!
//! Streaming requests never coalesce (each SSE stream is its own consumer).

use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use bytes::Bytes;
use tokio::sync::watch;

/// A response shared between the leader and all coalesced followers.
#[derive(Debug, Clone)]
pub struct SharedResponse {
    pub status: u16,
    pub content_type: String,
    pub body: Bytes,
}

struct Entry {
    tx: watch::Sender<Option<Arc<SharedResponse>>>,
    created: Instant,
}

/// The outcome of asking the coalescer about a request.
pub enum Coalesce {
    /// Another request with the same key is in flight; await its result.
    Follow(watch::Receiver<Option<Arc<SharedResponse>>>),
    /// This request is the leader: it must perform the upstream call and
    /// then call [`Lead::complete`] (or drop the lead, which releases
    /// followers to proceed alone).
    Lead(Lead),
}

/// The leader's handle. Dropping without `complete` releases followers.
pub struct Lead {
    coalescer: Arc<CoalescerInner>,
    key: String,
    tx: watch::Sender<Option<Arc<SharedResponse>>>,
    done: bool,
}

impl Lead {
    /// Publish the upstream result to all followers.
    pub fn complete(mut self, resp: SharedResponse) {
        let _ = self.tx.send(Some(Arc::new(resp)));
        self.done = true;
    }
}

impl Drop for Lead {
    fn drop(&mut self) {
        // Remove the entry so late followers don't attach to a dead call.
        // Followers already waiting see the channel close and proceed alone.
        self.coalescer.remove(&self.key);
    }
}

struct CoalescerInner {
    entries: Mutex<HashMap<String, Entry>>,
    ttl: Duration,
}

#[derive(Clone)]
pub struct Coalescer {
    inner: Arc<CoalescerInner>,
}

impl Coalescer {
    /// `ttl` bounds how long a follower waits and how long a dead leader's
    /// entry can linger. AstMatrix's configured TTL was 5 seconds.
    pub fn new(ttl: Duration) -> Self {
        Self {
            inner: Arc::new(CoalescerInner {
                entries: Mutex::new(HashMap::new()),
                ttl,
            }),
        }
    }

    pub fn ttl(&self) -> Duration {
        self.inner.ttl
    }

    /// Register `key`. Leaders get a [`Lead`]; followers get a receiver.
    pub fn register(&self, key: String) -> Coalesce {
        // Opportunistically reap expired entries first (bounded map).
        {
            let mut entries = self.inner.entries.lock().unwrap();
            let ttl = self.inner.ttl;
            entries.retain(|_, e| e.created.elapsed() < ttl * 2);
            if let Some(e) = entries.get(&key) {
                if e.created.elapsed() < ttl {
                    return Coalesce::Follow(e.tx.subscribe());
                }
            }
            let (tx, _rx) = watch::channel(None);
            entries.insert(
                key.clone(),
                Entry {
                    tx: tx.clone(),
                    created: Instant::now(),
                },
            );
            Coalesce::Lead(Lead {
                coalescer: self.inner.clone(),
                key,
                tx,
                done: false,
            })
        }
    }

    /// Await the leader's result. Returns `None` when the leader vanished
    /// without publishing (caller should proceed alone) or the wait timed
    /// out.
    pub async fn wait(
        &self,
        mut rx: watch::Receiver<Option<Arc<SharedResponse>>>,
    ) -> Option<Arc<SharedResponse>> {
        let ttl = self.inner.ttl;
        let res = tokio::time::timeout(ttl, rx.wait_for(|v| v.is_some())).await;
        match res {
            Ok(Ok(guard)) => guard.clone(),
            _ => None,
        }
    }
}

impl CoalescerInner {
    fn remove(&self, key: &str) {
        self.entries.lock().unwrap().remove(key);
    }
}

/// Canonical key for a buffered request: method + path + body hash.
/// Streaming requests must never be coalesced — callers enforce that.
pub fn coalesce_key(method: &str, path: &str, body: &[u8]) -> String {
    use sha2::{Digest, Sha256};
    let mut h = Sha256::new();
    h.update(method.as_bytes());
    h.update(b"\n");
    h.update(path.as_bytes());
    h.update(b"\n");
    h.update(body);
    format!("{:x}", h.finalize())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn follower_receives_leader_result() {
        let c = Coalescer::new(Duration::from_secs(5));
        let key = "k1".to_string();
        let lead = match c.register(key.clone()) {
            Coalesce::Lead(l) => l,
            Coalesce::Follow(_) => panic!("expected lead"),
        };
        let rx = match c.register(key) {
            Coalesce::Follow(rx) => rx,
            Coalesce::Lead(_) => panic!("expected follow"),
        };
        let c2 = c.clone();
        let waiter = tokio::spawn(async move { c2.wait(rx).await });
        // Give the waiter a moment to subscribe.
        tokio::time::sleep(Duration::from_millis(20)).await;
        lead.complete(SharedResponse {
            status: 200,
            content_type: "application/json".into(),
            body: Bytes::from_static(b"{\"ok\":true}"),
        });
        let got = waiter.await.unwrap().expect("follower got result");
        assert_eq!(got.status, 200);
        assert_eq!(&got.body[..], b"{\"ok\":true}");
    }

    #[tokio::test]
    async fn dropped_lead_releases_follower_to_proceed_alone() {
        let c = Coalescer::new(Duration::from_millis(100));
        let key = "k2".to_string();
        let lead = match c.register(key.clone()) {
            Coalesce::Lead(l) => l,
            _ => panic!("expected lead"),
        };
        let rx = match c.register(key) {
            Coalesce::Follow(rx) => rx,
            _ => panic!("expected follow"),
        };
        drop(lead); // no complete()
        let got = c.wait(rx).await;
        assert!(got.is_none(), "follower must proceed alone");
    }

    #[tokio::test]
    async fn wait_times_out() {
        let c = Coalescer::new(Duration::from_millis(50));
        let key = "k3".to_string();
        let _lead = match c.register(key.clone()) {
            Coalesce::Lead(l) => l,
            _ => panic!("expected lead"),
        };
        let rx = match c.register(key) {
            Coalesce::Follow(rx) => rx,
            _ => panic!("expected follow"),
        };
        // Leader never completes; waiter must not hang past the TTL.
        let got = c.wait(rx).await;
        assert!(got.is_none());
    }

    #[test]
    fn keys_differ_by_body() {
        let a = coalesce_key("POST", "/v1/chat/completions", b"{}");
        let b = coalesce_key("POST", "/v1/chat/completions", b"{\"x\":1}");
        assert_ne!(a, b);
        assert_eq!(a.len(), 64);
    }
}
