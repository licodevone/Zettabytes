import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Imagem Docker (apps/web/Dockerfile): `standalone` copia para .next/standalone
  // só o que a app importa. O rastreio parte da raiz do monorepo, onde ficam o
  // lockfile e o node_modules/.pnpm.
  output: "standalone",
  outputFileTracingRoot: path.join(__dirname, "../.."),
  // O client da API é consumido como código-fonte TS direto do workspace.
  transpilePackages: ["@zettabytes/api-client"],
};

export default nextConfig;
