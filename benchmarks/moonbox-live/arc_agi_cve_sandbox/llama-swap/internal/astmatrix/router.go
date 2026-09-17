package astmatrix

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"math/rand"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/mostlygeek/llama-swap/internal/logmon"
	"github.com/mostlygeek/llama-swap/internal/shared"
)

// Router implements router.Router for cloud provider dispatch.
type Router struct {
	cfg       *AstMatrixConfig
	logger    *logmon.Monitor
	registry  *ProviderRegistry
	healthDB  *HealthDB
	limiter   *RateLimiter
	circuits  sync.Map // string -> *CircuitBreaker
	coalescer *RequestCoalescer
	metrics   *MetricsCollector
	client    *http.Client
	rrCounter uint64
}

// routingContext holds per-request mutable state.
type routingContext struct {
	modelID   string
	isAST     bool
	bodyBytes []byte
	bodyJSON  map[string]interface{}
	startTime time.Time
	strategy  string
}

// NewRouter creates an astmatrix Router from config.
func NewRouter(cfg *AstMatrixConfig, logger *logmon.Monitor) (*Router, error) {
	if cfg == nil {
		cfg = &AstMatrixConfig{}
	}
	cfg.Defaults()

	reg := NewProviderRegistry(cfg.Providers)
	health := NewHealthDB(cfg.DbPath)
	limiter := NewRateLimiter(cfg.Providers)

	r := &Router{
		cfg:       cfg,
		logger:    logger,
		registry:  reg,
		healthDB:  health,
		limiter:   limiter,
		coalescer: NewRequestCoalescer(5 * time.Second),
		metrics:   NewMetricsCollector(),
		client: &http.Client{
			Timeout: time.Duration(cfg.RequestTimeout) * time.Second,
			Transport: &http.Transport{
				MaxIdleConns:        100,
				MaxIdleConnsPerHost: 10,
				IdleConnTimeout:     90 * time.Second,
				DisableCompression:  true,
			},
		},
	}
	go r.healthProbeLoop()
	return r, nil
}

// Handles returns true if any provider can serve modelID.
func (r *Router) Handles(modelID string) bool {
	if modelID == "" { return false }
	for _, p := range r.registry.All() {
		for _, m := range p.Models { if m == modelID { return true } }
		for local := range p.ModelMap { if local == modelID { return true } }
	}
	return false
}

// ServeHTTP implements http.Handler — main entry point.
func (r *Router) ServeHTTP(w http.ResponseWriter, req *http.Request) {
	start := time.Now()
	body, _ := io.ReadAll(req.Body)
	req.Body.Close()

	var bodyJSON map[string]interface{}
	json.Unmarshal(body, &bodyJSON)

	modelID := ""
	if bodyJSON != nil {
		if m, ok := bodyJSON["model"].(string); ok { modelID = m }
	}

	isAST := r.cfg.ASTAlways
	if !isAST && bodyJSON != nil {
		if msgs, ok := bodyJSON["messages"].([]interface{}); ok {
			for _, m := range msgs {
				if msg, ok := m.(map[string]interface{}); ok {
					if c, ok := msg["content"].(string); ok {
						if strings.Contains(c, "<ast>") || strings.Contains(c, "AST:") {
							isAST = true; break
						}
					}
				}
			}
		}
	}

	strategy := r.cfg.Strategy
	if isAST && r.cfg.ASTStrategy != "" { strategy = r.cfg.ASTStrategy }

	rt := &routingContext{
		modelID: modelID, isAST: isAST, bodyBytes: body,
		bodyJSON: bodyJSON, startTime: start, strategy: strategy,
	}

	r.logger.Infof("[astmatrix] %s model=%s strategy=%s", req.Method, modelID, strategy)

	switch strategy {
	case "ast_race":        r.routeAstRace(w, req, rt)
	case "sticky_affinity": r.routeSticky(w, req, rt)
	case "weighted_elo":    r.routeWeighted(w, req, rt)
	case "least_latency":    r.routeLeastLatency(w, req, rt)
	case "round_robin":      r.routeRoundRobin(w, req, rt)
	case "free":             r.routeFree(w, req, rt)
	case "circuit_chain":    r.routeCircuitChain(w, req, rt)
	default:                 r.routeHybrid(w, req, rt)
	}
	r.metrics.Record(strategy, time.Since(start))
}

