package violations

import (
	"sync"
	"testing"
	"time"
)

func makeViolation(agentID, sessionID, destination string) Violation {
	return Violation{
		Timestamp:   time.Now().UTC(),
		AgentID:     agentID,
		SessionID:   sessionID,
		Destination: destination,
		Protocol:    "HTTPS",
		Action:      "blocked",
		Reason:      "domain not in allowlist",
		TraceID:     "trace-001",
	}
}

func TestRecord_All(t *testing.T) {
	vs := NewViolationStore()

	vs.Record(makeViolation("agent-1", "sess-1", "evil.com:443"))
	vs.Record(makeViolation("agent-2", "sess-2", "bad.com:443"))

	all := vs.All()
	if len(all) != 2 {
		t.Fatalf("expected 2 violations, got %d", len(all))
	}
}

func TestAll_ReturnsCopy(t *testing.T) {
	vs := NewViolationStore()
	vs.Record(makeViolation("agent-1", "sess-1", "evil.com:443"))

	snap := vs.All()
	// Mutating the snapshot must not affect the store.
	snap[0].AgentID = "mutated"

	all := vs.All()
	if all[0].AgentID == "mutated" {
		t.Fatal("All() must return a copy, not a reference to internal slice")
	}
}

func TestQuery_ByAgent(t *testing.T) {
	vs := NewViolationStore()
	vs.Record(makeViolation("agent-A", "sess-1", "evil.com:443"))
	vs.Record(makeViolation("agent-B", "sess-2", "bad.com:443"))
	vs.Record(makeViolation("agent-A", "sess-3", "also-evil.com:443"))

	results := vs.Query("agent-A", "")
	if len(results) != 2 {
		t.Fatalf("expected 2 results for agent-A, got %d", len(results))
	}
	for _, v := range results {
		if v.AgentID != "agent-A" {
			t.Errorf("unexpected agent_id %q in results", v.AgentID)
		}
	}
}

func TestQuery_BySession(t *testing.T) {
	vs := NewViolationStore()
	vs.Record(makeViolation("agent-A", "sess-X", "evil.com:443"))
	vs.Record(makeViolation("agent-B", "sess-X", "bad.com:443"))
	vs.Record(makeViolation("agent-A", "sess-Y", "other.com:443"))

	results := vs.Query("", "sess-X")
	if len(results) != 2 {
		t.Fatalf("expected 2 results for sess-X, got %d", len(results))
	}
}

func TestQuery_ByAgentAndSession(t *testing.T) {
	vs := NewViolationStore()
	vs.Record(makeViolation("agent-A", "sess-X", "evil.com:443"))
	vs.Record(makeViolation("agent-A", "sess-Y", "bad.com:443"))
	vs.Record(makeViolation("agent-B", "sess-X", "other.com:443"))

	results := vs.Query("agent-A", "sess-X")
	if len(results) != 1 {
		t.Fatalf("expected 1 result, got %d", len(results))
	}
}

func TestQuery_NoResults(t *testing.T) {
	vs := NewViolationStore()
	results := vs.Query("nobody", "")
	if results == nil {
		t.Fatal("Query must return a non-nil slice")
	}
	if len(results) != 0 {
		t.Fatalf("expected 0 results, got %d", len(results))
	}
}

func TestRecord_TimestampAutoSet(t *testing.T) {
	vs := NewViolationStore()
	v := Violation{
		AgentID:     "agent-1",
		Destination: "evil.com:443",
	}
	before := time.Now().UTC()
	vs.Record(v)
	after := time.Now().UTC()

	all := vs.All()
	if all[0].Timestamp.Before(before) || all[0].Timestamp.After(after) {
		t.Fatal("Record must auto-set Timestamp when zero")
	}
}

func TestConcurrentAccess(t *testing.T) {
	vs := NewViolationStore()
	var wg sync.WaitGroup

	for i := 0; i < 50; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			vs.Record(makeViolation("agent", "sess", "evil.com"))
		}(i)
	}
	for i := 0; i < 50; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			_ = vs.All()
		}()
	}
	wg.Wait()

	if len(vs.All()) != 50 {
		t.Fatalf("expected 50 violations after concurrent writes, got %d", len(vs.All()))
	}
}
