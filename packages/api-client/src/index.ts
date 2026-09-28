import createClient, { type Middleware } from "openapi-fetch";

import type { components, paths } from "./schema";

export type { components, paths };
export type Schemas = components["schemas"];

export interface ApiClientOptions {
  baseUrl: string;
  /** Retorna o access token atual (ou null se deslogado). */
  getAccessToken?: () => string | null | Promise<string | null>;
  /** Retorna o tenant ativo — enviado como header `X-Company-ID`. */
  getCompanyId?: () => string | null | Promise<string | null>;
  /** Chamado em 401 (ex.: tentar refresh ou redirecionar para /login). */
  onUnauthorized?: () => void | Promise<void>;
}

export function createApiClient(options: ApiClientOptions) {
  const client = createClient<paths>({ baseUrl: options.baseUrl });

  const auth: Middleware = {
    async onRequest({ request }) {
      const token = await options.getAccessToken?.();
      if (token) request.headers.set("Authorization", `Bearer ${token}`);
      const companyId = await options.getCompanyId?.();
      if (companyId && !request.headers.has("X-Company-ID")) {
        request.headers.set("X-Company-ID", companyId);
      }
      return request;
    },
    async onResponse({ response }) {
      if (response.status === 401) await options.onUnauthorized?.();
      return response;
    },
  };

  client.use(auth);
  return client;
}

export type ApiClient = ReturnType<typeof createApiClient>;
