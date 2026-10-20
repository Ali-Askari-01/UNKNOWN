/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    unoptimized: true,
  },
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
