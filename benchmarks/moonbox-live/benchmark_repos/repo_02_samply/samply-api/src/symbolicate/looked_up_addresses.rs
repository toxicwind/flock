use std::collections::BTreeMap;

use samply_symbols::{FrameDebugInfo, FunctionNameHandle, SymbolInfo};

pub struct AddressResult {
    pub symbol: SymbolInfo,
    /// The function name from debug info, if available. This may be more
    /// accurate than the symbol name from the symbol table.
    pub function_name: Option<FunctionNameHandle>,
    pub inline_frames: Option<Vec<FrameDebugInfo>>,
}

impl AddressResult {
    pub fn new(symbol: SymbolInfo) -> Self {
        Self {
            symbol,
            function_name: None,
            inline_frames: None,
        }
    }

    pub fn set_debug_info(&mut self, frames: Vec<FrameDebugInfo>) {
        // Store the outer function name from debug info if available.
        self.function_name = frames.last().and_then(|f| f.function);
        // Add the inline frame info.
        self.inline_frames = Some(frames);
    }
}

pub type AddressResults = BTreeMap<u32, Option<AddressResult>>;
