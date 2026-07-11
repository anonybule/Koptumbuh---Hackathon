import { NextRequest, NextResponse } from 'next/server';

const DEMO_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDEiLCJyb2xlIjoiQURNSU4iLCJrb3BlcmFzaV9yZWYiOiJLT1AtSmFzYUFJLUExQjJDM0Q0RTVGNiIsImV4cCI6MTgxNTI4MDk1NX0.D2hScT89-l1tGCTmICml9pzc7WLdntnumI80O8sK0qE';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const response = NextResponse.next();

  // Always inject demo token so API calls work
  response.cookies.set('koptumbuh_token', DEMO_TOKEN, { path: '/', maxAge: 86400, sameSite: 'lax' });

  // Redirect /login straight to dashboard
  if (pathname.startsWith('/login')) {
    return NextResponse.redirect(new URL('/', request.url));
  }

  return response;
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
