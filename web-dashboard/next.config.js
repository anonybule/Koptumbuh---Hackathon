/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    // Docker Compose sets API_INTERNAL_URL=http://api:8000
    // Local `npm run dev` defaults to host-mapped API on :8100
    const api = process.env.API_INTERNAL_URL || 'http://localhost:8100';
    return [
      {
        source: '/api/v1/:path*',
        destination: `${api}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
