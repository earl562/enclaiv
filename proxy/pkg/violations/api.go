package violations

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
)

// Server exposes a read-only HTTP API for querying violations.
type Server struct {
	store *ViolationStore
	port  int
}

// NewServer creates a violations API server backed by the given store.
func NewServer(store *ViolationStore, port int) *Server {
	return &Server{store: store, port: port}
}

// ListenAndServe starts the violations API on the configured port.
// It blocks until the server exits and returns any error.
func (s *Server) ListenAndServe() error {
	mux := http.NewServeMux()
	mux.HandleFunc("/violations", s.handleViolations)

	addr := fmt.Sprintf(":%d", s.port)
	slog.Info("violations API listening", "addr", addr)
	return http.ListenAndServe(addr, mux)
}

// handleViolations handles GET /violations[?agent=xxx][&session=yyy].
func (s *Server) handleViolations(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	agentID := r.URL.Query().Get("agent")
	sessionID := r.URL.Query().Get("session")

	var result []Violation
	if agentID == "" && sessionID == "" {
		result = s.store.All()
	} else {
		result = s.store.Query(agentID, sessionID)
	}

	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(result); err != nil {
		slog.Error("failed to encode violations response", "error", err)
	}
}
