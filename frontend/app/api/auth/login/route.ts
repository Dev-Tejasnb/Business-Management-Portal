import { NextRequest, NextResponse } from "next/server";

/**
 * Auth proxy routes — forward requests to the backend and proxy responses back.
 *
 * Why proxy through Next.js?
 * - The refresh token is an HTTP-only cookie. Browsers only send cookies to
 *   the same origin. By proxying through Next.js, the browser talks to the
 *   Next.js origin, and Next.js forwards to the backend. This way the
 *   Set-Cookie header from the backend becomes a Set-Cookie for the frontend
 *   origin, and the cookie is automatically sent on subsequent proxy requests.
 */

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL ?? "http://backend:8000/api/v1";

async function proxy(req: NextRequest, path: string): Promise<NextResponse> {
  const url = `${BACKEND_URL}/auth${path}`;
  const headers = new Headers();

  // Forward Authorization header if present.
  const auth = req.headers.get("authorization");
  if (auth) headers.set("Authorization", auth);

  // Forward request body for POST/PUT.
  let body: string | undefined;
  if (req.method !== "GET" && req.method !== "HEAD") {
    body = await req.text();
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(url, {
    method: req.method,
    headers,
    body,
    credentials: "include",
  });

  // Build response, forwarding Set-Cookie headers.
  const response = NextResponse.json(await res.json(), { status: res.status });
  const setCookie = res.headers.getSetCookie();
  for (const cookie of setCookie) {
    response.headers.append("Set-Cookie", cookie);
  }
  return response;
}

export async function POST(req: NextRequest) {
  return proxy(req, "/login");
}
