package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"time"

	"github.com/projectdiscovery/goflags"
	"github.com/projectdiscovery/gologger"
)

type Result struct {
	Timestamp      string  `json:"timestamp"`
	TestName       string  `json:"test_name"`
	StatusCode     int     `json:"status_code"`
	Success        bool    `json:"success"`
	ElapsedMs      float64 `json:"elapsed_ms"`
	Error          string  `json:"error,omitempty"`
	ReasoningTokens *int   `json:"reasoning_tokens,omitempty"`
	ContentPreview string  `json:"content_preview,omitempty"`
}

func main() {
	var opts struct {
		Model           string  `json:"model"`
		MaxTokens       int     `json:"max_tokens"`
		Temperature     float64 `json:"temperature"`
		Stream          bool    `json:"stream"`
		ReasoningEffort string  `json:"reasoning_effort"`
		Discover        bool    `json:"discover"`
		Benchmark       bool    `json:"benchmark"`
	}

	flagSet := goflags.NewFlagSet()
	flagSet.SetDescription("NVIDIA NIM Inkling API Research Suite")
	flagSet.CreateGroup("target", "Target",
		flagSet.StringVarP(&opts.Model, "model", "m", "thinkingmachines/inkling", "Model ID"),
		flagSet.IntVarP(&opts.MaxTokens, "max-tokens", "t", 100, "Max output tokens"),
		flagSet.Float64VarP(&opts.Temperature, "temperature", "T", 1.0, "Temperature"),
		flagSet.BoolVarP(&opts.Stream, "stream", "s", false, "SSE streaming"),
	)
	flagSet.CreateGroup("reasoning", "Reasoning",
		flagSet.StringVarP(&opts.ReasoningEffort, "effort", "e", "max", "Reasoning effort"),
	)
	flagSet.CreateGroup("mode", "Mode",
		flagSet.BoolVarP(&opts.Discover, "discover", "d", false, "Parameter discovery"),
		flagSet.BoolVarP(&opts.Benchmark, "benchmark", "b", false, "Latency benchmark"),
	)
	flagSet.Parse()

	apiKey := os.Getenv("NVIDIA_API_KEY")
	if apiKey == "" {
		gologger.Fatal().Msg("NVIDIA_API_KEY required")
	}

	baseURL := "https://integrate.api.nvidia.com/v1"
	if opts.Discover {
		runDiscover(baseURL, apiKey)
	} else if opts.Benchmark {
		runBenchmark(baseURL, apiKey, opts)
	} else {
		runSingle(baseURL, apiKey, opts)
	}
}

func runSingle(baseURL, apiKey string, opts struct {
	Model string; MaxTokens int; Temperature float64; Stream bool; ReasoningEffort string; Discover bool; Benchmark bool
}) {
	payload := map[string]interface{}{
		"model": opts.Model,
		"messages": []map[string]string{{"role": "user", "content": "Prove p^2-1 divisible by 24 for prime p>3"}},
		"max_tokens": opts.MaxTokens,
		"temperature": opts.Temperature,
		"stream": opts.Stream,
		"chat_template_kwargs": map[string]string{"reasoning_effort": opts.ReasoningEffort},
	}
	printResult(call(baseURL, apiKey, payload, "single"))
}

func runDiscover(baseURL, apiKey string) {
	efforts := []string{"none", "low", "medium", "high", "max", "xhigh"}
	maxTokens := []int{1, 100, 1000, 8192, 16384, 32768, 65536}
	for _, e := range efforts {
		for _, m := range maxTokens {
			payload := map[string]interface{}{
				"model": "thinkingmachines/inkling",
				"messages": []map[string]string{{"role": "user", "content": "Hi"}},
				"max_tokens": m,
				"chat_template_kwargs": map[string]string{"reasoning_effort": e},
			}
			printResult(call(baseURL, apiKey, payload, fmt.Sprintf("discover_e=%s_m=%d", e, m)))
			time.Sleep(2 * time.Second)
		}
	}
}

func runBenchmark(baseURL, apiKey string, opts struct {
	Model string; MaxTokens int; Temperature float64; Stream bool; ReasoningEffort string; Discover bool; Benchmark bool
}) {
	prompts := []string{"Hi", "What is 2+2?", "Explain quantum computing", "Write Python sort function", "Prove p^2-1 divisible by 24"}
	efforts := []string{"none", "low", "medium", "high", "max"}
	for _, prompt := range prompts {
		for _, effort := range efforts {
			payload := map[string]interface{}{
				"model": opts.Model,
				"messages": []map[string]string{{"role": "user", "content": prompt}},
				"max_tokens": opts.MaxTokens,
				"chat_template_kwargs": map[string]string{"reasoning_effort": effort},
			}
			printResult(call(baseURL, apiKey, payload, fmt.Sprintf("bench_%d_%s", len(prompt), effort)))
			time.Sleep(2 * time.Second)
		}
	}
}

func call(baseURL, apiKey string, payload map[string]interface{}, testName string) Result {
	body, _ := json.Marshal(payload)
	req, _ := http.NewRequest("POST", baseURL+"/chat/completions", bytes.NewReader(body))
	req.Header.Set("Authorization", "Bearer "+apiKey)
	req.Header.Set("Content-Type", "application/json")

	start := time.Now()
	resp, err := http.DefaultClient.Do(req)
	elapsed := time.Since(start)

	if err != nil {
		return Result{Timestamp: time.Now().Format(time.RFC3339), TestName: testName, StatusCode: 0, Success: false, ElapsedMs: float64(elapsed.Milliseconds()), Error: err.Error()}
	}
	defer resp.Body.Close()

	var data map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&data)

	r := Result{Timestamp: time.Now().Format(time.RFC3339), TestName: testName, StatusCode: resp.StatusCode, Success: resp.StatusCode == 200, ElapsedMs: float64(elapsed.Milliseconds())}
	if resp.StatusCode == 200 {
		choices, _ := data["choices"].([]interface{})
		if len(choices) > 0 {
			msg := choices[0].(map[string]interface{})["message"].(map[string]interface{})
			r.ContentPreview = msg["content"].(string)[:min(200, len(msg["content"].(string)))]
		}
		usage, _ := data["usage"].(map[string]interface{})
		if rt, ok := usage["reasoning_tokens"]; ok && rt != nil {
			if v, ok := rt.(float64); ok { ri := int(v); r.ReasoningTokens = &ri }
		}
	} else {
		errBody, _ := json.Marshal(data)
		r.Error = string(errBody)[:200]
	}
	return r
}

func printResult(r Result) {
	status := "OK"
	if !r.Success { status = "FAIL" }
	fmt.Printf("[%s] %-30s | %3d | %8.1fms", status, r.TestName, r.StatusCode, r.ElapsedMs)
	if r.ReasoningTokens != nil { fmt.Printf(" | reasoning=%d", *r.ReasoningTokens) }
	if r.Error != "" { fmt.Printf(" | %s", r.Error[:60]) }
	fmt.Println()
}

func min(a, b int) int { if a < b { return a }; return b }
