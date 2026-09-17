package astmatrix

import "time"

// AstMatrixConfig configures cloud provider routing with production-grade defaults.
type AstMatrixConfig struct {
	Enabled     bool                   `yaml:"enabled"`
	Strategy    string                 `yaml:"strategy"`
	ASTStrategy string                 `yaml:"astStrategy"`
	MaxParallel int                    `yaml:"maxParallel"`
	DbPath      string                 `yaml:"dbPath"`
	StickyTTL   int                    `yaml:"stickyTtl"`
	FifoMax     int                    `yaml:"fifoMax"`
	Providers   map[string]ProviderCfg `yaml:"providers"`

	// Production tunables
	RequestTimeout      int  `yaml:"requestTimeout"`
	MaxRetries          int  `yaml:"maxRetries"`
	HealthProbeInterval int  `yaml:"healthProbeInterval"`
	EnableCoalescing    bool `yaml:"enableCoalescing"`
	ASTAlways           bool `yaml:"astAlways"`
}

// ProviderCfg is per-provider configuration.
type ProviderCfg struct {
	BaseURL   string            `yaml:"baseUrl"`
	KeyEnv    string            `yaml:"keyEnv"`
	KeyEnvAlt string            `yaml:"keyEnvAlt"`
	NoAuth    bool              `yaml:"noAuth"`
	FreeTier  bool              `yaml:"freeTier"`
	Models    []string          `yaml:"models"`
	ModelMap  map[string]string `yaml:"modelMap"`
	Weight    float64           `yaml:"weight"`
	ELO       int               `yaml:"elo"`
}

func (a *AstMatrixConfig) Defaults() {
	if a.Strategy == ""       { a.Strategy = "hybrid" }
	if a.ASTStrategy == ""   { a.ASTStrategy = "ast_race" }
	if a.MaxParallel <= 0     { a.MaxParallel = 4 }
	if a.DbPath == ""         { a.DbPath = "/tmp/ast_matrix.db" }
	if a.StickyTTL <= 0       { a.StickyTTL = 1800 }
	if a.FifoMax <= 0         { a.FifoMax = 64 }
	if a.RequestTimeout <= 0  { a.RequestTimeout = 95 }
	if a.MaxRetries <= 0      { a.MaxRetries = 3 }
	if a.HealthProbeInterval <= 0 { a.HealthProbeInterval = 30 }
}
