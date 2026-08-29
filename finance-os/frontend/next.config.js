/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  images: { unoptimized: true },
  async rewrites() {
    if (process.env.NODE_ENV === 'development') {
      return [
        { source: '/api/finance/:path*', destination: 'http://127.0.0.1:8000/api/finance/:path*' },
      ];
    }
    return [];
  },
};

module.exports = nextConfig;