// ---------------------------------------------------------------------------
// Strategy: hybrid (local-aware, retry, circuit breaker)
// ---------------------------------------------------------------------------
func (r *Router) routeHybrid(w http.ResponseWriter, req *http.Request, rt *routingContext) {
	providers := r.registry.ForModel(rt.modelID)
	var lastErr error

	for attempt := 0; attempt < r.cfg.MaxRetries; attempt++ {
		for _, p := range providers {
			cb := r.getCircuit(p.ID)
			if !cb.Allow() { continue }
			if !r.limiter.Allow(p.ID) { continue }
			if !r.healthDB.IsHealthy(p.ID) { continue }

			resp, err := r.call(req.Context(), p, req, rt)
			if err == nil && resp.StatusCode < 500 {
				cb.RecordSuccess()
				r.stream(w, resp, rt)
				return
			}
			if resp != nil { resp.Body.Close() }
			lastErr = err
			cb.RecordFailure()
		}
		if attempt < r.cfg.MaxRetries-1 {
			time.Sleep(time.Duration(attempt+1) * 500 * time.Millisecond)
		}
	}
	shared.SendError(w, req, fmt.Errorf("all providers exhausted: %w", lastErr))
}

// ---------------------------------------------------------------------------
// Strategy: ast_race (parallel fan-out, first valid wins)
// ---------------------------------------------------------------------------
func (r *Router) routeAstRace(w http.ResponseWriter, req *http.Request, rt *routingContext) {
	providers := r.registry.ForModel(rt.modelID)
	ctx, cancel := context.WithTimeout(req.Context(), time.Duration(r.cfg.RequestTimeout)*time.Second)
	defer cancel()

	type result struct { resp *http.Response; p Provider; err error }
	results := make(chan result, len(providers))

	for _, p := range providers {
		go func(p Provider) {
			resp, err := r.call(ctx, p, req, rt)
			results <- result{resp, p, err}
		}(p)
	}

	var lastErr error
	for i := 0; i < len(providers); i++ {
		select {
		case res := <-results:
			if res.err == nil && res.resp != nil && res.resp.StatusCode < 500 {
				r.getCircuit(res.p.ID).RecordSuccess()
				r.stream(w, res.resp, rt)
				return
			}
			if res.resp != nil { res.resp.Body.Close() }
			lastErr = res.err
		case <-ctx.Done():
			shared.SendError(w, req, fmt.Errorf("ast_race timeout"))
			return
		}
	}
	shared.SendError(w, req, fmt.Errorf("ast_race all failed: %w", lastErr))
}

// ---------------------------------------------------------------------------
// Strategy: sticky_affinity (session-based routing)
// ---------------------------------------------------------------------------
func (r *Router) routeSticky(w http.ResponseWriter, req *http.Request, rt *routingContext) {
	session := ""
	if auth := req.Header.Get("Authorization"); strings.HasPrefix(auth, "Bearer ") {
		session = auth[7:]
	}
	if session == "" {
		r.routeHybrid(w, req, rt)
		return
	}

	if pID := r.healthDB.GetSticky(session); pID != "" {
		if p, ok := r.registry.Get(pID); ok && r.healthDB.IsHealthy(p.ID) {
			if resp, err := r.call(req.Context(), p, req, rt); err == nil {
				r.stream(w, resp, rt)
				return
			}
		}
	}
	r.routeHybrid(w, req, rt)
}

