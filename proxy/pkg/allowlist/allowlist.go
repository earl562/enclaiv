package allowlist

import (
	"strings"
	"sync"
)

// Allowlist enforces domain-level access control with wildcard support.
// Policy: check denied first, then allowed, default deny.
type Allowlist struct {
	mu      sync.RWMutex
	allowed []string
	denied  []string
}

// NewAllowlist constructs an Allowlist with initial allowed and denied patterns.
func NewAllowlist(allowed, denied []string) *Allowlist {
	a := make([]string, len(allowed))
	copy(a, allowed)
	d := make([]string, len(denied))
	copy(d, denied)
	return &Allowlist{
		allowed: a,
		denied:  d,
	}
}

// IsAllowed returns true only if host matches an allowed pattern and no denied pattern.
// Evaluation order: denied → allowed → default deny.
func (al *Allowlist) IsAllowed(host string) bool {
	// Strip port if present.
	h := stripPort(host)

	al.mu.RLock()
	defer al.mu.RUnlock()

	for _, pattern := range al.denied {
		if matchDomain(pattern, h) {
			return false
		}
	}

	for _, pattern := range al.allowed {
		if matchDomain(pattern, h) {
			return true
		}
	}

	// Default deny.
	return false
}

// AddDomain appends a domain to the allowed list for hot-reload / TUI approval.
func (al *Allowlist) AddDomain(domain string) {
	al.mu.Lock()
	defer al.mu.Unlock()
	al.allowed = append(al.allowed, domain)
}

// matchDomain returns true when pattern matches host.
// Supports exact matches and *.example.com wildcards.
func matchDomain(pattern, host string) bool {
	if pattern == host {
		return true
	}

	if strings.HasPrefix(pattern, "*.") {
		suffix := pattern[1:] // e.g. ".example.com"
		if strings.HasSuffix(host, suffix) {
			// Ensure the wildcard covers exactly one label, not zero.
			// "*.example.com" must not match "example.com" itself.
			prefix := host[:len(host)-len(suffix)]
			return prefix != "" && !strings.Contains(prefix, ".")
		}
	}

	return false
}

// stripPort removes a trailing ":port" component from host.
func stripPort(host string) string {
	if idx := strings.LastIndex(host, ":"); idx != -1 {
		// Make sure it is not an IPv6 address without a port.
		if !strings.Contains(host[:idx], ":") {
			return host[:idx]
		}
	}
	return host
}
