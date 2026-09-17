package astmatrix

import "time"

// AstMatrixConfig configures the AST Matrix cloud router.
type AstMatrixConfig struct {
	Enabled     bool                   `yaml:"enabled"`
	Strategy    string                 `yaml:"strategy"`
	ASTStrategy string                 `yaml:"astStrategy"`     // Strategy for AST requests
	MaxParallel int                    `yaml:"maxParallel"`
	DbPath      string                 `yaml:"dbPath"`
	StickyTTL   int                    `yaml:"stickyTtl"`
	FifoMax     int                    `yaml:"fifoMax"`
	Providers   map[string]ProviderCfg `yaml:"providers"`

	// Production-grade additions
	RequestTimeout      int  `yaml:"requestTimeout"`      // Seconds (default: 95)
	MaxRetries          int  `yaml:"maxRetries"`          // Per provider (default: 3)
	HealthProbeInterval int  `yaml:"healthProbeInterval"` // Seconds (default: 30)
	EnableCoalescing    bool `yaml:"enableCoalescing"`    // Deduplicate identical requests
	ASTAlways           bool `yaml:"astAlways"`           // Treat all requests as AST
}

// ProviderCfg is per-provider configuration in the AST Matrix.
type ProviderCfg struct {
	BaseURL   string            `yaml:"baseUrl"`
	KeyEnv    string            `yaml:"keyEnv"`
	KeyEnvAlt string            `yaml:"keyEnvAlt"`
	NoAuth    bool              `yaml:"noAuth"`
	FreeTier  bool              `yaml:"freeTier"`  // Free-tier provider (no API key needed)
	Models    []string          `yaml:"models"`    // Explicit model list
	ModelMap  map[string]string `yaml:"modelMap"`  // Map local model IDs to provider model IDs
	Weight    float64           `yaml:"weight"`    // Load balancing weight
	ELO       int               `yaml:"elo"`       // Initial ELO score
}

func (a *AstMatrixConfig) Defaults() {
	if a.Strategy == "" {
		a.Strategy = "hybrid"
	}
	if a.ASTStrategy == "" {
		a.ASTStrategy = "ast_race"
	}
	if a.MaxParallel <= 0 {
		a.MaxParallel = 4
	}
	if a.DbPath == "" {
		a.DbPath = "/home/toxic/sovereign/data/ast_matrix.db"
	}
	if a.StickyTTL <= 0 {
		a.StickyTTL = 1800
	}
	if a.FifoMax <= 0 {
		a.FifoMax = 64
	}
	if a.RequestTimeout <= 0 {
		a.RequestTimeout = 95
	}
	if a.MaxRetries <= 0 {
		a.MaxRetries = 3
	}
	if a.HealthProbeInterval <= 0 {
		a.HealthProbeInterval = 30
	}
}
