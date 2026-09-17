package astmatrix

import (
	"sync"
)

// Matrix coordinates providers, circuit breakers, and health state.
// It is a thin wrapper around Router for compatibility with upstream naming.
type Matrix struct {
	mu        sync.RWMutex
	registry  *ProviderRegistry
	health    *HealthDB
	limiter   *RateLimiter
	config    *AstMatrixConfig
	router    *Router
	coalescer *Coalescer
}

// NewMatrix creates a Matrix from config.
func NewMatrix(cfg *AstMatrixConfig, reg *ProviderRegistry, health *HealthDB, limiter *RateLimiter) (*Matrix, error) {
	if cfg == nil {
		cfg = &AstMatrixConfig{}
		cfg.Defaults()
	}
	m := &Matrix{
		registry: reg, health: health,
		limiter: limiter, config: cfg,
	}
	// Wire router
	router, err := NewRouter(cfg, nil)
	if err != nil {
		return nil, err
	}
	m.router = router
	m.router.matrix = m // back-reference for Matrix() method
	// Wire coalescer
	m.coalescer = &Coalescer{cfg: cfg}
	return m, nil
}

func (m *Matrix) Providers() *ProviderRegistry { return m.registry }
func (m *Matrix) Health() *HealthDB            { return m.health }
func (m *Matrix) Limiter() *RateLimiter        { return m.limiter }
func (m *Matrix) Router() *Router              { return m.router }
func (m *Matrix) Coalescer() *Coalescer        { return m.coalescer }
