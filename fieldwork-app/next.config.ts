import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone", // small server bundle for the Cloud Run image (see Dockerfile)
};

export default nextConfig;