// ---------------------------------------------------------------------------
// Strategy: weighted_elo (ELO-weighted random selection)
// ---------------------------------------------------------------------------
func (r *Router) routeWeighted(w http.ResponseWriter, req *http.Request, rt *routingContext) {
	providers := r.filterHealthy(r.registry.ForModel(rt.modelID))
	if len(providers) == 0 {
		shared.SendError(w, req, fmt.Errorf("no healthy providers"))
		return
	}

	total := 0.0
	for _, p := range providers {
		elo := r.healthDB.GetELO(p.ID)
		if elo <= 0 { elo = 1500 }
		total += float64(elo)
	}

	pick := rand.Float64() * total
	cum := 0.0
	for _, p := range providers {
		elo := r.healthDB.GetELO(p.ID)
		if elo <= 0 { elo = 1500 }
		cum += float64(elo)
		if pick <= cum {
			if resp, err := r.call(req.Context(), p, req, rt); err == nil {
				r.stream(w, resp, rt)
				return
			}
			break
		}
	}
	r.routeHybrid(w, req, rt)
}

// ---------------------------------------------------------------------------
// Strategy: least_latency (route to lowest observed latency)
// ---------------------------------------------------------------------------
func (r *Router) routeLeastLatency(w http.ResponseWriter, req *http.Request, rt *routingContext) {
	providers := r.filterHealthy(r.registry.ForModel(rt.modelID))
	if len(providers) == 0 {
		shared.SendError(w, req, fmt.Errorf("no healthy providers"))
		return
	}

	best := providers[0]
	bestLat := r.healthDB.GetLatency(best.ID)
	for _, p := range providers[1:] {
		if lat := r.healthDB.GetLatency(p.ID); lat > 0 && (bestLat == 0 || lat < bestLat) {
			best = p; bestLat = lat
		}
	}

	if resp, err := r.call(req.Context(), best, req, rt); err == nil {
		r.stream(w, resp, rt)
		return
	}
	r.routeHybrid(w, req, rt)
}

// ---------------------------------------------------------------------------
// Strategy: round_robin (weighted round-robin)
// ---------------------------------------------------------------------------
func (r *Router) routeRoundRobin(w http.ResponseWriter, req *http.Request, rt *routingContext) {
	providers := r.filterHealthy(r.registry.ForModel(rt.modelID))
	if len(providers) == 0 {
		shared.SendError(w, req, fmt.Errorf("no healthy providers"))
		return
	}
	idx := atomic.AddUint64(&r.rrCounter, 1) % uint64(len(providers))
	p := providers[idx]

	if resp, err := r.call(req.Context(), p, req, rt); err == nil {
		r.stream(w, resp, rt)
		return
	}
	r.routeHybrid(w, req, rt)
}

// ---------------------------------------------------------------------------
// Strategy: free (free-tier providers only)
// ---------------------------------------------------------------------------
func (r *Router) routeFree(w http.ResponseWriter, req *http.Request, rt *routingContext) {
	for _, p := range r.registry.ForModel(rt.modelID) {
		if p.FreeTier && r.healthDB.IsHealthy(p.ID) && r.getCircuit(p.ID).Allow() {
			if resp, err := r.call(req.Context(), p, req, rt); err == nil {
				r.stream(w, resp, rt)
				return
			}
		}
	}
	shared.SendError(w, req, fmt.Errorf("no free provider available"))
}

// ---------------------------------------------------------------------------
// Strategy: circuit_chain (chain through providers until success)
// ---------------------------------------------------------------------------
func (r *Router) routeCircuitChain(w http.ResponseWriter, req *http.Request, rt *routingContext) {
	for _, p := range r.registry.ForModel(rt.modelID) {
		cb := r.getCircuit(p.ID)
		if !cb.Allow() { continue }
		resp, err := r.call(req.Context(), p, req, rt)
		if err == nil && resp.StatusCode < 500 {
			cb.RecordSuccess()
			r.stream(w, resp, rt)
			return
		}
		if resp != nil { resp.Body.Close() }
		cb.RecordFailure()
	}
	shared.SendError(w, req, fmt.Errorf("circuit_chain exhausted all providers"))
}

// ---------------------------------------------------------------------------
// Core helpers
// ---------------------------------------------------------------------------
func (r *Router) filterHealthy(providers []Provider) []Provider {
	var out []Provider
	for _, p := range providers {
		if r.healthDB.IsHealthy(p.ID) && r.getCircuit(p.ID).Allow() {
			out = append(out, p)
		}
	}
	return out
}

