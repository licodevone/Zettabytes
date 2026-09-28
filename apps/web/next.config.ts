import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // O client da API é consumido como código-fonte TS direto do workspace.
  transpilePackages: ["@zettachat/api-client"],
};

export default nextConfig;
