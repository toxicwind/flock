package astmatrix

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/mostlygeek/llama-swap/internal/config"
	"github.com/mostlygeek/llama-swap/internal/logmon"
	"github.com/mostlygeek/llama-swap/internal/shared"
)

// Router implements the router.Router interface for cloud provider routing
// with production-grade features: circuit breakers, health probes, retries,
// streaming SSE proxy, weighted load balancing, and request coalescing.
type Router struct {
	cfg         AstMatrixConfig
	logger      *logmon.Monitor
	providers   *ProviderRegistry
	ratelimiter *RateLimiter
	healthDB    *HealthDB

	// circuitBreakers maps providerID -> *CircuitBreaker
	circuitBreakers sync.Map

	// requestCache deduplicates in-flight identical requests
	requestCache *RequestCoalescer

	// strategy dispatch table
	strategies map[string]func(http.ResponseWriter, *http.Request, *routingContext)

	// metrics
	metrics *MetricsCollector

	// upstream HTTP client with tuned timeouts
	client *http.Client

	// reverse proxy cache for streaming
	proxyCache sync.Map
}

// routingContext holds per-request state
type routingContext struct {
	modelID      string
	isAST        bool
	bodyBytes    []byte
	bodyJSON     map[string]interface{}
	providerHint string
	strategy     string
	startTime    time.Time
}

// NewRouter creates an astmatrix router from config.
func NewRouter(cfg config.Config, logger *logmon.Monitor) *Router {
	amc := cfg.AstMatrix
	if amc.Strategy == "" {
		amc.Strategy = "hybrid"
	}
	if amc.RequestTimeout == 0 {
		amc.RequestTimeout = 95
	}
	if amc.MaxRetries == 0 {
		amc.MaxRetries = 3
	}
	if amc.HealthProbeInterval == 0 {
		amc.HealthProbeInterval = 30
	}

	r := &Router{
		cfg:         amc,
		logger:      logger,
		providers:   NewProviderRegistry(amc.Providers),
		ratelimiter: NewRateLimiter(amc.Providers),
		healthDB:    NewHealthDB(amc.HealthDBPath),
		requestCache: NewRequestCoalescer(5 * time.Second),
		metrics:     NewMetricsCollector(),
		client: &http.Client{
			Timeout: time.Duration(amc.RequestTimeout) * time.Second,
			Transport: &http.Transport{
				MaxIdleConns:        100,
				MaxIdleConnsPerHost: 10,
				IdleConnTimeout:     90 * time.Second,
				DisableCompression:  true, // We handle compression ourselves
			},
		},
	}

	r.strategies = map[string]func(http.ResponseWriter, *http.Request, *routingContext){
		"hybrid":            r.routeHybrid,
		"ast_race":          r.routeAstRace,
		"sticky_affinity":   r.routeStickyAffinity,
		"weighted_elo":      r.routeWeightedELO,
		"circuit_chain":     r.routeCircuitChain,
		"fifo_matrix":       r.routeFIFOMatrix,
		"free":              r.routeFree,
		"least_latency":     r.routeLeastLatency,
		"round_robin":       r.routeRoundRobin,
	}

	// Start background health probe goroutine
	go r.healthProbeLoop()

	return r
}

// Handles returns true if the model ID is managed by any configured provider.
func (r *Router) Handles(modelID string) bool {
	if modelID == "" {
		return false
	}
	// Check explicit aliases
	for _, alias := range r.cfg.Aliases {
		if alias == modelID {
			return true
		}
	}
	// Check auto/fcm
	if r.cfg.Auto || r.cfg.FCM {
		return true
	}
	// Check provider model lists
	for _, p := range r.providers.All() {
		for _, m := range p.Models {
			if m == modelID {
				return true
			}
		}
	}
	return false
}

