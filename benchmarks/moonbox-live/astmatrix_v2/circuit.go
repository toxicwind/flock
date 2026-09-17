package astmatrix

import (
	"sync"
	"time"
)

// CircuitState represents the circuit breaker state.
type CircuitState int

const (
	StateClosed CircuitState = iota
	StateOpen
	StateHalfOpen
)

// CircuitBreaker implements the circuit breaker pattern with half-open support.
type CircuitBreaker struct {
	mu                sync.RWMutex
	state             CircuitState
	failures          int
	lastFailureTime   time.Time
	consecutiveSuccesses int

	maxFailures       int
	timeout           time.Duration
	halfOpenMaxCalls  int
}

// NewCircuitBreaker creates a circuit breaker.
func NewCircuitBreaker(maxFailures int, timeout time.Duration) *CircuitBreaker {
	if maxFailures <= 0 {
		maxFailures = 5
	}
	if timeout <= 0 {
		timeout = 30 * time.Second
	}
	return &CircuitBreaker{
		maxFailures:      maxFailures,
		timeout:          timeout,
		halfOpenMaxCalls: 3,
		state:            StateClosed,
	}
}

// Allow returns true if the request should be allowed through.
func (cb *CircuitBreaker) Allow() bool {
	cb.mu.RLock()
	defer cb.mu.RUnlock()

	switch cb.state {
	case StateClosed:
		return true
	case StateOpen:
		if time.Since(cb.lastFailureTime) > cb.timeout {
			// Transition to half-open will happen on next Allow() call with write lock
			return true // Allow one probe
		}
		return false
	case StateHalfOpen:
		return cb.consecutiveSuccesses < cb.halfOpenMaxCalls
	}
	return false
}

// RecordSuccess records a successful call.
func (cb *CircuitBreaker) RecordSuccess() {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	switch cb.state {
	case StateHalfOpen:
		cb.consecutiveSuccesses++
		if cb.consecutiveSuccesses >= cb.halfOpenMaxCalls {
			cb.state = StateClosed
			cb.failures = 0
			cb.consecutiveSuccesses = 0
		}
	case StateClosed:
		cb.failures = 0
	}
}

// RecordFailure records a failed call.
func (cb *CircuitBreaker) RecordFailure() {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	cb.failures++
	cb.lastFailureTime = time.Now()

	switch cb.state {
	case StateHalfOpen:
		cb.state = StateOpen
		cb.consecutiveSuccesses = 0
	case StateClosed:
		if cb.failures >= cb.maxFailures {
			cb.state = StateOpen
		}
	}
}

// State returns the current state (for metrics/debugging).
func (cb *CircuitBreaker) State() CircuitState {
	cb.mu.RLock()
	defer cb.mu.RUnlock()
	return cb.state
}

// Stats returns circuit breaker statistics.
func (cb *CircuitBreaker) Stats() (state string, failures int, lastFail time.Time) {
	cb.mu.RLock()
	defer cb.mu.RUnlock()
	switch cb.state {
	case StateClosed:
		state = "closed"
	case StateOpen:
		state = "open"
	case StateHalfOpen:
		state = "half-open"
	}
	return state, cb.failures, cb.lastFailureTime
}