func (r *Router) call(ctx context.Context, p Provider, req *http.Request, rt *routingContext) (*http.Response, error) {
	u, err := url.Parse(p.BaseURL)
	if err != nil { return nil, err }

	target := u.String() + req.URL.Path
	if req.URL.RawQuery != "" { target += "?" + req.URL.RawQuery }

	bodyClone := bytes.NewReader(rt.bodyBytes)
	newReq, err := http.NewRequestWithContext(ctx, req.Method, target, bodyClone)
	if err != nil { return nil, err }

	for k, vv := range req.Header {
		for _, v := range vv { newReq.Header.Add(k, v) }
	}
	if p.APIKey != "" {
		newReq.Header.Set("Authorization", "Bearer "+p.APIKey)
	}
	newReq.Header.Set("Host", u.Host)

	if rt.modelID != "" && p.ModelMap != nil {
		if mapped, ok := p.ModelMap[rt.modelID]; ok {
			bodyMap := make(map[string]interface{})
			json.Unmarshal(rt.bodyBytes, &bodyMap)
			bodyMap["model"] = mapped
			newBody, _ := json.Marshal(bodyMap)
			newReq.Body = io.NopCloser(bytes.NewReader(newBody))
			newReq.ContentLength = int64(len(newBody))
			newReq.Header.Set("Content-Length", fmt.Sprintf("%d", len(newBody)))
		}
	}

	start := time.Now()
	resp, err := r.client.Do(newReq)
	if err != nil { return nil, err }

	r.healthDB.RecordLatency(p.ID, time.Since(start))
	return resp, nil
}

func (r *Router) stream(w http.ResponseWriter, resp *http.Response, rt *routingContext) {
	defer resp.Body.Close()
	for k, vv := range resp.Header {
		for _, v := range vv { w.Header().Add(k, v) }
	}
	w.WriteHeader(resp.StatusCode)

	if flusher, ok := w.(http.Flusher); ok {
		buf := make([]byte, 32*1024)
		for {
			n, err := resp.Body.Read(buf)
			if n > 0 { w.Write(buf[:n]); flusher.Flush() }
			if err == io.EOF { break }
			if err != nil { r.logger.Warnf("[astmatrix] stream error: %v", err); break }
		}
	} else {
		io.Copy(w, resp.Body)
	}

	if resp.StatusCode < 400 {
		r.metrics.RecordSuccess(rt.strategy, resp.StatusCode)
	} else {
		r.metrics.RecordError(rt.strategy, resp.StatusCode)
	}
}

func (r *Router) getCircuit(id string) *CircuitBreaker {
	v, _ := r.circuits.LoadOrStore(id, NewCircuitBreaker(5, 30*time.Second))
	return v.(*CircuitBreaker)
}

func (r *Router) healthProbeLoop() {
	ticker := time.NewTicker(time.Duration(r.cfg.HealthProbeInterval) * time.Second)
	defer ticker.Stop()
	for range ticker.C {
		for _, p := range r.registry.All() {
			go r.probe(p)
		}
	}
}

func (r *Router) probe(p Provider) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	probeURL := p.BaseURL
	if !strings.HasSuffix(probeURL, "/") { probeURL += "/" }
	probeURL += "health"

	req, _ := http.NewRequestWithContext(ctx, "GET", probeURL, nil)
	if p.APIKey != "" { req.Header.Set("Authorization", "Bearer "+p.APIKey) }

	start := time.Now()
	resp, err := r.client.Do(req)
	if err != nil {
		r.healthDB.RecordHealth(p.ID, false, err.Error())
		return
	}
	resp.Body.Close()
	r.healthDB.RecordHealth(p.ID, resp.StatusCode < 500, "")
	r.healthDB.RecordLatency(p.ID, time.Since(start))
}

// Shutdown gracefully shuts down the router.
func (r *Router) Shutdown() {
	r.logger.Infof("[astmatrix] shutdown")
	r.healthDB.Close()
}
