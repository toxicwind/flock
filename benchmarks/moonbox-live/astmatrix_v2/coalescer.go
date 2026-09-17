package astmatrix

import (
	"net/http"
	"sync"
	"time"
)

// PendingRequest represents an in-flight request that others can wait on.
type PendingRequest struct {
	mu       sync.Mutex
	done     chan struct{}
	response *http.Response
	err      error
}

// Wait blocks until the request completes.
func (pr *PendingRequest) Wait() (*http.Response, error) {
	<-pr.done
	return pr.response, pr.err
}

// Complete marks the request as done with the result.
func (pr *PendingRequest) Complete(resp *http.Response, err error) {
	pr.mu.Lock()
	defer pr.mu.Unlock()
	if pr.response == nil && pr.err == nil {
		pr.response = resp
		pr.err = err
		close(pr.done)
	}
}

// RequestCoalescer deduplicates identical concurrent requests.
type RequestCoalescer struct {
	mu       sync.RWMutex
	pending  map[string]*PendingRequest
	ttl      time.Duration
}

// NewRequestCoalescer creates a coalescer with the given TTL.
func NewRequestCoalescer(ttl time.Duration) *RequestCoalescer {
	return &RequestCoalescer{
		pending: make(map[string]*PendingRequest),
		ttl:     ttl,
	}
}

// Get returns a pending request if one exists for the key.
func (rc *RequestCoalescer) Get(key string) *PendingRequest {
	rc.mu.RLock()
	defer rc.mu.RUnlock()
	return rc.pending[key]
}

// Register registers a new pending request for the key.
func (rc *RequestCoalescer) Register(key string) *PendingRequest {
	rc.mu.Lock()
	defer rc.mu.Unlock()
	pr := &PendingRequest{done: make(chan struct{})}
	rc.pending[key] = pr
	// Auto-cleanup after TTL
	go func() {
		time.Sleep(rc.ttl)
		rc.mu.Lock()
		delete(rc.pending, key)
		rc.mu.Unlock()
	}()
	return pr
}

// Complete marks a pending request as complete.
func (rc *RequestCoalescer) Complete(key string, pr *PendingRequest) {
	// The pending request is already in the map, just wait for caller to Complete it
}
