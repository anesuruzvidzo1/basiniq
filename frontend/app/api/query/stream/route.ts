import { NextRequest } from "next/server";

const API_URL = process.env.BASINIQ_API_URL;
const API_KEY = process.env.BASINIQ_API_KEY;

export async function POST(req: NextRequest) {
  if (!API_URL) {
    return new Response(
      `data: ${JSON.stringify({ type: "error", message: "API not configured" })}\n\n`,
      { status: 503, headers: { "Content-Type": "text/event-stream" } }
    );
  }

  const body = await req.json();

  const upstream = await fetch(`${API_URL}/query/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
    },
    body: JSON.stringify(body),
  });

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
