# ── Stage 1: build ────────────────────────────────────────────────────────────
FROM golang:1.22-alpine AS builder

WORKDIR /src

# Copy module files first for better layer caching.
COPY go.mod ./

# Download dependencies (no external deps currently, but this future-proofs the image).
RUN go mod download

# Copy the rest of the source tree.
COPY . .

# Build a fully static binary with no CGO so it runs on scratch.
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build \
      -ldflags="-s -w" \
      -trimpath \
      -o /enclaiv-proxy \
      ./cmd/proxy

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM scratch

# Copy the statically linked binary.
COPY --from=builder /enclaiv-proxy /enclaiv-proxy

# Copy CA certificates so the proxy can verify TLS upstream.
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# HTTP proxy port.
EXPOSE 9080
# Violations API port.
EXPOSE 9081

ENTRYPOINT ["/enclaiv-proxy"]
