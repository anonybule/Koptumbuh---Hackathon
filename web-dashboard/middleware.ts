import { NextRequest, NextResponse } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('koptumbuh_token')?.value;
  const { pathname } = request.nextUrl;

  if (pathname.startsWith('/login')) {
    if (token && _isValidJwtStructure(token)) {
      return NextResponse.redirect(new URL('/', request.url));
    }
    return NextResponse.next();
  }

  if (!token || !_isValidJwtStructure(token)) {
    const response = NextResponse.redirect(new URL('/login', request.url));
    response.cookies.delete('koptumbuh_token');
    return response;
  }

  return NextResponse.next();
}

function _isValidJwtStructure(token: string): boolean {
  const parts = token.split('.');
  return parts.length === 3 && parts.every((p) => p.length > 0);
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
