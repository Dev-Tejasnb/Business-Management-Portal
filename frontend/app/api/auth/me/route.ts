import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL ?? "http://backend:8000/api/v1";

async function proxy(req: NextRequest, path: string): Promise<NextResponse> {
  const url = `${BACKEND_URL}/auth${path}`;
  const headers = new Headers();

  const auth = req.headers.get("authorization");
  if (auth) headers.set("Authorization", auth);

  const res = await fetch(url, {
    method: req.method,
    headers,
    credentials: "include",
  });

  const response = NextResponse.json(await res.json(), { status: res.status });
  const setCookie = res.headers.getSetCookie();
  for (const cookie of setCookie) {
    response.headers.append("Set-Cookie", cookie);
  }
  return response;
}

export async function GET(req: NextRequest) {
  return proxy(req, "/me");
}