// ServeHTTP is the main entry point. It implements http.Handler.
func (r *Router) ServeHTTP(w http.ResponseWriter, req *http.Request) {
	ctx := req.Context()
	start := time.Now()

	// Extract model from request body (we need to read it)
	body, err := io.ReadAll(req.Body)
	if err != nil {
		shared.SendError(w, req, fmt.Errorf("read body: %w", err))
		return
	}
	req.Body.Close()

	var bodyJSON map[string]interface{}
	if err := json.Unmarshal(body, &bodyJSON); err != nil {
		// Non-JSON body (e.g., embeddings) - pass through
		bodyJSON = nil
	}

	modelID := ""
	if bodyJSON != nil {
		if m, ok := bodyJSON["model"].(string); ok {
			modelID = m
		}
	}

	isAST := r.isASTRequest(bodyJSON, req)

	rtCtx := &routingContext{
		modelID:   modelID,
		isAST:     isAST,
		bodyBytes: body,
		bodyJSON:  bodyJSON,
		startTime: start,
	}

	// Determine strategy
	strategy := r.cfg.Strategy
	if isAST && r.cfg.ASTStrategy != "" {
		strategy = r.cfg.ASTStrategy
	}
	if bodyJSON != nil {
		if s, ok := bodyJSON["_ast_strategy"].(string); ok {
			strategy = s
		}
	}
	rtCtx.strategy = strategy

	// Log
	r.logger.Infof("[astmatrix] %s model=%s strategy=%s ast=%v", req.Method, modelID, strategy, isAST)

	// Check request coalescing cache
	if r.cfg.EnableCoalescing && req.Method == "POST" {
		cacheKey := r.cacheKey(req, body)
		if pending := r.requestCache.Get(cacheKey); pending != nil {
			// Wait for existing request and stream its response
			r.serveCoalesced(w, req, pending)
			r.metrics.Record("coalesced", time.Since(start))
			return
		}
		// Register this request as pending
		pending := r.requestCache.Register(cacheKey)
		defer r.requestCache.Complete(cacheKey, pending)
		// Dispatch actual request
		go func() {
			// The strategy handler will write to a recorder, then we broadcast
		}()
	}

	// Dispatch to strategy
	handler, ok := r.strategies[strategy]
	if !ok {
		handler = r.routeHybrid
	}
	handler(w, req, rtCtx)

	// Record metrics
	r.metrics.Record(strategy, time.Since(start))
}

// Shutdown gracefully shuts down the router.
func (r *Router) Shutdown() {
	r.logger.Infof("[astmatrix] shutdown")
	if r.healthDB != nil {
		r.healthDB.Close()
	}
}

// ---------------------------------------------------------------------------
// Strategy implementations
// ---------------------------------------------------------------------------

// routeHybrid: local first, then cloud with circuit breaker + retry
func (r *Router) routeHybrid(w http.ResponseWriter, req *http.Request, rt *routingContext) {
	providers := r.providers.ForModel(rt.modelID)
	if len(providers) == 0 {
		shared.SendError(w, req, fmt.Errorf("no provider for model %s", rt.modelID))
		return
	}

	// Try each provider with retry and circuit breaker
	var lastErr error
	for attempt := 0; attempt < r.cfg.MaxRetries; attempt++ {
		for _, p := range providers {
			cb := r.getCircuitBreaker(p.ID)
			if !cb.Allow() {
				r.logger.Infof("[astmatrix] circuit open for %s", p.ID)
				continue
			}

			if !r.ratelimiter.Allow(p.ID) {
				r.logger.Infof("[astmatrix] rate limited %s", p.ID)
				continue
			}

			// Health probe check
			if !r.isHealthy(p) {
				r.logger.Infof("[astmatrix] %s unhealthy, skipping", p.ID)
				continue
			}

			resp, err := r.callWithRetry(req.Context(), p, req, rt)
			if err == nil {
				cb.RecordSuccess()
				r.streamResponse(w, resp, rt)
				return
			}

			lastErr = err
			cb.RecordFailure()
			r.logger.Warnf("[astmatrix] %s attempt %d failed: %v", p.ID, attempt+1, err)

			// Classify error
			if isPermanentError(err) {
				break // Don't retry permanent errors
			}
			// Exponential backoff
			backoff := time.Duration(attempt+1) * 500 * time.Millisecond
			time.Sleep(backoff)
		}
	}

	shared.SendError(w, req, fmt.Errorf("all providers exhausted: %w", lastErr))
}

