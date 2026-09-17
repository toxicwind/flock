package astmatrix

import (
	"database/sql"
	"fmt"
	"sync"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

// HealthDB tracks provider health, latency, and ELO scores.
type HealthDB struct {
	mu     sync.RWMutex
	db     *sql.DB
	path   string

	// In-memory cache
	healthy   map[string]bool
	latencies map[string]time.Duration
	elos      map[string]int
	stickies  map[string]string // session -> provider
	lastProbe map[string]time.Time
}

// NewHealthDB creates or opens the health database.
func NewHealthDB(path string) *HealthDB {
	h := &HealthDB{
		path:      path,
		healthy:   make(map[string]bool),
		latencies: make(map[string]time.Duration),
		elos:      make(map[string]int),
		stickies:  make(map[string]string),
		lastProbe: make(map[string]time.Time),
	}
	// Try to open DB, but don't fail if sqlite3 is not available
	if db, err := sql.Open("sqlite3", path); err == nil {
		h.db = db
		h.initSchema()
	}
	return h
}

func (h *HealthDB) initSchema() {
	if h.db == nil {
		return
	}
	schema := `
CREATE TABLE IF NOT EXISTS provider_health (
	provider TEXT PRIMARY KEY,
	healthy INTEGER,
	latency_ms REAL,
	elo INTEGER,
	last_probe TEXT,
	failures INTEGER
);
CREATE TABLE IF NOT EXISTS sticky_sessions (
	session TEXT PRIMARY KEY,
	provider TEXT,
	expires TEXT
);
`
	h.db.Exec(schema)
}

// RecordHealth records health status for a provider.
func (h *HealthDB) RecordHealth(provider string, healthy bool, reason string) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.healthy[provider] = healthy
	h.lastProbe[provider] = time.Now()

	if h.db != nil {
		h.db.Exec(`
			INSERT INTO provider_health (provider, healthy, last_probe)
			VALUES (?, ?, ?)
			ON CONFLICT(provider) DO UPDATE SET
				healthy = excluded.healthy,
				last_probe = excluded.last_probe
		`, provider, healthy, time.Now().Format(time.RFC3339))
	}
}

// RecordLatency records a latency sample.
func (h *HealthDB) RecordLatency(provider string, latency time.Duration) {
	h.mu.Lock()
	defer h.mu.Unlock()
	// Exponential moving average
	old := h.latencies[provider]
	if old == 0 {
		h.latencies[provider] = latency
	} else {
		h.latencies[provider] = old*0.7 + latency*0.3
	}

	if h.db != nil {
		h.db.Exec(`
			INSERT INTO provider_health (provider, latency_ms, last_probe)
			VALUES (?, ?, ?)
			ON CONFLICT(provider) DO UPDATE SET
				latency_ms = excluded.latency_ms,
				last_probe = excluded.last_probe
		`, provider, float64(latency.Milliseconds()), time.Now().Format(time.RFC3339))
	}
}

// GetLatency returns the average latency for a provider.
func (h *HealthDB) GetLatency(provider string) time.Duration {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return h.latencies[provider]
}

// GetELO returns the ELO score for a provider.
func (h *HealthDB) GetELO(provider string) int {
	h.mu.RLock()
	defer h.mu.RUnlock()
	if e, ok := h.elos[provider]; ok {
		return e
	}
	return 1500 // Default
}

// SetELO sets the ELO score for a provider.
func (h *HealthDB) SetELO(provider string, elo int) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.elos[provider] = elo
}

// IsHealthy returns true if the provider is healthy.
func (h *HealthDB) IsHealthy(provider string) bool {
	h.mu.RLock()
	defer h.mu.RUnlock()
	// If never probed, assume healthy
	if _, ok := h.lastProbe[provider]; !ok {
		return true
	}
	return h.healthy[provider]
}

// SetSticky sets the sticky affinity for a session.
func (h *HealthDB) SetSticky(session, provider string, ttl time.Duration) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.stickies[session] = provider

	if h.db != nil {
		expires := time.Now().Add(ttl).Format(time.RFC3339)
		h.db.Exec(`
			INSERT INTO sticky_sessions (session, provider, expires)
			VALUES (?, ?, ?)
			ON CONFLICT(session) DO UPDATE SET
				provider = excluded.provider,
				expires = excluded.expires
		`, session, provider, expires)
	}
}

// GetSticky returns the sticky provider for a session.
func (h *HealthDB) GetSticky(session string) string {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return h.stickies[session]
}

// Close closes the database.
func (h *HealthDB) Close() error {
	if h.db != nil {
		return h.db.Close()
	}
	return nil
}
