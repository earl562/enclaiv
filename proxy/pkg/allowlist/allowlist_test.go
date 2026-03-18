package allowlist

import (
	"testing"
)

func TestExactMatch(t *testing.T) {
	al := NewAllowlist([]string{"example.com"}, nil)
	if !al.IsAllowed("example.com") {
		t.Fatal("exact match should be allowed")
	}
}

func TestExactMatchWithPort(t *testing.T) {
	al := NewAllowlist([]string{"example.com"}, nil)
	if !al.IsAllowed("example.com:443") {
		t.Fatal("exact match with port should be allowed")
	}
}

func TestWildcardMatch(t *testing.T) {
	al := NewAllowlist([]string{"*.example.com"}, nil)

	cases := []struct {
		host    string
		allowed bool
	}{
		{"api.example.com", true},
		{"cdn.example.com", true},
		{"example.com", false},           // wildcard does not match bare domain
		{"sub.api.example.com", false},   // two labels under wildcard not matched
		{"notexample.com", false},
		{"api.example.com:443", true},    // port is stripped before match
	}

	for _, tc := range cases {
		got := al.IsAllowed(tc.host)
		if got != tc.allowed {
			t.Errorf("IsAllowed(%q) = %v, want %v", tc.host, got, tc.allowed)
		}
	}
}

func TestDenyOverridesAllow(t *testing.T) {
	al := NewAllowlist(
		[]string{"*.example.com"},
		[]string{"bad.example.com"},
	)

	if al.IsAllowed("bad.example.com") {
		t.Fatal("denied domain must not be allowed even when covered by wildcard allow")
	}
	if !al.IsAllowed("good.example.com") {
		t.Fatal("non-denied subdomain should be allowed")
	}
}

func TestDefaultDeny(t *testing.T) {
	al := NewAllowlist([]string{"example.com"}, nil)

	if al.IsAllowed("other.com") {
		t.Fatal("unlisted domain must be denied by default")
	}
	if al.IsAllowed("") {
		t.Fatal("empty host must be denied")
	}
}

func TestHotReload(t *testing.T) {
	al := NewAllowlist(nil, nil)

	if al.IsAllowed("newdomain.com") {
		t.Fatal("domain should not be allowed before AddDomain")
	}

	al.AddDomain("newdomain.com")

	if !al.IsAllowed("newdomain.com") {
		t.Fatal("domain should be allowed after AddDomain")
	}
}

func TestHotReloadConcurrent(t *testing.T) {
	al := NewAllowlist([]string{"base.com"}, nil)

	done := make(chan struct{})
	go func() {
		for i := 0; i < 100; i++ {
			al.AddDomain("dynamic.com")
		}
		close(done)
	}()

	for i := 0; i < 100; i++ {
		_ = al.IsAllowed("base.com")
	}
	<-done
}
