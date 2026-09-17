package astmatrix

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"

	"fmt"
)

func TestLiveProviders(t *testing.T) {
	if os.Getenv("LIVE_TEST") != "1" {
		t.Skip("Set LIVE_TEST=1 to run live provider tests")
	}
	logger := NewMockMonitor("astmatrix-test")
	cfg := &AstMatrixConfig{
		Enabled: true, Strategy: "hybrid", ASTStrategy: "ast_race",
		RequestTimeout: 120, MaxRetries: 2, HealthProbeInterval: 60,
		EnableCoalescing: true,
		Providers: map[string]ProviderCfg{
			"openrouter": {BaseURL: "https://openrouter.ai/api/v1", KeyEnv: "OPENROUTER_API_KEY", Models: []string{"openrouter/auto"}},
			"groq": {BaseURL: "https://api.groq.com/openai/v1", KeyEnv: "GROQ_API_KEY", FreeTier: true, Models: []string{"groq/llama-3.1-70b-versatile"}},
			"github": {BaseURL: "https://models.inference.ai.azure.com", KeyEnv: "GITHUB_TOKEN", FreeTier: true, Models: []string{"github/gpt-4o-mini"}},
		},
	}
	cfg.Defaults()
	router, err := NewRouter(cfg, logger)
	if err != nil { t.Fatalf("NewRouter: %v", err) }
	defer router.Shutdown()

	t.Run("BasicCompletion", func(t *testing.T) {
		body := map[string]interface{}{
			"model": "openrouter/auto", "messages": []map[string]string{{"role": "user", "content": "Say hello"}},
			"max_tokens": 100,
		}
		resp := testRequest(t, router, body)
		if resp.StatusCode != http.StatusOK { t.Fatalf("expected 200, got %d", resp.StatusCode) }
		var result map[string]interface{}
		json.NewDecoder(resp.Body).Decode(&result)
		if _, ok := result["choices"]; !ok { t.Fatalf("no choices: %v", result) }
	})

	t.Run("StreamingSSE", func(t *testing.T) {
		body := map[string]interface{}{
			"model": "groq/llama-3.1-70b-versatile", "messages": []map[string]string{{"role": "user", "content": "Count 1 to 10"}},
			"stream": true, "max_tokens": 4096,
		}
		resp := testRequest(t, router, body)
		if resp.StatusCode != http.StatusOK { t.Fatalf("expected 200, got %d", resp.StatusCode) }
		ct := resp.Header.Get("Content-Type")
		if !strings.Contains(ct, "text/event-stream") { t.Logf("Warning: expected text/event-stream, got %s", ct) }
		buf := new(bytes.Buffer)
		buf.ReadFrom(resp.Body)
		if buf.Len() == 0 { t.Fatal("empty SSE stream") }
		t.Logf("SSE stream: %d bytes", buf.Len())
	})

	t.Run("LargeContext", func(t *testing.T) {
		largeText := strings.Repeat("The quick brown fox jumps over the lazy dog. ", 20000)
		body := map[string]interface{}{
			"model": "github/gpt-4o-mini",
			"messages": []map[string]string{
				{"role": "system", "content": "You are a helpful assistant."},
				{"role": "user", "content": "Summarize: " + largeText[:100000]},
			},
			"max_tokens": 500,
		}
		resp := testRequest(t, router, body)
		if resp.StatusCode != http.StatusOK {
			body := readBody(resp)
			if strings.Contains(body, "context_length_exceeded") { t.Skip("Context limit exceeded") }
			t.Fatalf("expected 200, got %d: %s", resp.StatusCode, body)
		}
	})

	t.Run("CircuitBreaker", func(t *testing.T) {
		cb := NewCircuitBreaker(3, 5*time.Second)
		for i := 0; i < 3; i++ { cb.RecordFailure() }
		if cb.State() != StateOpen { t.Fatalf("expected open, got %v", cb.State()) }
		time.Sleep(6 * time.Second)
		if !cb.Allow() { t.Fatal("expected half-open") }
		cb.RecordSuccess(); cb.RecordSuccess(); cb.RecordSuccess()
		if cb.State() != StateClosed { t.Fatalf("expected closed, got %v", cb.State()) }
	})

	t.Run("RateLimiting", func(t *testing.T) {
		providers := map[string]ProviderCfg{"test": {FreeTier: true}}
		limiter := NewRateLimiter(providers)
		for i := 0; i < 10; i++ {
			if !limiter.Allow("test") { t.Fatalf("request %d blocked", i) }
		}
	})
}

func testRequest(t *testing.T, router *Router, body map[string]interface{}) *http.Response {
	bodyJSON, _ := json.Marshal(body)
	req := httptest.NewRequest("POST", "/v1/chat/completions", bytes.NewReader(bodyJSON))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer test-token")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	return w.Result()
}

func readBody(resp *http.Response) string {
	if resp == nil || resp.Body == nil { return "" }
	defer resp.Body.Close()
	buf := new(bytes.Buffer)
	buf.ReadFrom(resp.Body)
	return buf.String()
}
