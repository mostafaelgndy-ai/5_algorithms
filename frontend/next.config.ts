import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  // Monorepo: the root package.json (with its lockfile) lives one level up.
  turbopack: {
    root: path.join(__dirname, ".."),
  },
};

export default nextConfig;
