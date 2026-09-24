import { NextResponse } from "next/server";

const INTERNAL_URL = process.env.BACKEND_INTERNAL_URL ?? "http://backend:8000/api/v1";

/**
 * Server-side proxy to the backend readiness endpoint.
 * The browser never talks directly to the backend, keeping the API URL internal.
 */
export async function GET() {
  try {
    const res = await fetch(`${INTERNAL_URL}/health`, { cache: "no-store" });
    const body = await res.json();
    return NextResponse.json(body, { status: res.status });
  } catch {
    return NextResponse.json(
      { status: "down", message: "Backend unreachable" },
      { status: 503 }
    );
  }
}