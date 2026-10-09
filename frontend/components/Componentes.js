"use client";

import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, brl, dataHora, kwh, ROTULO_STATUS } from "@/lib/api";

export function Kpi({ rotulo, valor, detalhe }) {
  return (
    <div className="cartao">
      <div className="kpi-rotulo">{rotulo}</div>
      <div className="kpi-valor">{valor}</div>
      {detalhe && <div className="kpi-detalhe">{detalhe}</div>}
    </div>
  );
}

export function Selo({ status }) {
  return <span className={`selo selo-${status}`}>{ROTULO_STATUS[status] || status}</span>;
}

export function GraficoUsoPorHora({ dados }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={dados} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid stroke="#eef1ef" vertical={false} />
        <XAxis dataKey="hora" tickFormatter={(h) => `${h}h`} fontSize={11} interval={1} />
        <YAxis fontSize={11} allowDecimals={false} />
        <Tooltip formatter={(v, nome) => [nome === "sessoes" ? v : kwh(v), nome === "sessoes" ? "Sessões" : "Energia"]}
                 labelFormatter={(h) => `Início às ${h}h`} />
        <Bar dataKey="sessoes" fill="#0f7b5a" radius={[3, 3, 0, 0]} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  );
}

const CORES_NIVEL = { baixa: "var(--baixa)", moderada: "var(--moderada)", alta: "var(--alta)" };
const DIAS = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];

/** Mapa de calor da ocupação prevista: uma linha por dia, uma coluna por hora. */
export function MapaDemanda({ previsao }) {
  // Agrupa as horas previstas por dia; cada célula fica na coluna da sua hora
  const porDia = new Map();
  for (const h of previsao) {
    const momento = new Date(h.momento);
    const chave = momento.toDateString();
    if (!porDia.has(chave)) porDia.set(chave, { data: momento, horas: Array(24).fill(null) });
    porDia.get(chave).horas[momento.getHours()] = h;
  }
  return (
    <>
      <div className="heatmap">
        <div />
        {Array.from({ length: 24 }, (_, h) => (
          <div key={h} className="rotulo-coluna">{h % 3 === 0 ? `${h}h` : ""}</div>
        ))}
        {[...porDia.values()].map(({ data, horas }) => [
          <div key={`r${data}`} className="rotulo-linha">{DIAS[data.getDay()]} {data.getDate()}</div>,
          ...horas.map((h, i) => (
            <div
              key={`${data}-${i}`}
              className="celula"
              title={h ? `${dataHora(h.momento)}: ${Math.round((h.ocupacao_prevista ?? 0) * 100)}% (${h.nivel})` : ""}
              style={{ background: h ? CORES_NIVEL[h.nivel] : "transparent" }}
            />
          )),
        ])}
      </div>
      <div className="legenda">
        <span style={{ "--cor": CORES_NIVEL.baixa }}>Baixa: ociosidade não é cobrada</span>
        <span style={{ "--cor": CORES_NIVEL.moderada }}>Moderada: taxa base</span>
        <span style={{ "--cor": CORES_NIVEL.alta }}>Alta: taxa dobrada</span>
      </div>
    </>
  );
}

