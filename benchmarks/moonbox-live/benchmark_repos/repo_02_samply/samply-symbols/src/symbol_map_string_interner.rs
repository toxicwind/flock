use std::{borrow::Cow, collections::HashMap};

use crate::{
    generation::SymbolMapGeneration,
    shared::{FunctionNameIndex, SymbolNameIndex},
    FunctionNameHandle, SourceFilePathHandle, SourceFilePathIndex, SymbolNameHandle,
};

#[derive(Debug)]
pub struct SymbolMapStringInterner<'a> {
    symbol_map_generation: SymbolMapGeneration,
    borrowed_strings: Vec<&'a str>,
    index_for_borrowed_string: HashMap<&'a str, u32>,
    owned_strings: Vec<String>,
    index_for_owned_string: HashMap<String, u32>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct SymbolMapStringHandle {
    generation: SymbolMapGeneration,
    index: u32,
}

impl From<SourceFilePathHandle> for SymbolMapStringHandle {
    fn from(value: SourceFilePathHandle) -> Self {
        Self {
            generation: value.generation,
            index: value.index.0,
        }
    }
}

impl From<FunctionNameHandle> for SymbolMapStringHandle {
    fn from(value: FunctionNameHandle) -> Self {
        Self {
            generation: value.generation,
            index: value.index.0,
        }
    }
}

impl From<SymbolNameHandle> for SymbolMapStringHandle {
    fn from(value: SymbolNameHandle) -> Self {
        Self {
            generation: value.generation,
            index: value.index.0,
        }
    }
}

impl From<SymbolMapStringHandle> for SourceFilePathHandle {
    fn from(value: SymbolMapStringHandle) -> Self {
        SourceFilePathHandle {
            generation: value.generation,
            index: SourceFilePathIndex(value.index),
        }
    }
}

impl From<SymbolMapStringHandle> for FunctionNameHandle {
    fn from(value: SymbolMapStringHandle) -> Self {
        FunctionNameHandle {
            generation: value.generation,
            index: FunctionNameIndex(value.index),
        }
    }
}

impl From<SymbolMapStringHandle> for SymbolNameHandle {
    fn from(value: SymbolMapStringHandle) -> Self {
        SymbolNameHandle {
            generation: value.generation,
            index: SymbolNameIndex(value.index),
        }
    }
}

impl<'a> SymbolMapStringInterner<'a> {
    pub fn new(symbol_map_generation: SymbolMapGeneration) -> Self {
        Self {
            symbol_map_generation,
            borrowed_strings: Default::default(),
            index_for_borrowed_string: Default::default(),
            owned_strings: Default::default(),
            index_for_owned_string: Default::default(),
        }
    }

    fn handle(&self, index: u32) -> SymbolMapStringHandle {
        SymbolMapStringHandle {
            generation: self.symbol_map_generation,
            index,
        }
    }

    pub fn intern_cow(&mut self, cow: Cow<'a, str>) -> SymbolMapStringHandle {
        match cow {
            Cow::Borrowed(s) => self.intern(s),
            Cow::Owned(s) => self.intern_owned(&s),
        }
    }

    pub fn intern(&mut self, s: &'a str) -> SymbolMapStringHandle {
        let index = self.intern_inner(s);
        self.handle(index)
    }

    fn intern_inner(&mut self, s: &'a str) -> u32 {
        if let Some(index) = self.index_for_borrowed_string.get(s) {
            return (*index) << 1;
        }
        if let Some(index) = self.index_for_owned_string.get(s) {
            return ((*index) << 1) | 1;
        }
        let index = self.borrowed_strings.len() as u32;
        self.borrowed_strings.push(s);
        self.index_for_borrowed_string.insert(s, index);
        (index) << 1
    }

    pub fn intern_owned(&mut self, s: &str) -> SymbolMapStringHandle {
        let index = self.intern_owned_inner(s);
        self.handle(index)
    }

    fn intern_owned_inner(&mut self, s: &str) -> u32 {
        if let Some(index) = self.index_for_borrowed_string.get(s) {
            return (*index) << 1;
        }
        if let Some(index) = self.index_for_owned_string.get(s) {
            return ((*index) << 1) | 1;
        }
        let index = self.owned_strings.len() as u32;
        self.owned_strings.push(s.to_string());
        self.index_for_owned_string.insert(s.to_string(), index);
        ((index) << 1) | 1
    }

    pub fn resolve(&self, handle: SymbolMapStringHandle) -> Option<Cow<'a, str>> {
        assert_eq!(
            handle.generation, self.symbol_map_generation,
            "Attempting to resolve handle from different symbol map"
        );
        let index = handle.index;
        match index & 1 {
            0 => self
                .borrowed_strings
                .get((index >> 1) as usize)
                .map(|s| Cow::Borrowed(*s)),
            1 => self
                .owned_strings
                .get((index >> 1) as usize)
                .map(|s| Cow::Owned(s.clone())),
            _ => unreachable!(),
        }
    }
}
