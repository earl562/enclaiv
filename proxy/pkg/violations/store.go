package violations

import (
	"log/slog"
	"sync"
	"time"
)

// Violation records a single policy enforcement event.
type Violation struct {
	Timestamp   time.Time `json:"timestamp"`
	AgentID     string    `json:"agent_id"`
	SessionID   string    `json:"session_id"`
	Destination string    `json:"destination"`
	Protocol    string    `json:"protocol"`
	Action      string    `json:"action"`
	Reason      string    `json:"reason"`
	TraceID     string    `json:"trace_id"`
}

// ViolationStore holds all recorded violations and provides thread-safe access.
type ViolationStore struct {
	mu         sync.RWMutex
	violations []Violation
}

// NewViolationStore returns an empty, ready-to-use ViolationStore.
func NewViolationStore() *ViolationStore {
	return &ViolationStore{
		violations: make([]Violation, 0),
	}
}

// Record appends a violation and emits a structured warning log.
func (vs *ViolationStore) Record(v Violation) {
	if v.Timestamp.IsZero() {
		v.Timestamp = time.Now().UTC()
	}

	vs.mu.Lock()
	vs.violations = append(vs.violations, v)
	vs.mu.Unlock()

	slog.Warn("policy violation",
		"agent_id", v.AgentID,
		"session_id", v.SessionID,
		"destination", v.Destination,
		"protocol", v.Protocol,
		"action", v.Action,
		"reason", v.Reason,
		"trace_id", v.TraceID,
	)
}

// Query returns violations filtered by agentID and/or sessionID.
// Empty string values are treated as "match any".
func (vs *ViolationStore) Query(agentID, sessionID string) []Violation {
	vs.mu.RLock()
	defer vs.mu.RUnlock()

	result := make([]Violation, 0)
	for _, v := range vs.violations {
		if agentID != "" && v.AgentID != agentID {
			continue
		}
		if sessionID != "" && v.SessionID != sessionID {
			continue
		}
		result = append(result, v)
	}
	return result
}

// All returns a snapshot of every recorded violation.
func (vs *ViolationStore) All() []Violation {
	vs.mu.RLock()
	defer vs.mu.RUnlock()

	snapshot := make([]Violation, len(vs.violations))
	copy(snapshot, vs.violations)
	return snapshot
}
