import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  experimental: {
    // Turbopack's on-disk cache (on by default since 16.1 dev / 16.3 build)
    // served stale Tailwind CSS here: classes added to components were never
    // generated until `.next` was deleted, so new styles silently didn't
    // apply. Off for both — dev restarts are a little slower, CSS is correct.
    turbopackFileSystemCacheForDev: false,
    turbopackFileSystemCacheForBuild: false,
  },
}

export default nextConfig
