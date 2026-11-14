export default function Home() {
  return (
    <main style={{ minHeight: "100dvh", display: "grid", placeItems: "center", padding: 24, background: "radial-gradient(ellipse at top right, #18386a, #09152e 65%)" }}>
      <section style={{ maxWidth: 680, padding: 36, border: "1px solid #ffffff20", borderRadius: 24, background: "#ffffff08" }}>
        <p style={{ color: "#f8c927", fontWeight: 700, letterSpacing: 3 }}>ACMEbr · ATENDIMENTOS</p>
        <h1 style={{ fontSize: "clamp(30px, 5vw, 48px)", lineHeight: 1.15 }}>A conversa começa com a Acme.</h1>
        <p style={{ lineHeight: 1.8, color: "#cbd5e1" }}>Conheça nossas soluções e converse com a assistente pelo site da ACMEbr. A equipe acompanha as mensagens e os contatos em uma área protegida.</p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 28 }}>
          <a href="https://acmebr.net" style={{ padding: "14px 20px", borderRadius: 10, background: "#f8c927", color: "#09152e", textDecoration: "none", fontWeight: 700 }}>Conversar com a Acme</a>
          <a href="https://acmebr.net/painel/atendimentos" style={{ padding: "14px 20px", borderRadius: 10, border: "1px solid #ffffff40", color: "white", textDecoration: "none" }}>Área da equipe</a>
        </div>
        <p style={{ fontSize: 13, color: "#94a3b8", marginTop: 28 }}>Sistemas · Aplicativos · Automação</p>
      </section>
    </main>
  );
}
