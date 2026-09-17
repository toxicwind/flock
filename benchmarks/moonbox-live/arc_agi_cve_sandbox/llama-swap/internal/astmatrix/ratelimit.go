package astmatrix

import (
	"sync"
	"time"
)

// TokenBucket implements token bucket rate limiting.
type TokenBucket struct {
	mu       sync.Mutex
	tokens   float64
	capacity float64
	rate     float64
	lastFill time.Time
}

func NewTokenBucket(capacity, rate float64) *TokenBucket {
	return &TokenBucket{
		tokens: capacity, capacity: capacity,
		rate: rate, lastFill: time.Now(),
	}
}

func (tb *TokenBucket) Allow() bool {
	tb.mu.Lock(); defer tb.mu.Unlock()
	now := time.Now()
	elapsed := now.Sub(tb.lastFill).Seconds()
	tb.tokens = min(tb.capacity, tb.tokens+elapsed*tb.rate)
	tb.lastFill = now
	if tb.tokens >= 1 { tb.tokens--; return true }
	return false
}

// RateLimiter manages per-provider token buckets.
type RateLimiter struct {
	mu      sync.RWMutex
	buckets map[string]*TokenBucket
}

func NewRateLimiter(providers map[string]ProviderCfg) *RateLimiter {
	rl := &RateLimiter{buckets: make(map[string]*TokenBucket)}
	for id, p := range providers {
		rate := 60.0
		if p.FreeTier { rate = 10.0 }
		rl.buckets[id] = NewTokenBucket(rate, rate/60.0)
	}
	return rl
}

func (rl *RateLimiter) Allow(provider string) bool {
	rl.mu.RLock()
	b, ok := rl.buckets[provider]
	rl.mu.RUnlock()
	if !ok { return true }
	return b.Allow()
}
