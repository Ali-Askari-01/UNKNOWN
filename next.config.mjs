/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  // Prevent Next.js from bundling server-only packages used in server.ts
  serverExternalPackages: ['bcryptjs', 'socket.io'],
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${process.env.FASTAPI_INTERNAL_URL || 'http://127.0.0.1:8000'}/api/v1/:path*`,
      },
    ]
  },
}

export default nextConfig
