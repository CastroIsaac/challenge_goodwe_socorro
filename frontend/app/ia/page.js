"use client";

import { useCallback, useEffect, useState } from "react";
import { Kpi } from "@/components/Componentes";
import { api, dataHora } from "@/lib/api";

export default function ModelosIA() {
  const [status, setStatus] = useState(null);
  const [perfis, setPerfis] = useState(null);
  const [treinando, setTreinando] = useState(false);
  const [erro, setErro] = useState(null);

  const carregar = useCallback(() => {
    Promise.all([api("/ia/status"), api("/ia/perfis")])
      .then(([s, p]) => { setStatus(s); setPerfis(p); })
      .catch((e) => setErro(e.message));
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  async function retreinar() {
    setTreinando(true);
    await api("/ia/treinar", { method: "POST" });
    setTreinando(false);
    carregar();
  }

  if (erro) return <div className="erro">Erro ao falar com a API: {erro}</div>;
  if (!status) return <p className="suave">Carregando…</p>;
  const metricas = status.demanda.metricas;

  return (
    <>
      <div className="cabecalho">
        <div>
          <h1>Modelos de IA</h1>
          <p className="subtitulo">Último treino: {status.treinado_em ? dataHora(status.treinado_em) : "nunca"}</p>
        </div>
        <button onClick={retreinar} disabled={treinando}>{treinando ? "Treinando…" : "Retreinar com o histórico"}</button>
      </div>

      <div className="grade grade-kpi">
        <Kpi rotulo="Anomalias · amostras de treino" valor={status.anomalias.amostras_treino}
             detalhe={status.anomalias.algoritmo} />
        <Kpi rotulo="Demanda · erro médio (MAE)" valor={metricas.mae_modelo ?? "—"}
             detalhe={`média simples: ${metricas.mae_baseline_media ?? "—"} · ${metricas.dias_historico ?? 0} dias`} />
        <Kpi rotulo="Perfis · silhueta" valor={status.perfis.silhueta ?? "—"} detalhe={`${status.perfis.grupos} grupos · K-Means`} />
        <Kpi rotulo="Assistente" valor="Ativo" detalhe={status.assistente.algoritmo} />
      </div>

      <div className="cartao" style={{ marginBottom: 16 }}>
        <h2>Onde cada modelo atua no fluxo</h2>
        <div className="tabela-container">
          <table>
            <thead><tr><th>Modelo</th><th>Entrada</th><th>Saída</th><th>Efeito no sistema</th></tr></thead>
            <tbody>
              <tr><td>Detector de anomalias</td><td>Cada sessão nova</td><td>Score + motivos</td>
                <td style={{ whiteSpace: "normal" }}>Sessão anômala vai para revisão e não é cobrada até o gestor decidir</td></tr>
              <tr><td>Previsão de demanda</td><td>Histórico de ocupação</td><td>Ocupação prevista por hora</td>
                <td style={{ whiteSpace: "normal" }}>Define o fator da taxa de ocupação (0×, 1× ou 2×) de cada minuto ocioso</td></tr>
              <tr><td>Perfis (K-Means)</td><td>Hábitos de cada morador</td><td>Grupo + recomendação</td>
                <td style={{ whiteSpace: "normal" }}>Dicas personalizadas na área do morador e no assistente</td></tr>
              <tr><td>Assistente</td><td>Pergunta em texto livre</td><td>Intenção</td>
                <td style={{ whiteSpace: "normal" }}>Responde com dados reais do rateio, sessões e previsões</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="cartao">
        <h2>Perfis de uso descobertos</h2>
        <div className="tabela-container">
          <table>
            <thead>
              <tr><th>Perfil</th><th>Moradores</th><th className="num">Início médio</th><th className="num">kWh/sessão</th>
                <th className="num">Sessões/sem.</th><th className="num">Ocioso (h)</th><th className="num">Fim de semana</th></tr>
            </thead>
            <tbody>
              {perfis.grupos.map((g) => (
                <tr key={g.grupo}>
                  <td><strong>{g.nome}</strong></td>
                  <td style={{ whiteSpace: "normal" }}>{g.usuarios.map((u) => u.nome).join(", ")}</td>
                  <td className="num">{Math.round(g.centroide.hora_media)}h</td>
                  <td className="num">{g.centroide.energia_media_kwh}</td>
                  <td className="num">{g.centroide.sessoes_por_semana}</td>
                  <td className="num">{g.centroide.ociosidade_media_h}</td>
                  <td className="num">{Math.round(g.centroide.fracao_fim_de_semana * 100)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
