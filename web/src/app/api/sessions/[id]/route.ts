const CP = process.env.CONTROL_PLANE_URL ?? "http://localhost:8080";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const token = req.headers.get("Authorization") ?? "";
  const res = await fetch(`${CP}/sessions/${id}`, {
    headers: { Authorization: token },
    cache: "no-store",
  });
  const data = await res.json();
  return Response.json(data, { status: res.status });
}
