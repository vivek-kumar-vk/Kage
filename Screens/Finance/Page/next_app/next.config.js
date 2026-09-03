/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  images: { unoptimized: true },
  async rewrites() {
    if (process.env.NODE_ENV === 'development') {
      const origin = process.env.FINANCE_API_ORIGIN || 'http://127.0.0.1:8000';
      return [
        { source: '/api/finance/:path*', destination: `${origin}/api/finance/:path*` },
      ];
    }
    return [];
  },
};

module.exports = nextConfig;
