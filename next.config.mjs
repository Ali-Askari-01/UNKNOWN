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
}

export default nextConfig
