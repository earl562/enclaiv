const CP = process.env.CONTROL_PLANE_URL ?? "http://localhost:8080";

export async function POST(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  await params; // consume — not needed for this route but required by Next.js
  const { messages, model, sessionToken } = await req.json();

  const res = await fetch(`${CP}/llm/complete`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${sessionToken}`,
    },
    body: JSON.stringify({ messages, model, stream: true }),
  });

  if (!res.ok) {
    const text = await res.text();
    return new Response(text, { status: res.status });
  }

  return new Response(res.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