export function TabelaRateio({ rateio }) {
  if (!rateio.itens.length) return <p className="suave">Nenhuma sessão faturável neste mês.</p>;
  const soma = (campo) => rateio.itens.reduce((t, i) => t + i[campo], 0);
  return (
    <div className="tabela-container">
      <table>
        <thead>
          <tr>
            <th>Apto</th><th>Morador</th><th className="num">Sessões</th><th className="num">Energia</th>
            <th className="num">R$ energia</th><th className="num">R$ ocupação</th>
            <th className="num">R$ manutenção</th><th className="num">Total</th>
          </tr>
        </thead>
        <tbody>
          {rateio.itens.map((i) => (
            <tr key={i.usuario_id}>
              <td>{i.apartamento}</td>
              <td>{i.nome}{i.sessoes_em_revisao > 0 && <span className="selo selo-em_revisao" style={{ marginLeft: 6 }}>{i.sessoes_em_revisao} em revisão</span>}</td>
              <td className="num">{i.sessoes}</td>
              <td className="num">{kwh(i.energia_kwh)}</td>
              <td className="num">{brl(i.valor_energia)}</td>
              <td className="num">{brl(i.valor_ocupacao)}</td>
              <td className="num">{brl(i.valor_manutencao)}</td>
              <td className="num"><strong>{brl(i.valor_total)}</strong></td>
            </tr>
          ))}
          <tr className="total">
            <td colSpan={2}>Total</td>
            <td className="num">{soma("sessoes")}</td>
            <td className="num">{kwh(soma("energia_kwh"))}</td>
            <td className="num">{brl(soma("valor_energia"))}</td>
            <td className="num">{brl(soma("valor_ocupacao"))}</td>
            <td className="num">{brl(soma("valor_manutencao"))}</td>
            <td className="num">{brl(rateio.total_arrecadado)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

export function FilaRevisao({ sessoes, usuarios, aoRevisar }) {
  const [enviando, setEnviando] = useState(null);
  if (!sessoes.length) return <p className="suave">Nenhuma sessão aguardando revisão.</p>;

  async function decidir(sessao, decisao) {
    setEnviando(sessao.id);
    try {
      await api(`/sessoes/${sessao.id}/revisao`, { method: "POST", body: { decisao } });
      aoRevisar();
    } finally {
      setEnviando(null);
    }
  }

  return sessoes.map((s) => {
    const usuario = usuarios[s.usuario_id];
    return (
      <div key={s.id} className="revisao-item">
        <strong>{usuario ? `${usuario.nome} (ap. ${usuario.apartamento})` : s.usuario_id}</strong>
        <span className="suave"> · {dataHora(s.inicio)} · {kwh(s.energia_kwh)} · {brl(s.custo)}</span>
        <div className="revisao-motivo">{s.motivo_revisao}</div>
        <div className="acoes">
          <button className="secundario" disabled={enviando === s.id} onClick={() => decidir(s, "aprovar")}>
            Aprovar e cobrar
          </button>
          <button className="perigo" disabled={enviando === s.id} onClick={() => decidir(s, "rejeitar")}>
            Rejeitar
          </button>
        </div>
      </div>
    );
  });
}

const SUGESTOES = [
  "Quanto devo pagar este mês?",
  "Qual foi meu consumo?",
  "Qual o melhor horário para carregar?",
  "Qual é meu perfil?",
  "Tenho sessão em revisão?",
];

export function Assistente({ usuarioId }) {
  const [mensagens, setMensagens] = useState([]);
  const [texto, setTexto] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function perguntar(pergunta) {
    if (!pergunta.trim()) return;
    setMensagens((m) => [...m, { autor: "usuario", texto: pergunta }]);
    setTexto("");
    setCarregando(true);
    try {
      const r = await api("/assistente", { method: "POST", body: { usuario_id: usuarioId, pergunta } });
      setMensagens((m) => [...m, { autor: "assistente", texto: r.resposta, meta: `${r.intencao} · confiança ${Math.round(r.confianca * 100)}%` }]);
    } catch (e) {
      setMensagens((m) => [...m, { autor: "assistente", texto: `Erro: ${e.message}` }]);
    } finally {
      setCarregando(false);
    }
  }

  return (
    <>
      <div className="sugestoes">
        {SUGESTOES.map((s) => <button key={s} className="secundario" onClick={() => perguntar(s)}>{s}</button>)}
      </div>
      <div className="chat">
        {mensagens.map((m, i) => (
          <div key={i} className={`msg msg-${m.autor}`}>
            {m.texto}
            {m.meta && <div className="msg-meta">{m.meta}</div>}
          </div>
        ))}
        {carregando && <div className="msg msg-assistente suave">…</div>}
      </div>
      <form className="acoes" onSubmit={(e) => { e.preventDefault(); perguntar(texto); }}>
        <input style={{ flex: 1 }} value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Pergunte algo sobre suas recargas" />
        <button type="submit" disabled={carregando}>Enviar</button>
      </form>
    </>
  );
}
