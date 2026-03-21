const CP = process.env.CONTROL_PLANE_URL ?? "http://localhost:8080";

export async function POST(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const { messages, sessionToken } = await req.json();

  const res = await fetch(`${CP}/sessions/${id}/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${sessionToken}`,
    },
    body: JSON.stringify(messages),
  });

  return new Response(null, { status: res.ok ? 204 : res.status });
}
