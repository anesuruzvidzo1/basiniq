import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.BASINIQ_API_URL;
const API_KEY = process.env.BASINIQ_API_KEY;

export async function POST(req: NextRequest) {
  if (!API_URL) {
    return NextResponse.json({ error: "API not configured" }, { status: 503 });
  }

  const body = await req.json();

  const upstream = await fetch(`${API_URL}/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
    },
    body: JSON.stringify(body),
  });

  const data = await upstream.json();
  return NextResponse.json(data, { status: upstream.status });
}