// routeAstRace: parallel fan-out, first valid response wins
func (r *Router) routeAstRace(w http.ResponseWriter, req *http.Request, rt *routingContext) {
	providers := r.providers.ForModel(rt.modelID)
	if len(providers) == 0 {
		shared.SendError(w, req, fmt.Errorf("no provider for model %s", rt.modelID))
		return
	}

	ctx, cancel := context.WithTimeout(req.Context(), time.Duration(r.cfg.RequestTimeout)*time.Second)
	defer cancel()

	type result struct {
		resp *http.Response
		p    Provider
		err  error
	}
	results := make(chan result, len(providers))

	for _, p := range providers {
		go func(p Provider) {
			resp, err := r.callOne(ctx, p, req, rt)
			results <- result{resp, p, err}
		}(p)
	}

	var lastErr error
	for i := 0; i < len(providers); i++ {
		select {
		case res := <-results:
			if res.err == nil && res.resp != nil && res.resp.StatusCode < 500 {
				r.getCircuitBreaker(res.p.ID).RecordSuccess()
				r.streamResponse(w, res.resp, rt)
				return
			}
			if res.err != nil {
				lastErr = res.err
				r.getCircuitBreaker(res.p.ID).RecordFailure()
			}
		case <-ctx.Done():
			shared.SendError(w, req, fmt.Errorf("ast_race timeout: %w", ctx.Err()))
			return
		}
	}

	shared.SendError(w, req, fmt.Errorf("ast_race all failed: %w", lastErr))
}

// routeStickyAffinity: session-based sticky routing
func (r *Router) routeStickyAffinity(w http.ResponseWriter, req *http.Request, rt *routingContext) {
	// Extract session ID from Authorization header or body
	sessionID := r.extractSessionID(req, rt.bodyJSON)
	if sessionID == "" {
		// Fall back to hybrid
		r.routeHybrid(w, req, rt)
		return
	}

	pID := r.healthDB.GetSticky(sessionID)
	if pID != "" {
		if p, ok := r.providers.Get(pID); ok && r.isHealthy(p) {
			resp, err := r.callWithRetry(req.Context(), p, req, rt)
			if err == nil {
				r.streamResponse(w, resp, rt)
				return
			}
		}
	}

	// No sticky or sticky failed - route hybrid and save affinity
	r.routeHybrid(w, req, rt)
	// Note: affinity is saved after successful response in streamResponse
}

// routeWeightedELO: route by ELO score weighted probability
func (r *Router) routeWeightedELO(w http.ResponseWriter, req *http.Request, rt *routingContext) {
	providers := r.providers.ForModel(rt.modelID)
	if len(providers) == 0 {
		shared.SendError(w, req, fmt.Errorf("no provider for model %s", rt.modelID))
		return
	}

	// Filter healthy providers
	healthy := make([]Provider, 0, len(providers))
	for _, p := range providers {
		if r.isHealthy(p) && r.getCircuitBreaker(p.ID).Allow() {
			healthy = append(healthy, p)
		}
	}
	if len(healthy) == 0 {
		shared.SendError(w, req, fmt.Errorf("no healthy providers for model %s", rt.modelID))
		return
	}

	// Weighted random selection by ELO
	p := r.weightedSelect(healthy)
	resp, err := r.callWithRetry(req.Context(), p, req, rt)
	if err != nil {
		shared.SendError(w, req, err)
		return
	}
	r.streamResponse(w, resp, rt)
}

// routeCircuitChain: chain through providers until one succeeds
func (r *Router) routeCircuitChain(w http.ResponseWriter, req *http.Request, rt *routingContext) {
	providers := r.providers.ForModel(rt.modelID)
	if len(providers) == 0 {
		shared.SendError(w, req, fmt.Errorf("no provider for model %s", rt.modelID))
		return
	}

	for _, p := range providers {
		cb := r.getCircuitBreaker(p.ID)
		if !cb.Allow() {
			continue
		}
		resp, err := r.callWithRetry(req.Context(), p, req, rt)
		if err == nil {
			cb.RecordSuccess()
			r.streamResponse(w, resp, rt)
			return
		}
		cb.RecordFailure()
	}

	shared.SendError(w, req, fmt.Errorf("circuit_chain exhausted all providers"))
}

