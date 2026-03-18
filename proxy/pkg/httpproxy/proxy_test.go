package httpproxy

import (
	"net"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/enclaiv/enclaiv/proxy/pkg/allowlist"
	"github.com/enclaiv/enclaiv/proxy/pkg/audit"
	"github.com/enclaiv/enclaiv/proxy/pkg/credentials"
	"github.com/enclaiv/enclaiv/proxy/pkg/violations"
)

// buildProxy returns a Proxy configured with the given allowed/denied lists.
func buildProxy(allowed, denied []string) *Proxy {
	al := allowlist.NewAllowlist(allowed, denied)
	vs := violations.NewViolationStore()
	inj := credentials.NewInjector(map[string]credentials.Credential{})
	au := audit.NewLogger(nil)
	return New(Config{
		Allowlist:  al,
		Injector:   inj,
		Violations: vs,
		Audit:      au,
		Port:       9080,
	})
}

// roundTripHTTP sends a plain HTTP request through the proxy using httptest.
func roundTripHTTP(t *testing.T, proxy *Proxy, target string) *http.Response {
	t.Helper()
	req := httptest.NewRequest(http.MethodGet, target, nil)
	// httptest.NewRequest sets RequestURI; the proxy strips it for forwarding.
	req.Host = req.URL.Host
	w := httptest.NewRecorder()
	proxy.ServeHTTP(w, req)
	return w.Result()
}

func TestAllowedDomain_HTTPRequest(t *testing.T) {
	// Spin up a real upstream to receive the forwarded request.
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	defer upstream.Close()

	// upstream.Listener.Addr().String() is "127.0.0.1:<port>".
	// The allowlist strips ports during matching, so we register the bare host.
	upstreamAddr := upstream.Listener.Addr().String()
	bareHost, _, err := net.SplitHostPort(upstreamAddr)
	if err != nil {
		t.Fatalf("failed to split upstream addr: %v", err)
	}

	proxy := buildProxy([]string{bareHost}, nil)

	req := httptest.NewRequest(http.MethodGet, upstream.URL+"/", nil)
	req.Host = upstreamAddr
	req.RequestURI = ""
	w := httptest.NewRecorder()
	proxy.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200 for allowed domain, got %d", w.Code)
	}
}

func TestBlockedDomain_HTTPRequest(t *testing.T) {
	proxy := buildProxy([]string{"allowed.com"}, nil)

	req := httptest.NewRequest(http.MethodGet, "http://blocked.example.com/", nil)
	req.Host = "blocked.example.com"
	w := httptest.NewRecorder()
	proxy.ServeHTTP(w, req)

	if w.Code != http.StatusForbidden {
		t.Fatalf("expected 403 for blocked domain, got %d", w.Code)
	}
}

func TestBlockedDomain_RecordsViolation(t *testing.T) {
	al := allowlist.NewAllowlist([]string{"allowed.com"}, nil)
	vs := violations.NewViolationStore()
	au := audit.NewLogger(nil)
	proxy := New(Config{
		Allowlist:  al,
		Violations: vs,
		Audit:      au,
		Port:       9080,
	})

	req := httptest.NewRequest(http.MethodGet, "http://evil.com/", nil)
	req.Host = "evil.com"
	w := httptest.NewRecorder()
	proxy.ServeHTTP(w, req)

	if w.Code != http.StatusForbidden {
		t.Fatalf("expected 403, got %d", w.Code)
	}
	if len(vs.All()) != 1 {
		t.Fatalf("expected 1 violation recorded, got %d", len(vs.All()))
	}
	if vs.All()[0].Destination != "evil.com" {
		t.Fatalf("unexpected violation destination: %q", vs.All()[0].Destination)
	}
}

func TestWildcardDomain_HTTPRequest(t *testing.T) {
	// A wildcard entry covers any single-label subdomain.
	proxy := buildProxy([]string{"*.example.com"}, nil)

	// Blocked because not in the allowlist.
	req := httptest.NewRequest(http.MethodGet, "http://other.org/", nil)
	req.Host = "other.org"
	w := httptest.NewRecorder()
	proxy.ServeHTTP(w, req)
	if w.Code != http.StatusForbidden {
		t.Fatalf("expected 403 for non-wildcard domain, got %d", w.Code)
	}
}

func TestConnectRequest_BlockedDomain(t *testing.T) {
	proxy := buildProxy([]string{"allowed.com"}, nil)

	req := httptest.NewRequest(http.MethodConnect, "//evil.com:443", nil)
	req.Host = "evil.com:443"
	w := httptest.NewRecorder()
	proxy.ServeHTTP(w, req)

	if w.Code != http.StatusForbidden {
		t.Fatalf("expected 403 for blocked CONNECT, got %d", w.Code)
	}
}
