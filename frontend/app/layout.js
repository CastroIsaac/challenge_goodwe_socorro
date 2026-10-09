import "./globals.css";
import Navegacao from "@/components/Navegacao";

export const metadata = {
  title: "EV ChargeOps",
  description: "Gestão de recarga compartilhada de veículos elétricos",
};

export default function RootLayout({ children }) {
  return (
    <html lang="pt-BR">
      <body>
        <header className="topo">
          <div className="marca">
            <span className="marca-icone">⚡</span> EV ChargeOps
          </div>
          <Navegacao />
        </header>
        <main className="conteudo">{children}</main>
      </body>
    </html>
  );
}
