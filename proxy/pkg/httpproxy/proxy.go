package httpproxy

import (
	"fmt"
	"io"
	"log/slog"
	"net"
	"net/http"
	"time"

	"github.com/enclaiv/enclaiv/proxy/pkg/allowlist"
	"github.com/enclaiv/enclaiv/proxy/pkg/audit"
	"github.com/enclaiv/enclaiv/proxy/pkg/credentials"
	"github.com/enclaiv/enclaiv/proxy/pkg/violations"
)

// Proxy is an HTTP CONNECT proxy that enforces an allowlist and injects
// credentials for known upstream providers.
type Proxy struct {
	allowlist  *allowlist.Allowlist
	injector   *credentials.Injector
	violations *violations.ViolationStore
	audit      *audit.Logger
	port       int
}

// Config holds all dependencies needed to construct a Proxy.
type Config struct {
	Allowlist  *allowlist.Allowlist
	Injector   *credentials.Injector
	Violations *violations.ViolationStore
	Audit      *audit.Logger
	Port       int
}

// New creates a Proxy from the given Config.
func New(cfg Config) *Proxy {
	return &Proxy{
		allowlist:  cfg.Allowlist,
		injector:   cfg.Injector,
		violations: cfg.Violations,
		audit:      cfg.Audit,
		port:       cfg.Port,
	}
}

// ListenAndServe starts the HTTP proxy and blocks until it returns an error.
func (p *Proxy) ListenAndServe() error {
	addr := fmt.Sprintf(":%d", p.port)
	slog.Info("HTTP proxy listening", "addr", addr)
	return http.ListenAndServe(addr, p)
}

// ServeHTTP handles every proxied request.
// CONNECT requests are tunnelled; plain HTTP requests are forwarded.
func (p *Proxy) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodConnect {
		p.handleConnect(w, r)
		return
	}
	p.handleHTTP(w, r)
}

// handleConnect processes HTTP CONNECT tunnel requests.
func (p *Proxy) handleConnect(w http.ResponseWriter, r *http.Request) {
	host := r.Host
	start := time.Now()

	if !p.allowlist.IsAllowed(host) {
		p.recordViolation(r, host, "blocked", "domain not in allowlist")
		http.Error(w, "403 Forbidden", http.StatusForbidden)
		slog.Warn("CONNECT blocked", "host", host)
		return
	}

	slog.Info("CONNECT allowed", "host", host)

	// Take over the raw TCP connection from the HTTP server.
	hijacker, ok := w.(http.Hijacker)
	if !ok {
		http.Error(w, "hijacking not supported", http.StatusInternalServerError)
		return
	}

	clientConn, _, err := hijacker.Hijack()
	if err != nil {
		slog.Error("hijack failed", "host", host, "error", err)
		return
	}
	defer clientConn.Close()

	// Determine dial target: if credentials need injection, route through
	// the credential injector shim; otherwise connect directly.
	dialTarget := host
	if p.injector != nil && p.injector.NeedsInjection(host) {
		dialTarget = host // direct dial; injection happens at the HTTP layer
	}

	upstreamConn, err := net.DialTimeout("tcp", dialTarget, 30*time.Second)
	if err != nil {
		slog.Error("upstream dial failed", "host", host, "error", err)
		// Inform the client that the tunnel could not be established.
		_, _ = fmt.Fprintf(clientConn, "HTTP/1.1 502 Bad Gateway\r\n\r\n")
		return
	}
	defer upstreamConn.Close()

	// Signal the client that the tunnel is established.
	_, err = fmt.Fprint(clientConn, "HTTP/1.1 200 Connection Established\r\n\r\n")
	if err != nil {
		slog.Error("failed to send 200 to client", "host", host, "error", err)
		return
	}

	bytesSent, bytesReceived := pipe(clientConn, upstreamConn)

	p.audit.Log(audit.Entry{
		Timestamp:     start,
		Destination:   host,
		Protocol:      "HTTPS",
		Action:        "allowed",
		BytesSent:     bytesSent,
		BytesReceived: bytesReceived,
		DurationMs:    time.Since(start).Milliseconds(),
	})
}

// handleHTTP forwards plain HTTP requests, injecting credentials where required.
func (p *Proxy) handleHTTP(w http.ResponseWriter, r *http.Request) {
	host := r.Host
	start := time.Now()

	if !p.allowlist.IsAllowed(host) {
		p.recordViolation(r, host, "blocked", "domain not in allowlist")
		http.Error(w, "403 Forbidden", http.StatusForbidden)
		slog.Warn("HTTP blocked", "host", host, "url", r.URL.String())
		return
	}

	if p.injector != nil {
		p.injector.Inject(r)
	}

	// Strip hop-by-hop headers and the proxy-specific ones.
	r.RequestURI = ""
	removeHopByHopHeaders(r.Header)

	resp, err := http.DefaultTransport.RoundTrip(r)
	if err != nil {
		slog.Error("upstream request failed", "host", host, "error", err)
		http.Error(w, "502 Bad Gateway", http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()

	removeHopByHopHeaders(resp.Header)
	copyHeaders(w.Header(), resp.Header)
	w.WriteHeader(resp.StatusCode)

	bytesReceived, err := io.Copy(w, resp.Body)
	if err != nil {
		slog.Error("failed to copy response body", "host", host, "error", err)
	}

	p.audit.Log(audit.Entry{
		Timestamp:     start,
		Destination:   host,
		Protocol:      "HTTP",
		Action:        "allowed",
		BytesReceived: bytesReceived,
		DurationMs:    time.Since(start).Milliseconds(),
	})
}

// recordViolation logs a blocked connection into the violation store.
func (p *Proxy) recordViolation(r *http.Request, host, action, reason string) {
	if p.violations == nil {
		return
	}
	p.violations.Record(violations.Violation{
		Destination: host,
		Protocol:    "HTTP",
		Action:      action,
		Reason:      reason,
	})
}

// pipe performs bidirectional byte copying between two net.Conn connections.
// It returns the number of bytes written to upstream (sent) and read from
// upstream (received).
func pipe(client, upstream net.Conn) (sent, received int64) {
	done := make(chan int64, 2)

	go func() {
		n, _ := io.Copy(upstream, client)
		done <- n
		// Half-close so upstream sees EOF.
		if tc, ok := upstream.(*net.TCPConn); ok {
			_ = tc.CloseWrite()
		}
	}()

	go func() {
		n, _ := io.Copy(client, upstream)
		done <- n
		if tc, ok := client.(*net.TCPConn); ok {
			_ = tc.CloseWrite()
		}
	}()

	sent = <-done
	received = <-done
	return sent, received
}

// removeHopByHopHeaders deletes headers that must not be forwarded.
func removeHopByHopHeaders(h http.Header) {
	hopByHop := []string{
		"Connection", "Keep-Alive", "Proxy-Authenticate",
		"Proxy-Authorization", "TE", "Trailers",
		"Transfer-Encoding", "Upgrade",
	}
	for _, key := range hopByHop {
		h.Del(key)
	}
}

// copyHeaders copies all headers from src to dst.
func copyHeaders(dst, src http.Header) {
	for key, values := range src {
		for _, v := range values {
			dst.Add(key, v)
		}
	}
}
