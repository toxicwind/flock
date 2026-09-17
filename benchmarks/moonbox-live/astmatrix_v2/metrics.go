package astmatrix

import (
	"sync"
	"time"
)

// MetricsCollector tracks routing metrics.
type MetricsCollector struct {
	mu sync.RWMutex

	requests    map[string]int64         // strategy -> count
	latencies   map[string][]time.Duration // provider -> latencies
	errors      map[string]int64         // strategy -> error count
	statusCodes map[int]int64            // HTTP status -> count
}

// NewMetricsCollector creates a metrics collector.
func NewMetricsCollector() *MetricsCollector {
	return &MetricsCollector{
		requests:    make(map[string]int64),
		latencies:   make(map[string][]time.Duration),
		errors:      make(map[string]int64),
		statusCodes: make(map[int]int64),
	}
}

// Record records a successful request.
func (m *MetricsCollector) Record(strategy string, latency time.Duration) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.requests[strategy]++
}

// RecordLatency records latency for a provider.
func (m *MetricsCollector) RecordLatency(provider string, latency time.Duration) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.latencies[provider] = append(m.latencies[provider], latency)
	// Keep only last 100 samples
	if len(m.latencies[provider]) > 100 {
		m.latencies[provider] = m.latencies[provider][len(m.latencies[provider])-100:]
	}
}

// RecordSuccess records a successful response.
func (m *MetricsCollector) RecordSuccess(strategy string, statusCode int) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.requests[strategy]++
	m.statusCodes[statusCode]++
}

// RecordError records an error.
func (m *MetricsCollector) RecordError(strategy string, statusCode int) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.errors[strategy]++
	m.statusCodes[statusCode]++
}

// GetLatency returns average latency for a provider.
func (m *MetricsCollector) GetLatency(provider string) time.Duration {
	m.mu.RLock()
	defer m.mu.RUnlock()
	latencies := m.latencies[provider]
	if len(latencies) == 0 {
		return 0
	}
	var total time.Duration
	for _, l := range latencies {
		total += l
	}
	return total / time.Duration(len(latencies))
}

// Snapshot returns a snapshot of current metrics.
func (m *MetricsCollector) Snapshot() map[string]interface{} {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return map[string]interface{}{
		"requests":    m.requests,
		"errors":      m.errors,
		"statusCodes": m.statusCodes,
	}
}
