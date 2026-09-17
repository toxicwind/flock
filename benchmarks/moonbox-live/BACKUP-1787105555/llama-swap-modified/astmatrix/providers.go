package astmatrix

import (
	"os"
	"strings"
)

// Provider represents a resolved upstream provider.
type Provider struct {
	ID       string
	BaseURL  string
	APIKey   string
	NoAuth   bool
	FreeTier bool
	Models   []string
	ModelMap map[string]string
	Weight   float64
	ELO      int
}

// ProviderRegistry manages configured providers.
type ProviderRegistry struct {
	providers map[string]Provider
	byModel   map[string][]string
}

func NewProviderRegistry(cfg map[string]ProviderCfg) *ProviderRegistry {
	pr := &ProviderRegistry{
		providers: make(map[string]Provider),
		byModel:   make(map[string][]string),
	}
	defaults := defaultProviders()
	for id, p := range defaults {
		pr.providers[id] = p
	}
	for id, pcfg := range cfg {
		p := Provider{
			ID: id, BaseURL: pcfg.BaseURL, NoAuth: pcfg.NoAuth,
			FreeTier: pcfg.FreeTier, Models: pcfg.Models,
			ModelMap: pcfg.ModelMap, Weight: pcfg.Weight, ELO: pcfg.ELO,
		}
		if pcfg.KeyEnv != "" { p.APIKey = os.Getenv(pcfg.KeyEnv) }
		if p.APIKey == "" && pcfg.KeyEnvAlt != "" { p.APIKey = os.Getenv(pcfg.KeyEnvAlt) }
		pr.providers[id] = p
	}
	pr.rebuildIndex()
	return pr
}

func (pr *ProviderRegistry) rebuildIndex() {
	pr.byModel = make(map[string][]string)
	for id, p := range pr.providers {
		for _, m := range p.Models { pr.byModel[m] = append(pr.byModel[m], id) }
		for local := range p.ModelMap { pr.byModel[local] = append(pr.byModel[local], id) }
	}
}

func (pr *ProviderRegistry) ForModel(modelID string) []Provider {
	ids, ok := pr.byModel[modelID]
	if !ok {
		var all []Provider
		for _, p := range pr.providers { all = append(all, p) }
		return all
	}
	var result []Provider
	for _, id := range ids {
		if p, ok := pr.providers[id]; ok { result = append(result, p) }
	}
	return result
}

func (pr *ProviderRegistry) Get(id string) (Provider, bool) {
	p, ok := pr.providers[id]
	return p, ok
}

func (pr *ProviderRegistry) All() []Provider {
	var result []Provider
	for _, p := range pr.providers { result = append(result, p) }
	return result
}

func defaultProviders() map[string]Provider {
	return map[string]Provider{
		"llama-swap": {
			ID: "llama-swap", BaseURL: "http://127.0.0.1:25100/v1",
			NoAuth: true, Models: []string{"local-fast", "local-quality", "local-longctx"},
			Weight: 1.0, ELO: 1600,
		},
		"openrouter": {
			ID: "openrouter", BaseURL: "https://openrouter.ai/api/v1",
			APIKey: os.Getenv("OPENROUTER_API_KEY"),
			Models: []string{"openrouter/auto", "openrouter/optimus-alpha"},
			Weight: 1.0, ELO: 1500,
		},
		"nvidia": {
			ID: "nvidia", BaseURL: "https://integrate.api.nvidia.com/v1",
			APIKey: os.Getenv("NVIDIA_API_KEY"), FreeTier: true,
			Models: []string{"nvidia/llama-3.1-nemotron-70b", "nvidia/mistral-7b-instruct"},
			Weight: 1.2, ELO: 1550,
		},
		"groq": {
			ID: "groq", BaseURL: "https://api.groq.com/openai/v1",
			APIKey: os.Getenv("GROQ_API_KEY"), FreeTier: true,
			Models: []string{"groq/llama-3.1-70b-versatile", "groq/mixtral-8x7b"},
			Weight: 1.5, ELO: 1580,
		},
		"together": {
			ID: "together", BaseURL: "https://api.together.xyz/v1",
			APIKey: os.Getenv("TOGETHER_API_KEY"),
			Models: []string{"together/llama-3.1-70b", "together/mixtral-8x22b"},
			Weight: 1.0, ELO: 1520,
		},
		"cerebras": {
			ID: "cerebras", BaseURL: "https://api.cerebras.ai/v1",
			APIKey: os.Getenv("CEREBRAS_API_KEY"), FreeTier: true,
			Models: []string{"cerebras/llama-3.1-70b"},
			Weight: 1.3, ELO: 1560,
		},
		"fireworks": {
			ID: "fireworks", BaseURL: "https://api.fireworks.ai/inference/v1",
			APIKey: os.Getenv("FIREWORKS_API_KEY"),
			Models: []string{"fireworks/llama-3.1-70b", "fireworks/mixtral-8x22b"},
			Weight: 1.0, ELO: 1510,
		},
		"hyperbolic": {
			ID: "hyperbolic", BaseURL: "https://api.hyperbolic.xyz/v1",
			APIKey: os.Getenv("HYPERBOLIC_API_KEY"), FreeTier: true,
			Models: []string{"hyperbolic/llama-3.1-70b"},
			Weight: 1.0, ELO: 1490,
		},
		"github": {
			ID: "github", BaseURL: "https://models.inference.ai.azure.com",
			APIKey: os.Getenv("GITHUB_TOKEN"), FreeTier: true,
			Models: []string{"github/Phi-4", "github/gpt-4o-mini"},
			Weight: 1.0, ELO: 1500,
		},
		"mistral": {
			ID: "mistral", BaseURL: "https://api.mistral.ai/v1",
			APIKey: os.Getenv("MISTRAL_API_KEY"),
			Models: []string{"mistral/mistral-large-2"},
			Weight: 1.0, ELO: 1530,
		},
		"openai": {
			ID: "openai", BaseURL: "https://api.openai.com/v1",
			APIKey: os.Getenv("OPENAI_API_KEY"),
			Models: []string{"gpt-4o", "gpt-4o-mini", "o1-preview"},
			Weight: 1.0, ELO: 1650,
		},
		"perplexity": {
			ID: "perplexity", BaseURL: "https://api.perplexity.ai",
			APIKey: os.Getenv("PERPLEXITY_API_KEY"),
			Models: []string{"perplexity/sonar"},
			Weight: 1.0, ELO: 1480,
		},
		"siliconflow": {
			ID: "siliconflow", BaseURL: "https://api.siliconflow.cn/v1",
			APIKey: os.Getenv("SILICONFLOW_API_KEY"), FreeTier: true,
			Models: []string{"siliconflow/deepseek-v2"},
			Weight: 1.0, ELO: 1470,
		},
	}
}

func RegistryProviders(baseURL string) ([]Provider, error) {
	return nil, nil
}
