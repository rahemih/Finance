/**
 * WEB-P0 market previews: fail-closed method boundary.
 * These routes expose non-operational read-only mock pages only.
 * This is NOT an authentication or trading authorization mechanism.
 */
import { NextResponse, type NextRequest } from "next/server";

export const config = {
  matcher: ["/markets/:path*"],
};

export function proxy(request: NextRequest) {
  if (request.method !== "GET" && request.method !== "HEAD") {
    return new Response(null, {
      status: 405,
      headers: {
        Allow: "GET, HEAD",
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
      },
    });
  }
  return NextResponse.next();
}
