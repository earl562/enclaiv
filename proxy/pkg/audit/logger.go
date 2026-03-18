package audit

import (
	"log/slog"
	"time"
)

// Entry captures all metadata for a single proxied connection.
type Entry struct {
	Timestamp     time.Time `json:"timestamp"`
	AgentID       string    `json:"agent_id"`
	SessionID     string    `json:"session_id"`
	Destination   string    `json:"destination"`
	Protocol      string    `json:"protocol"`
	Action        string    `json:"action"`
	BytesSent     int64     `json:"bytes_sent"`
	BytesReceived int64     `json:"bytes_received"`
	DurationMs    int64     `json:"duration_ms"`
}

// Logger writes structured JSON audit entries via slog.
type Logger struct {
	logger *slog.Logger
}

// NewLogger returns a Logger that writes to the provided slog.Logger.
// Pass slog.Default() to use the process-wide default logger.
func NewLogger(l *slog.Logger) *Logger {
	if l == nil {
		l = slog.Default()
	}
	return &Logger{logger: l}
}

// Log emits a single structured audit entry.
func (al *Logger) Log(e Entry) {
	if e.Timestamp.IsZero() {
		e.Timestamp = time.Now().UTC()
	}

	al.logger.Info("connection",
		"timestamp", e.Timestamp.Format(time.RFC3339),
		"agent_id", e.AgentID,
		"session_id", e.SessionID,
		"destination", e.Destination,
		"protocol", e.Protocol,
		"action", e.Action,
		"bytes_sent", e.BytesSent,
		"bytes_received", e.BytesReceived,
		"duration_ms", e.DurationMs,
	)
}
