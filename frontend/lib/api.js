export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function api(caminho, opcoes = {}) {
  const resposta = await fetch(`${API_URL}${caminho}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...opcoes,
    body: opcoes.body ? JSON.stringify(opcoes.body) : undefined,
  });
  const dados = await resposta.json();
  if (!resposta.ok) throw new Error(dados.detail?.toString() || "Erro na API");
  return dados;
}

const formatoBRL = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
export const brl = (valor) => formatoBRL.format(valor ?? 0);
export const kwh = (valor) => `${(valor ?? 0).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} kWh`;
export const dataHora = (iso) =>
  new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
export const mesAtual = () => new Date().toISOString().slice(0, 7);

export function ultimosMeses(quantidade = 5) {
  const hoje = new Date();
  return Array.from({ length: quantidade }, (_, i) => {
    const d = new Date(hoje.getFullYear(), hoje.getMonth() - i, 1);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  });
}

export const ROTULO_STATUS = {
  faturavel: "Faturável",
  em_revisao: "Em revisão",
  rejeitada: "Rejeitada",
};
