//! Re-exports the ledger data layer from `llmtrim-ledger`.
//!
//! All types and functions live in `crates/llmtrim-ledger`; this module keeps existing
//! `crate::tracking::*` call sites working without modification.

pub use llmtrim_ledger::tracking::*;

/// Wire CLI pricing into the ledger's daily unpriced-turn reprice (#244).
///
/// Safe to call more than once — first registration wins. Without this, ledger open
/// still works; zero-rate historical turns just stay unpriced until something registers.
pub fn init_rate_lookup() {
    #[cfg(feature = "intercept")]
    {
        register_rate_lookup(|provider, model| {
            let r = crate::monitor::rates_for(provider, model);
            (r.input, r.output, r.cache_read, r.cache_write)
        });
    }
}
