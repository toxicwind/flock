package astmatrix

import (
	"sync"
	"time"
)

type CircuitState int
const (
	StateClosed CircuitState = iota
	StateOpen
	StateHalfOpen
)

// CircuitBreaker with half-open probe support.
type CircuitBreaker struct {
	mu                   sync.RWMutex
	state                CircuitState
	failures             int
	lastFailureTime      time.Time
	consecutiveSuccesses int
	maxFailures          int
	timeout              time.Duration
	halfOpenMaxCalls     int
}

func NewCircuitBreaker(maxFailures int, timeout time.Duration) *CircuitBreaker {
	if maxFailures <= 0 { maxFailures = 5 }
	if timeout <= 0     { timeout = 30 * time.Second }
	return &CircuitBreaker{
		maxFailures: maxFailures, timeout: timeout,
		halfOpenMaxCalls: 3, state: StateClosed,
	}
}

func (cb *CircuitBreaker) Allow() bool {
	cb.mu.Lock(); defer cb.mu.Unlock()
	switch cb.state {
	case StateClosed:
		return true
	case StateOpen:
		if time.Since(cb.lastFailureTime) > cb.timeout {
			cb.state = StateHalfOpen
			cb.consecutiveSuccesses = 0
			return true
		}
		return false
	case StateHalfOpen:
		return cb.consecutiveSuccesses < cb.halfOpenMaxCalls
	}
	return false
}

func (cb *CircuitBreaker) RecordSuccess() {
	cb.mu.Lock(); defer cb.mu.Unlock()
	switch cb.state {
	case StateHalfOpen:
		cb.consecutiveSuccesses++
		if cb.consecutiveSuccesses >= cb.halfOpenMaxCalls {
			cb.state = StateClosed; cb.failures = 0; cb.consecutiveSuccesses = 0
		}
	case StateClosed:
		cb.failures = 0
	}
}

func (cb *CircuitBreaker) RecordFailure() {
	cb.mu.Lock(); defer cb.mu.Unlock()
	cb.failures++; cb.lastFailureTime = time.Now()
	switch cb.state {
	case StateHalfOpen:
		cb.state = StateOpen; cb.consecutiveSuccesses = 0
	case StateClosed:
		if cb.failures >= cb.maxFailures { cb.state = StateOpen }
	}
}

func (cb *CircuitBreaker) State() CircuitState {
	cb.mu.RLock(); defer cb.mu.RUnlock()
	return cb.state
}
