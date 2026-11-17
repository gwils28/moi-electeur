import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Le moteur est livré en sources TS, compilé dans le bundle client (SPEC § 15.5).
  transpilePackages: ["@moi-electeur/engine"],
  poweredByHeader: false,
};

export default nextConfig;
