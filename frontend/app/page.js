"use client";

import { useCallback, useEffect, useState } from "react";
import { FilaRevisao, GraficoUsoPorHora, Kpi, MapaDemanda, TabelaRateio } from "@/components/Componentes";
import { api, brl, kwh, mesAtual, ultimosMeses } from "@/lib/api";

const ROTULO_POSTO = { fora_ponta: "Fora de ponta", intermediario: "Intermediário", ponta: "Ponta" };

export default function PainelGestor() {
  const [mes, setMes] = useState(mesAtual());
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(null);
  const [mensagem, setMensagem] = useState(null);

  const carregar = useCallback(async () => {
    try {
      const [painel, rateio, revisao, previsao, usuarios] = await Promise.all([
        api(`/painel?mes=${mes}`),
        api(`/rateio/${mes}`),
        api(`/sessoes?mes=${mes}&status=em_revisao`),
        api("/ia/previsao-demanda"),
        api("/usuarios"),
      ]);
      setDados({ painel, rateio, revisao, previsao, usuarios: Object.fromEntries(usuarios.map((u) => [u.id, u])) });
      setErro(null);
    } catch (e) {
      setErro(`Não foi possível falar com a API (${e.message}). O backend está rodando na porta 8000?`);
    }
  }, [mes]);

  useEffect(() => { carregar(); }, [carregar]);

  async function fecharMes() {
    const r = await api(`/rateio/${mes}/fechar`, { method: "POST" });
    setMensagem(`Mês ${mes} fechado: ${r.faturas_geradas} faturas gravadas, total ${brl(r.total)}.`);
  }

  if (erro) return <div className="erro">{erro}</div>;
  if (!dados) return <p className="suave">Carregando…</p>;
  const { painel, rateio, revisao, previsao, usuarios } = dados;
  const ind = painel.indicadores;
  const totalPostos = Object.values(painel.energia_por_posto).reduce((a, b) => a + b, 0) || 1;

  return (
    <>
      <div className="cabecalho">
        <div>
          <h1>Painel do gestor</h1>
          <p className="subtitulo">Condomínio piloto · 2 carregadores GoodWe HCA G2</p>
        </div>
        <label>
          Mês de referência
          <select value={mes} onChange={(e) => setMes(e.target.value)}>
            {ultimosMeses().map((m) => <option key={m}>{m}</option>)}
          </select>
        </label>
      </div>

      {mensagem && <div className="sucesso">{mensagem}</div>}

      <div className="grade grade-kpi">
        <Kpi rotulo="Energia faturável" valor={kwh(ind.energia_kwh)} detalhe={`${ind.sessoes} sessões`} />
        <Kpi rotulo="Total do rateio" valor={brl(ind.total_arrecadado)} detalhe={`${ind.usuarios_ativos} moradores ativos`} />
        <Kpi rotulo="Tempo ocioso conectado" valor={`${Math.round(ind.fracao_ociosa * 100)}%`}
             detalhe={`${ind.horas_carregando} h carregando de ${ind.horas_conectado} h conectado`} />
        <Kpi rotulo="Barradas pela IA" valor={ind.sessoes_em_revisao}
             detalhe={`aguardando revisão · ${ind.sessoes_rejeitadas} rejeitadas`} />
      </div>

      <div className="grade grade-2">
        <div className="cartao">
          <h2>Sessões por horário de início</h2>
          <GraficoUsoPorHora dados={painel.uso_por_hora} />
        </div>
        <div className="cartao">
          <h2>Energia por posto tarifário</h2>
          {Object.entries(ROTULO_POSTO).map(([posto, rotulo]) => {
            const valor = painel.energia_por_posto[posto] || 0;
            return (
              <div key={posto} style={{ marginBottom: 12 }}>
                <div className="linha-detalhe" style={{ border: "none", fontWeight: 400 }}>
                  <span>{rotulo}</span><span>{kwh(valor)} · {Math.round((valor / totalPostos) * 100)}%</span>
                </div>
                <div style={{ height: 8, background: "var(--fundo)", borderRadius: 4 }}>
                  <div style={{ width: `${(valor / totalPostos) * 100}%`, height: 8, borderRadius: 4,
                                background: posto === "ponta" ? "var(--alta)" : posto === "intermediario" ? "var(--moderada)" : "var(--primaria)" }} />
                </div>
              </div>
            );
          })}
          <p className="suave" style={{ fontSize: 13 }}>
            Cada minuto de recarga é cobrado pela tarifa do seu posto (Tarifa Branca).
          </p>
        </div>
      </div>

      <div className="cartao" style={{ marginBottom: 16 }}>
        <h2>Previsão de demanda para os próximos 7 dias (IA)</h2>
        <p className="suave" style={{ marginTop: -6 }}>
          A ocupação prevista define quanto custa deixar o carro conectado depois de carregar em cada horário.
        </p>
        <MapaDemanda previsao={previsao.previsao} />
      </div>

      <div className="cartao" style={{ marginBottom: 16 }}>
        <h2>Fila de revisão: sessões barradas pela IA</h2>
        <p className="suave" style={{ marginTop: -6 }}>Só entram no rateio depois de aprovadas pelo gestor.</p>
        <FilaRevisao sessoes={revisao} usuarios={usuarios} aoRevisar={carregar} />
      </div>

      <div className="cartao">
        <div className="cabecalho">
          <h2>Rateio do mês</h2>
          <button className="secundario" onClick={fecharMes}>Fechar mês</button>
        </div>
        <TabelaRateio rateio={rateio} />
      </div>
    </>
  );
}
