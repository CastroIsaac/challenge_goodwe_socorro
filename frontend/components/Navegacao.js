"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", rotulo: "Painel do gestor" },
  { href: "/usuario", rotulo: "Área do morador" },
  { href: "/sessoes", rotulo: "Sessões" },
  { href: "/ia", rotulo: "Modelos de IA" },
];

export default function Navegacao() {
  const atual = usePathname();
  return (
    <nav className="nav">
      {LINKS.map((link) => (
        <Link key={link.href} href={link.href} className={atual === link.href ? "ativo" : ""}>
          {link.rotulo}
        </Link>
      ))}
    </nav>
  );
}
