package credentials

import (
	"net/http"
	"strings"
	"sync"
)

// Credential describes how to inject an API key for a specific upstream host.
type Credential struct {
	// Host is the upstream hostname this credential applies to (e.g. "api.anthropic.com").
	Host string `json:"host"`
	// HeaderName is the HTTP header to set (e.g. "x-api-key", "Authorization").
	HeaderName string `json:"header_name"`
	// Value is the raw header value.
	// For Bearer-style headers include the "Bearer " prefix in the config,
	// or set Provider to have it applied automatically.
	Value string `json:"value"`
	// Provider controls automatic header formatting.
	// Supported values: "anthropic", "openai".
	// When empty, Value is used verbatim.
	Provider string `json:"provider,omitempty"`
}

// Injector maps upstream hosts to their credentials and injects them into requests.
type Injector struct {
	mu    sync.RWMutex
	creds map[string]Credential // keyed by normalised host
}

// NewInjector constructs an Injector from a host-keyed credential map.
func NewInjector(creds map[string]Credential) *Injector {
	normalised := make(map[string]Credential, len(creds))
	for k, v := range creds {
		normalised[normaliseHost(k)] = v
	}
	return &Injector{creds: normalised}
}

// NeedsInjection returns true when the given host has a registered credential.
func (inj *Injector) NeedsInjection(host string) bool {
	inj.mu.RLock()
	defer inj.mu.RUnlock()
	_, ok := inj.creds[normaliseHost(host)]
	return ok
}

// Inject adds the appropriate credential header to r.
// It does nothing when no credential is registered for the request's host.
func (inj *Injector) Inject(r *http.Request) {
	if r == nil {
		return
	}
	host := normaliseHost(r.Host)

	inj.mu.RLock()
	cred, ok := inj.creds[host]
	inj.mu.RUnlock()

	if !ok {
		return
	}

	headerName, headerValue := buildHeader(cred)
	r.Header.Set(headerName, headerValue)
}

// buildHeader returns the header name and value for the given credential,
// applying provider-specific formatting where applicable.
func buildHeader(cred Credential) (name, value string) {
	switch strings.ToLower(cred.Provider) {
	case "anthropic":
		return "x-api-key", cred.Value
	case "openai":
		return "Authorization", "Bearer " + cred.Value
	default:
		return cred.HeaderName, cred.Value
	}
}

// normaliseHost strips the port component and lowercases the result.
func normaliseHost(host string) string {
	h := strings.ToLower(host)
	if idx := strings.LastIndex(h, ":"); idx != -1 {
		if !strings.Contains(h[:idx], ":") {
			return h[:idx]
		}
	}
	return h
}
