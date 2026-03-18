# ---------------------------------------------------------------------------
# Enclaiv — top-level Makefile
# ---------------------------------------------------------------------------
# Targets:
#   build   — build the Go proxy binary + install the Python CLI
#   test    — run Go tests + Python tests
#   run     — start the local dev stack via Docker Compose
#   lint    — go vet + ruff check
#   clean   — remove build artefacts
#   proxy   — build just the Go proxy
#   cli     — install just the Python CLI
# ---------------------------------------------------------------------------

.PHONY: build test run lint clean proxy cli

# ---- Paths -----------------------------------------------------------------
PROXY_DIR   := ./proxy
CLI_DIR     := ./cli
BIN_DIR     := ./bin
PROXY_BIN   := $(BIN_DIR)/enclaiv-proxy

# ---- Build flags -----------------------------------------------------------
GO          ?= go
GOFLAGS     ?= -trimpath
CGO_ENABLED ?= 0

# ---- Python / tooling -------------------------------------------------------
PYTHON      ?= python3
PIP         ?= pip3
RUFF        ?= ruff
PYTEST      ?= pytest

# ---- Default target --------------------------------------------------------
all: build

# ---- build -----------------------------------------------------------------
build: proxy cli

## proxy: Compile the Go allowlist proxy binary into ./bin/
proxy:
	@echo "==> Building proxy …"
	@mkdir -p $(BIN_DIR)
	CGO_ENABLED=$(CGO_ENABLED) $(GO) build $(GOFLAGS) \
		-o $(PROXY_BIN) \
		./$(PROXY_DIR)/cmd/proxy
	@echo "    Built: $(PROXY_BIN)"

## cli: Install the Python CLI in editable mode
cli:
	@echo "==> Installing Python CLI …"
	$(PIP) install --quiet -e "$(CLI_DIR)[dev]"
	@echo "    Installed: enclaiv CLI"

# ---- test ------------------------------------------------------------------
test: test-go test-python

## test-go: Run Go unit + race tests with coverage
test-go:
	@echo "==> Running Go tests …"
	$(GO) test -race -cover ./$(PROXY_DIR)/...

## test-python: Run Python tests with coverage
test-python:
	@echo "==> Running Python tests …"
	$(PYTEST) $(CLI_DIR) --cov=$(CLI_DIR)/enclaiv --cov-report=term-missing -q

# ---- run -------------------------------------------------------------------
## run: Start the full local dev stack (detached)
run:
	@echo "==> Starting dev stack …"
	docker compose up -d
	@echo "    Proxy:         http://localhost:9080"
	@echo "    Control plane: http://localhost:8080"
	@echo "    Prometheus:    http://localhost:9090"
	@echo "    Grafana:       http://localhost:3000"

## stop: Stop the dev stack without removing volumes
stop:
	docker compose down

# ---- lint ------------------------------------------------------------------
lint: lint-go lint-python

## lint-go: Run go vet on all packages
lint-go:
	@echo "==> go vet …"
	$(GO) vet ./$(PROXY_DIR)/...

## lint-python: Run ruff on the CLI source
lint-python:
	@echo "==> ruff check …"
	$(RUFF) check $(CLI_DIR)

# ---- clean -----------------------------------------------------------------
## clean: Remove compiled binaries and Python cache artefacts
clean:
	@echo "==> Cleaning …"
	rm -rf $(BIN_DIR)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "    Done."

# ---- help ------------------------------------------------------------------
help:
	@echo ""
	@echo "Enclaiv build targets:"
	@echo "  make build        Build proxy binary + install Python CLI"
	@echo "  make proxy        Build just the Go proxy"
	@echo "  make cli          Install just the Python CLI"
	@echo "  make test         Run all tests (Go + Python)"
	@echo "  make test-go      Run Go tests with race detector"
	@echo "  make test-python  Run Python tests with coverage"
	@echo "  make run          Start local dev stack (docker compose up -d)"
	@echo "  make stop         Stop local dev stack"
	@echo "  make lint         Run go vet + ruff check"
	@echo "  make clean        Remove build artefacts"
	@echo ""
