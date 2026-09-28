import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Zettabytes",
  description: "Automação de WhatsApp com fluxos e agentes de IA.",
};

// Shell provisório: o design system (Tailwind + shadcn/ui + dark mode) chega no Prompt 4.
export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR">
      <body style={{ margin: 0, fontFamily: "system-ui, sans-serif", background: "#0a0a0a", color: "#ededed" }}>
        {children}
      </body>
    </html>
  );
}
