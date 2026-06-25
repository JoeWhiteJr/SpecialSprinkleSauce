/**
 * Server-side proxy for all /api/* requests.
 *
 * The client calls /api/<path> (same-origin, no credentials in JS bundle).
 * This route reads API_KEY and API_URL as server-side env vars and forwards
 * the request to the FastAPI backend, passing the response body through as a
 * stream so SSE / chunked-transfer endpoints work transparently.
 *
 * Security properties:
 *   - API_KEY never touches the browser (not NEXT_PUBLIC_*)
 *   - Backend URL is server-side only; clients cannot enumerate it from the bundle
 *   - Streaming responses (SSE) are proxied without buffering
 */

import { NextRequest, NextResponse } from "next/server"

const BACKEND_URL = process.env.API_URL ?? "http://localhost:8000"
const API_KEY = process.env.API_KEY ?? ""

async function proxy(
  req: NextRequest,
  path: string[]
): Promise<NextResponse> {
  const target = new URL(`${BACKEND_URL}/api/${path.join("/")}`)

  // Forward query string intact
  req.nextUrl.searchParams.forEach((value, key) => {
    target.searchParams.set(key, value)
  })

  const headers: Record<string, string> = {
    "Content-Type": req.headers.get("content-type") ?? "application/json",
  }
  if (API_KEY) {
    headers["X-API-Key"] = API_KEY
  }

  const body =
    req.method !== "GET" && req.method !== "HEAD"
      ? await req.text()
      : undefined

  let upstream: Response
  try {
    upstream = await fetch(target.toString(), {
      method: req.method,
      headers,
      body,
    })
  } catch (err) {
    return NextResponse.json(
      { detail: "Backend unreachable", error: String(err) },
      { status: 502 }
    )
  }

  // Pass the response body through as a stream — works for both regular JSON
  // and SSE / chunked-transfer responses without buffering.
  const responseHeaders: Record<string, string> = {
    "Content-Type":
      upstream.headers.get("content-type") ?? "application/json",
  }
  const cacheControl = upstream.headers.get("cache-control")
  if (cacheControl) responseHeaders["Cache-Control"] = cacheControl

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  })
}

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxy(req, (await params).path)
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxy(req, (await params).path)
}

export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxy(req, (await params).path)
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxy(req, (await params).path)
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxy(req, (await params).path)
}