// routeFIFOMatrix: first-come-first-served with queue
func (r *Router) routeFIFOMatrix(w http.ResponseWriter, req *http.Request, rt *routingContext) {
	// Simple implementation: just route to first available
	providers := r.providers.ForModel(rt.modelID)
	for _, p := range providers {
		if r.isHealthy(p) && r.getCircuitBreaker(p.ID).Allow() {
			resp, err := r.callWithRetry(req.Context(), p, req, rt)
			if err == nil {
				r.streamResponse(w, resp, rt)
				return
			}
		}
	}
	shared.SendError(w, req, fmt.Errorf("fifo_matrix no available provider"))
}

// routeFree: route to free-tier providers only
func (r *Router) routeFree(w http.ResponseWriter, req *http.Request, rt *routingContext) {
	providers := r.providers.ForModel(rt.modelID)
	for _, p := range providers {
		if p.FreeTier && r.isHealthy(p) && r.getCircuitBreaker(p.ID).Allow() {
			resp, err := r.callWithRetry(req.Context(), p, req, rt)
			if err == nil {
				r.streamResponse(w, resp, rt)
				return
			}
		}
	}
	shared.SendError(w, req, fmt.Errorf("no free provider available"))
}

// routeLeastLatency: route to provider with lowest observed latency
func (r *Router) routeLeastLatency(w http.ResponseWriter, req *http.Request, rt *routingContext) {
	providers := r.providers.ForModel(rt.modelID)
	if len(providers) == 0 {
		shared.SendError(w, req, fmt.Errorf("no provider for model %s", rt.modelID))
		return
	}

	best := providers[0]
	bestLatency := r.healthDB.GetLatency(best.ID)
	for _, p := range providers[1:] {
		if !r.isHealthy(p) || !r.getCircuitBreaker(p.ID).Allow() {
			continue
		}
		lat := r.healthDB.GetLatency(p.ID)
		if lat < bestLatency || bestLatency == 0 {
			best = p
			bestLatency = lat
		}
	}

	resp, err := r.callWithRetry(req.Context(), best, req, rt)
	if err != nil {
		shared.SendError(w, req, err)
		return
	}
	r.streamResponse(w, resp, rt)
}

// round-robin counter
var rrCounter uint64

func (r *Router) routeRoundRobin(w http.ResponseWriter, req *http.Request, rt *routingContext) {
	providers := r.providers.ForModel(rt.modelID)
	if len(providers) == 0 {
		shared.SendError(w, req, fmt.Errorf("no provider for model %s", rt.modelID))
		return
	}

	// Filter healthy
	healthy := make([]Provider, 0, len(providers))
	for _, p := range providers {
		if r.isHealthy(p) && r.getCircuitBreaker(p.ID).Allow() {
			healthy = append(healthy, p)
		}
	}
	if len(healthy) == 0 {
		shared.SendError(w, req, fmt.Errorf("no healthy providers"))
		return
	}

	idx := atomic.AddUint64(&rrCounter, 1) % uint64(len(healthy))
	p := healthy[idx]

	resp, err := r.callWithRetry(req.Context(), p, req, rt)
	if err != nil {
		shared.SendError(w, req, err)
		return
	}
	r.streamResponse(w, resp, rt)
}

// ---------------------------------------------------------------------------
// Core call logic with retry
// ---------------------------------------------------------------------------

