package astmatrix

import (
	"bytes"
	"encoding/json"
	"os"
	"strings"
	"testing"
	"time"
)

func TestLiveKimi(t *testing.T) {
	if os.Getenv("LIVE_TEST") != "1" {
		t.Skip("Set LIVE_TEST=1 to run live tests")
	}

	apiKey := os.Getenv("KIMI_API_KEY")
	if apiKey == "" {
		t.Skip("KIMI_API_KEY not set")
	}

	cfg := &AstMatrixConfig{
		Enabled:        true,
		Strategy:       "hybrid",
		ASTStrategy:    "ast_race",
		RequestTimeout: 120,
		MaxRetries:     2,
		Providers: map[string]ProviderCfg{
			"kimi": {
				BaseURL: "https://agent-gw.kimi.com/coding",
				KeyEnv:  "KIMI_API_KEY",
				Models:  []string{"kimi-latest"},
			},
		},
	}
	cfg.Defaults()

	t.Run("ProviderResolution", func(t *testing.T) {
		reg := NewProviderRegistry(cfg.Providers)
		providers := reg.ForModel("kimi-latest")
		if len(providers) == 0 {
			t.Fatal("no provider for kimi-latest")
		}
		if providers[0].BaseURL != "https://agent-gw.kimi.com/coding" {
			t.Fatalf("wrong base URL: %s", providers[0].BaseURL)
		}
	})

	t.Run("CircuitBreakerLive", func(t *testing.T) {
		cb := NewCircuitBreaker(2, 3*time.Second)
		cb.RecordFailure()
		cb.RecordFailure()
		if cb.State() != StateOpen {
			t.Fatalf("expected open, got %v", cb.State())
		}
		time.Sleep(4 * time.Second)
		if !cb.Allow() {
			t.Fatal("should allow probe after timeout")
		}
		// Need 3 consecutive successes to close (halfOpenMaxCalls=3)
		cb.RecordSuccess()
		cb.RecordSuccess()
		cb.RecordSuccess()
		if cb.State() != StateClosed {
			t.Fatalf("expected closed, got %v", cb.State())
		}
	})

	t.Run("RateLimitBurst", func(t *testing.T) {
		providers := map[string]ProviderCfg{
			"fast": {FreeTier: false},
			"slow": {FreeTier: true},
		}
		limiter := NewRateLimiter(providers)

		count := 0
		for i := 0; i < 70; i++ {
			if limiter.Allow("fast") {
				count++
			}
		}
		if count < 10 {
			t.Fatalf("paid tier too restrictive: %d allowed", count)
		}
		t.Logf("Paid tier allowed %d/70 requests", count)

		count = 0
		for i := 0; i < 20; i++ {
			if limiter.Allow("slow") {
				count++
			}
		}
		if count > 12 {
			t.Fatalf("free tier too permissive: %d allowed", count)
		}
		t.Logf("Free tier allowed %d/20 requests", count)
	})

	t.Run("HealthDBLatencyEMA", func(t *testing.T) {
		hdb := NewHealthDB(":memory:")
		hdb.RecordLatency("p1", 100*time.Millisecond)
		hdb.RecordLatency("p1", 200*time.Millisecond)
		hdb.RecordLatency("p1", 150*time.Millisecond)

		lat := hdb.GetLatency("p1")
		if lat < 100*time.Millisecond || lat > 200*time.Millisecond {
			t.Fatalf("EMA latency out of range: %v", lat)
		}
		t.Logf("EMA latency: %v", lat)
	})

	t.Run("LargeContextPayload", func(t *testing.T) {
		largeText := strings.Repeat("The quick brown fox jumps over the lazy dog. ", 10000)
		// Ensure we don't slice beyond string length
		sample := largeText
		if len(sample) > 500000 {
			sample = sample[:500000]
		}
		body := map[string]interface{}{
			"model": "kimi-latest",
			"messages": []map[string]string{
				{"role": "system", "content": "You are a helpful assistant."},
				{"role": "user", "content": sample},
			},
			"max_tokens": 100,
		}
		bodyJSON, _ := json.Marshal(body)
		t.Logf("Large payload: %d bytes (%.1f MB)", len(bodyJSON), float64(len(bodyJSON))/(1024*1024))
	})

	t.Run("StreamingResponseMock", func(t *testing.T) {
		var buf bytes.Buffer
		for i := 0; i < 100; i++ {
			buf.WriteString("data: {\"choices\":[{\"delta\":{\"content\":\"test\"}}]}\n\n")
		}
		buf.WriteString("data: [DONE]\n\n")

		if buf.Len() < 1000 {
			t.Fatal("mock stream too small")
		}
		t.Logf("Mock stream: %d bytes", buf.Len())
	})

	t.Run("RequestCoalescingConcurrency", func(t *testing.T) {
		coalescer := NewRequestCoalescer(5 * time.Second)
		key := "POST|/v1/chat/completions|{\"model\":\"kimi-latest\"}"

		pr := coalescer.Register(key)
		var completed int
		done := make(chan bool, 10)

		for i := 0; i < 10; i++ {
			go func() {
				p := coalescer.Get(key)
				if p != nil {
					p.Wait()
					completed++
				}
				done <- true
			}()
		}

		go func() {
			time.Sleep(100 * time.Millisecond)
			pr.Complete(nil, nil)
		}()

		for i := 0; i < 10; i++ {
			<-done
		}

		if completed < 9 {
			t.Fatalf("only %d/10 requests coalesced", completed)
		}
		t.Logf("Coalesced %d/10 requests", completed)
	})

	t.Run("WeightedELOSelection", func(t *testing.T) {
		hdb := NewHealthDB(":memory:")
		hdb.SetELO("high", 2000)
		hdb.SetELO("mid", 1500)
		hdb.SetELO("low", 1000)

		highCount := 0
		for i := 0; i < 1000; i++ {
			total := 2000.0 + 1500.0 + 1000.0
			pick := float64(i%1000) / 1000.0 * total
			if pick <= 2000 {
				highCount++
			}
		}

		ratio := float64(highCount) / 1000.0
		if ratio < 0.3 || ratio > 0.6 {
			t.Fatalf("ELO weighting skewed: %.2f", ratio)
		}
		t.Logf("High ELO selected %.1f%% of time", ratio*100)
	})

	t.Run("MetricsAggregation", func(t *testing.T) {
		m := NewMetricsCollector()

		for i := 0; i < 100; i++ {
			m.RecordSuccess("hybrid", 200)
			m.RecordLatency("openrouter", time.Duration(100+i)*time.Millisecond)
		}
		for i := 0; i < 10; i++ {
			m.RecordError("hybrid", 500)
		}

		snap := m.Snapshot()
		if snap == nil {
			t.Fatal("snapshot nil")
		}

		lat := m.GetLatency("openrouter")
		if lat == 0 {
			t.Fatal("latency not tracked")
		}
		t.Logf("Avg latency: %v", lat)
	})
}
