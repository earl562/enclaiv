package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log/slog"
	"os"

	"github.com/enclaiv/enclaiv/proxy/pkg/allowlist"
	"github.com/enclaiv/enclaiv/proxy/pkg/audit"
	"github.com/enclaiv/enclaiv/proxy/pkg/credentials"
	"github.com/enclaiv/enclaiv/proxy/pkg/httpproxy"
	"github.com/enclaiv/enclaiv/proxy/pkg/violations"
)

// allowlistConfig is the JSON schema for --config.
type allowlistConfig struct {
	Allowed []string `json:"allowed"`
	Denied  []string `json:"denied"`
}

// credConfig is the JSON schema for --cred-config.
// Keys are host names; values describe the credential to inject.
type credConfig map[string]credentials.Credential

func main() {
	port := flag.Int("port", 9080, "HTTP proxy listen port")
	configPath := flag.String("config", "", "path to allowlist JSON config")
	credConfigPath := flag.String("cred-config", "", "path to credentials JSON config")
	violationsPort := flag.Int("violations-port", 9081, "violations API listen port")
	flag.Parse()

	setupLogging()

	al, err := loadAllowlist(*configPath)
	if err != nil {
		slog.Error("failed to load allowlist", "error", err)
		os.Exit(1)
	}

	inj, err := loadCredentials(*credConfigPath)
	if err != nil {
		slog.Error("failed to load credentials", "error", err)
		os.Exit(1)
	}

	vs := violations.NewViolationStore()
	au := audit.NewLogger(slog.Default())

	// Start violations API on its own port.
	vServer := violations.NewServer(vs, *violationsPort)
	go func() {
		if err := vServer.ListenAndServe(); err != nil {
			slog.Error("violations API exited", "error", err)
			os.Exit(1)
		}
	}()

	// Start the HTTP proxy (blocks).
	proxy := httpproxy.New(httpproxy.Config{
		Allowlist:  al,
		Injector:   inj,
		Violations: vs,
		Audit:      au,
		Port:       *port,
	})

	slog.Info("enclaiv proxy starting",
		"proxy_port", *port,
		"violations_port", *violationsPort,
	)

	if err := proxy.ListenAndServe(); err != nil {
		slog.Error("proxy exited", "error", err)
		os.Exit(1)
	}
}

// setupLogging configures slog to emit structured JSON to stdout.
func setupLogging() {
	handler := slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	})
	slog.SetDefault(slog.New(handler))
}

// loadAllowlist reads the allowlist JSON config from path.
// If path is empty, an empty (deny-all) allowlist is returned.
func loadAllowlist(path string) (*allowlist.Allowlist, error) {
	if path == "" {
		slog.Warn("no allowlist config provided; all domains will be denied")
		return allowlist.NewAllowlist(nil, nil), nil
	}

	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read allowlist config %q: %w", path, err)
	}

	var cfg allowlistConfig
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("parse allowlist config %q: %w", path, err)
	}

	return allowlist.NewAllowlist(cfg.Allowed, cfg.Denied), nil
}

// loadCredentials reads the credential injection config from path.
// If path is empty, an injector with no credentials is returned.
func loadCredentials(path string) (*credentials.Injector, error) {
	if path == "" {
		slog.Warn("no credential config provided; credential injection disabled")
		return credentials.NewInjector(map[string]credentials.Credential{}), nil
	}

	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read credential config %q: %w", path, err)
	}

	var cfg credConfig
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("parse credential config %q: %w", path, err)
	}

	return credentials.NewInjector(cfg), nil
}