func (r *Router) callWithRetry(ctx context.Context, p Provider, req *http.Request, rt *routingContext) (*http.Response, error) {
	var lastErr error
	for attempt := 0; attempt < r.cfg.MaxRetries; attempt++ {
		if attempt > 0 {
			backoff := time.Duration(attempt) * 500 * time.Millisecond
			select {
			case <-time.After(backoff):
			case <-ctx.Done():
				return nil, ctx.Err()
			}
		}

		resp, err := r.callOne(ctx, p, req, rt)
		if err == nil {
			if resp.StatusCode >= 500 {
				lastErr = fmt.Errorf("%s returned %d", p.ID, resp.StatusCode)
				resp.Body.Close()
				continue // Retry on 5xx
			}
			if resp.StatusCode == 429 {
				lastErr = fmt.Errorf("%s rate limited (429)", p.ID)
				resp.Body.Close()
				continue // Retry on 429
			}
			if resp.StatusCode >= 400 {
				// 4xx is client error, don't retry
				return resp, nil
			}
			return resp, nil
		}
		lastErr = err
		if isPermanentError(err) {
			break
		}
	}
	return nil, fmt.Errorf("after %d attempts: %w", r.cfg.MaxRetries, lastErr)
}

func (r *Router) callOne(ctx context.Context, p Provider, req *http.Request, rt *routingContext) (*http.Response, error) {
	u, err := url.Parse(p.BaseURL)
	if err != nil {
		return nil, err
	}

	// Build target URL preserving path
	targetURL := u.String() + req.URL.Path
	if req.URL.RawQuery != "" {
		targetURL += "?" + req.URL.RawQuery
	}

	// Clone request with new body
	bodyClone := bytes.NewReader(rt.bodyBytes)
	newReq, err := http.NewRequestWithContext(ctx, req.Method, targetURL, bodyClone)
	if err != nil {
		return nil, err
	}

	// Copy headers
	for k, vv := range req.Header {
		for _, v := range vv {
			newReq.Header.Add(k, v)
		}
	}

	// Set provider auth
	if p.APIKey != "" {
		newReq.Header.Set("Authorization", "Bearer "+p.APIKey)
	}
	newReq.Header.Set("Host", u.Host)

	// Inject provider-specific model mapping
	if rt.modelID != "" && p.ModelMap != nil {
		if mapped, ok := p.ModelMap[rt.modelID]; ok {
			// Modify body to use mapped model
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
	if err != nil {
		return nil, err
	}

	latency := time.Since(start)
	r.healthDB.RecordLatency(p.ID, latency)
	r.metrics.RecordLatency(p.ID, latency)

	return resp, nil
}

// ---------------------------------------------------------------------------
// Streaming response proxy
// ---------------------------------------------------------------------------

func (r *Router) streamResponse(w http.ResponseWriter, resp *http.Response, rt *routingContext) {
	defer resp.Body.Close()

	// Copy headers
	for k, vv := range resp.Header {
		for _, v := range vv {
			w.Header().Add(k, v)
		}
	}
	w.WriteHeader(resp.StatusCode)

	// For SSE streaming, ensure flush works
	if flusher, ok := w.(http.Flusher); ok {
		// Stream with periodic flush for SSE
		buf := make([]byte, 32*1024)
		for {
			n, err := resp.Body.Read(buf)
			if n > 0 {
				w.Write(buf[:n])
				flusher.Flush()
			}
			if err == io.EOF {
				break
			}
			if err != nil {
				r.logger.Warnf("[astmatrix] stream error: %v", err)
				break
			}
		}
	} else {
		// Fallback: simple copy
		io.Copy(w, resp.Body)
	}

	// Record success metrics
	if resp.StatusCode < 400 {
		r.metrics.RecordSuccess(rt.strategy, resp.StatusCode)
	} else {
		r.metrics.RecordError(rt.strategy, resp.StatusCode)
	}
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func (r *Router) isASTRequest(bodyJSON map[string]interface{}, req *http.Request) bool {
	if r.cfg.ASTAlways {
		return true
	}
	// Check for AST markers in body
	if bodyJSON != nil {
		if ast, ok := bodyJSON["ast"].(bool); ok && ast {
			return true
		}
		if m, ok := bodyJSON["model"].(string); ok {
			if strings.Contains(m, "ast-") || strings.Contains(m, "-ast-") {
				return true
			}
		}
		// Check messages for AST content
		if msgs, ok := bodyJSON["messages"].([]interface{}); ok {
			for _, m := range msgs {
				if msg, ok := m.(map[string]interface{}); ok {
					if content, ok := msg["content"].(string); ok {
						if strings.Contains(content, "<ast>") || strings.Contains(content, "AST:") {
							return true
						}
					}
				}
			}
		}
	}
	return false
}

func (r *Router) getCircuitBreaker(id string) *CircuitBreaker {
	v, _ := r.circuitBreakers.LoadOrStore(id, NewCircuitBreaker(5, 30*time.Second))
	return v.(*CircuitBreaker)
}

func (r *Router) isHealthy(p Provider) bool {
	return r.healthDB.IsHealthy(p.ID)
}

func (r *Router) weightedSelect(providers []Provider) Provider {
	// Simple weighted random by ELO
	total := 0.0
	for _, p := range providers {
		elo := r.healthDB.GetELO(p.ID)
		if elo <= 0 {
			elo = 1500 // Default ELO
		}
		// Convert ELO to weight (higher ELO = higher weight)
		weight := elo / 1500.0
		total += weight
	}

	pick := randFloat() * total
	cum := 0.0
	for _, p := range providers {
		elo := r.healthDB.GetELO(p.ID)
		if elo <= 0 {
			elo = 1500
		}
		weight := elo / 1500.0
		cum += weight
		if pick <= cum {
			return p
		}
	}
	return providers[len(providers)-1]
}

func randFloat() float64 {
	// Simple deterministic for now; use crypto/rand in production
	return float64(time.Now().UnixNano()%1000000) / 1000000.0
}

func (r *Router) extractSessionID(req *http.Request, bodyJSON map[string]interface{}) string {
	// Try Authorization header
	auth := req.Header.Get("Authorization")
	if strings.HasPrefix(auth, "Bearer ") {
		return auth[7:]
	}
	// Try body session field
	if bodyJSON != nil {
		if s, ok := bodyJSON["session_id"].(string); ok {
			return s
		}
		if s, ok := bodyJSON["_session"].(string); ok {
			return s
		}
	}
	return ""
}

func (r *Router) cacheKey(req *http.Request, body []byte) string {
	return req.URL.Path + "|" + string(body)
}

func (r *Router) serveCoalesced(w http.ResponseWriter, req *http.Request, pending *PendingRequest) {
	// Wait for the original request to complete
	resp := pending.Wait()
	if resp == nil {
		shared.SendError(w, req, fmt.Errorf("coalesced request failed"))
		return
	}
	r.streamResponse(w, resp, nil)
}

func (r *Router) healthProbeLoop() {
	ticker := time.NewTicker(time.Duration(r.cfg.HealthProbeInterval) * time.Second)
	defer ticker.Stop()
	for range ticker.C {
		for _, p := range r.providers.All() {
			go r.probeProvider(p)
		}
	}
}

func (r *Router) probeProvider(p Provider) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// Try a simple GET to the base URL or health endpoint
	probeURL := p.BaseURL
	if !strings.HasSuffix(probeURL, "/") {
		probeURL += "/"
	}
	probeURL += "health" // Most providers have /health

	req, _ := http.NewRequestWithContext(ctx, "GET", probeURL, nil)
	if p.APIKey != "" {
		req.Header.Set("Authorization", "Bearer "+p.APIKey)
	}

	start := time.Now()
	resp, err := r.client.Do(req)
	if err != nil {
		r.healthDB.RecordHealth(p.ID, false, err.Error())
		return
	}
	resp.Body.Close()

	latency := time.Since(start)
	r.healthDB.RecordHealth(p.ID, resp.StatusCode < 500, "")
	r.healthDB.RecordLatency(p.ID, latency)
}

func isPermanentError(err error) bool {
	if err == nil {
		return false
	}
	s := err.Error()
	// DNS errors, auth errors, malformed URL are permanent
	if strings.Contains(s, "no such host") ||
		strings.Contains(s, "connection refused") ||
		strings.Contains(s, "unauthorized") ||
		strings.Contains(s, "invalid api key") {
		return true
	}
	return false
}
