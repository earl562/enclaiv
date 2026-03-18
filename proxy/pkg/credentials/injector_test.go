package credentials

import (
	"net/http"
	"testing"
)

func buildInjector() *Injector {
	creds := map[string]Credential{
		"api.anthropic.com": {
			Host:     "api.anthropic.com",
			Provider: "anthropic",
			Value:    "sk-ant-test-key",
		},
		"api.openai.com": {
			Host:     "api.openai.com",
			Provider: "openai",
			Value:    "sk-openai-test-key",
		},
		"custom.api.com": {
			Host:       "custom.api.com",
			HeaderName: "X-Custom-Token",
			Value:      "custom-secret",
		},
	}
	return NewInjector(creds)
}

func TestNeedsInjection_Known(t *testing.T) {
	inj := buildInjector()
	if !inj.NeedsInjection("api.anthropic.com") {
		t.Fatal("expected NeedsInjection=true for api.anthropic.com")
	}
}

func TestNeedsInjection_Unknown(t *testing.T) {
	inj := buildInjector()
	if inj.NeedsInjection("unknown.example.com") {
		t.Fatal("expected NeedsInjection=false for unknown host")
	}
}

func TestNeedsInjection_PortStripped(t *testing.T) {
	inj := buildInjector()
	if !inj.NeedsInjection("api.anthropic.com:443") {
		t.Fatal("NeedsInjection must match after stripping port")
	}
}

func TestInject_Anthropic(t *testing.T) {
	inj := buildInjector()

	req, _ := http.NewRequest(http.MethodGet, "https://api.anthropic.com/v1/messages", nil)
	req.Host = "api.anthropic.com"

	inj.Inject(req)

	got := req.Header.Get("x-api-key")
	if got != "sk-ant-test-key" {
		t.Fatalf("expected x-api-key=sk-ant-test-key, got %q", got)
	}
}

func TestInject_OpenAI(t *testing.T) {
	inj := buildInjector()

	req, _ := http.NewRequest(http.MethodPost, "https://api.openai.com/v1/chat/completions", nil)
	req.Host = "api.openai.com"

	inj.Inject(req)

	got := req.Header.Get("Authorization")
	want := "Bearer sk-openai-test-key"
	if got != want {
		t.Fatalf("expected Authorization=%q, got %q", want, got)
	}
}

func TestInject_CustomHeader(t *testing.T) {
	inj := buildInjector()

	req, _ := http.NewRequest(http.MethodGet, "https://custom.api.com/resource", nil)
	req.Host = "custom.api.com"

	inj.Inject(req)

	got := req.Header.Get("X-Custom-Token")
	if got != "custom-secret" {
		t.Fatalf("expected X-Custom-Token=custom-secret, got %q", got)
	}
}

func TestInject_UnknownHost_NoHeaders(t *testing.T) {
	inj := buildInjector()

	req, _ := http.NewRequest(http.MethodGet, "https://unknown.example.com/", nil)
	req.Host = "unknown.example.com"
	req.Header = make(http.Header)

	inj.Inject(req)

	if len(req.Header) != 0 {
		t.Fatalf("expected no headers added for unknown host, got %v", req.Header)
	}
}

func TestInject_NilRequest(t *testing.T) {
	inj := buildInjector()
	// Must not panic.
	inj.Inject(nil)
}

func TestInject_CaseInsensitiveHost(t *testing.T) {
	inj := buildInjector()

	req, _ := http.NewRequest(http.MethodGet, "https://API.ANTHROPIC.COM/v1/messages", nil)
	req.Host = "API.ANTHROPIC.COM"

	inj.Inject(req)

	got := req.Header.Get("x-api-key")
	if got != "sk-ant-test-key" {
		t.Fatalf("expected x-api-key after case-insensitive host match, got %q", got)
	}
}
