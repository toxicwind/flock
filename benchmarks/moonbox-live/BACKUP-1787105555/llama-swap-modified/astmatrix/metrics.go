package astmatrix

import (
	"sync"
	"time"
)

type MetricsCollector struct {
	mu          sync.RWMutex
	requests    map[string]int64
	latencies   map[string][]time.Duration
	errors      map[string]int64
	statusCodes map[int]int64
}

func NewMetricsCollector() *MetricsCollector {
	return &MetricsCollector{
		requests: make(map[string]int64),
		latencies: make(map[string][]time.Duration),
		errors: make(map[string]int64),
		statusCodes: make(map[int]int64),
	}
}

func (m *MetricsCollector) Record(strategy string, latency time.Duration) {
	m.mu.Lock(); defer m.mu.Unlock()
	m.requests[strategy]++
}

func (m *MetricsCollector) RecordLatency(provider string, latency time.Duration) {
	m.mu.Lock(); defer m.mu.Unlock()
	m.latencies[provider] = append(m.latencies[provider], latency)
	if len(m.latencies[provider]) > 100 {
		m.latencies[provider] = m.latencies[provider][len(m.latencies[provider])-100:]
	}
}

func (m *MetricsCollector) RecordSuccess(strategy string, statusCode int) {
	m.mu.Lock(); defer m.mu.Unlock()
	m.requests[strategy]++; m.statusCodes[statusCode]++
}

func (m *MetricsCollector) RecordError(strategy string, statusCode int) {
	m.mu.Lock(); defer m.mu.Unlock()
	m.errors[strategy]++; m.statusCodes[statusCode]++
}

func (m *MetricsCollector) GetLatency(provider string) time.Duration {
	m.mu.RLock(); defer m.mu.RUnlock()
	latencies := m.latencies[provider]
	if len(latencies) == 0 { return 0 }
	var total time.Duration
	for _, l := range latencies { total += l }
	return total / time.Duration(len(latencies))
}
