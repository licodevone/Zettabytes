import { createApiClient } from "@zettabytes/api-client";

const api = createApiClient({
  baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8100",
});

export const dynamic = "force-dynamic";

async function getApiStatus() {
  try {
    const { data } = await api.GET("/api/v1/health");
    return data ? `API ${data.status} · banco ${data.database} · v${data.version}` : "API indisponível";
  } catch {
    return "API indisponível";
  }
}

export default async function Home() {
  const status = await getApiStatus();
  return (
    <main style={{ minHeight: "100dvh", display: "grid", placeItems: "center", padding: 24 }}>
      <div style={{ textAlign: "center" }}>
        <h1 style={{ fontSize: 28, fontWeight: 600, letterSpacing: "-0.02em", margin: 0 }}>Zettabytes</h1>
        <p style={{ color: "#a1a1a1", marginTop: 8 }}>{status}</p>
      </div>
    </main>
  );
}
