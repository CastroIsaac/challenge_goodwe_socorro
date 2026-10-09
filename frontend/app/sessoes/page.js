"use client";

import { useCallback, useEffect, useState } from "react";
import { Selo } from "@/components/Componentes";
import { api, brl, dataHora, kwh, mesAtual } from "@/lib/api";

function paraInput(data) {
  const d = new Date(data.getTime() - data.getTimezoneOffset() * 60000);
  return d.toISOString().slice(0, 16);
}

function leituraPadrao() {
  const agora = new Date();
  const h = (horas) => new Date(agora.getTime() - horas * 3600000);
  return { inicio: paraInput(h(5)), fim_recarga: paraInput(h(2)), fim: paraInput(h(1)), energia_kwh: 19.5 };
}

export default function Sessoes() {
  const [usuarios, setUsuarios] = useState([]);
  const [carregadores, setCarregadores] = useState([]);
  const [sessoes, setSessoes] = useState([]);
  const [form, setForm] = useState({ rfid_tag: "", numero_serie_carregador: "", ...leituraPadrao() });
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState(null);
  const [sincronizacao, setSincronizacao] = useState(null);

  const carregarSessoes = useCallback(() => api(`/sessoes?mes=${mesAtual()}`).then(setSessoes), []);

  useEffect(() => {
    Promise.all([api("/usuarios"), api("/carregadores")]).then(([u, c]) => {
      setUsuarios(u);
      setCarregadores(c);
      setForm((f) => ({ ...f, rfid_tag: u[0]?.rfid_tag, numero_serie_carregador: c[0]?.numero_serie }));
    }).catch((e) => setErro(e.message));
    carregarSessoes();
  }, [carregarSessoes]);

  const nomes = Object.fromEntries(usuarios.map((u) => [u.id, `${u.nome} (${u.apartamento})`]));
  const alterar = (campo) => (e) => setForm({ ...form, [campo]: e.target.value });

  async function registrar(e) {
    e.preventDefault();
    setErro(null);
    setResultado(null);
    try {
      const r = await api("/sessoes", {
        method: "POST",
        body: { ...form, energia_kwh: Number(form.energia_kwh), id_externo: `MANUAL-${Date.now()}` },
      });
      setResultado(r);
      carregarSessoes();
    } catch (e) {
      setErro(e.message);
    }
  }

  async function sincronizar() {
    const r = await api("/integracao/sems/sincronizar", { method: "POST" });
    setSincronizacao(r);
    carregarSessoes();
  }

  return (
    <>
      <h1>Sessões de recarga</h1>
      <p className="subtitulo">Registre uma leitura do carregador e veja a IA e o rateio agindo sobre ela.</p>

      <div className="cartao" style={{ marginBottom: 16 }}>
        <h2>Registrar leitura do carregador</h2>
        <form className="formulario" onSubmit={registrar}>
          <label>Morador (tag RFID)
            <select value={form.rfid_tag} onChange={alterar("rfid_tag")}>
              {usuarios.map((u) => <option key={u.id} value={u.rfid_tag}>{u.nome} · {u.rfid_tag}</option>)}
            </select>
          </label>
          <label>Carregador
            <select value={form.numero_serie_carregador} onChange={alterar("numero_serie_carregador")}>
              {carregadores.map((c) => <option key={c.id} value={c.numero_serie}>{c.numero_serie} · {c.localizacao}</option>)}
            </select>
          </label>
          <label>Início<input type="datetime-local" value={form.inicio} onChange={alterar("inicio")} /></label>
          <label>Fim da recarga<input type="datetime-local" value={form.fim_recarga} onChange={alterar("fim_recarga")} /></label>
          <label>Desconexão<input type="datetime-local" value={form.fim} onChange={alterar("fim")} /></label>
          <label>Energia (kWh)<input type="number" step="0.1" min="0" value={form.energia_kwh} onChange={alterar("energia_kwh")} /></label>
          <button type="submit">Registrar sessão</button>
          <button type="button" className="secundario" onClick={sincronizar}>Sincronizar com SEMS (simulado)</button>
        </form>
        <p className="suave" style={{ fontSize: 13, marginBottom: 0 }}>
          Dica: com 3 h de recarga, 7 kW permite no máximo ~23 kWh. Coloque 60 kWh para ver a IA barrar a sessão.
        </p>
      </div>

      {erro && <div className="erro">{erro}</div>}
      {sincronizacao && (
        <div className="sucesso">
          Sincronização: {sincronizacao.importadas} sessões importadas desde {dataHora(sincronizacao.desde)}
          {sincronizacao.em_revisao > 0 && `, ${sincronizacao.em_revisao} enviadas para revisão`}.
        </div>
      )}

      {resultado && (
        <div className="grade grade-2">
          <div className="cartao">
            <h2>Análise da IA</h2>
            <p><Selo status={resultado.sessao.status} /></p>
            {resultado.ia.motivos.length
              ? <ul>{resultado.ia.motivos.map((m) => <li key={m}>{m}</li>)}</ul>
              : <p>Sessão dentro do padrão do histórico.</p>}
            <p className="suave">Score de anomalia (Isolation Forest): {resultado.ia.score ?? "modelo ainda sem histórico"}</p>
          </div>
          <div className="cartao">
            <h2>Cálculo do custo</h2>
            {Object.entries(resultado.custo.energia_por_posto).map(([posto, k]) => (
              <div key={posto} className="linha-detalhe"><span>Energia {posto.replace("_", " ")}</span><span>{kwh(k)}</span></div>
            ))}
            <div className="linha-detalhe"><span>Custo da energia</span><span>{brl(resultado.custo.custo_energia)}</span></div>
            <div className="linha-detalhe">
              <span>Ociosidade: {resultado.custo.minutos_ociosos} min ({resultado.custo.minutos_ociosos_cobrados} após tolerância)
                {Object.entries(resultado.custo.ociosidade_por_nivel).map(([n, m]) => ` · ${m} min demanda ${n}`).join("")}</span>
              <span>{brl(resultado.custo.custo_ocupacao)}</span>
            </div>
            <div className="linha-detalhe"><span>Total da sessão</span><span>{brl(resultado.custo.custo_total)}</span></div>
          </div>
        </div>
      )}

      <div className="cartao">
        <h2>Sessões do mês ({sessoes.length})</h2>
        <div className="tabela-container">
          <table>
            <thead>
              <tr><th>Início</th><th>Morador</th><th className="num">Energia</th><th className="num">Ocioso</th>
                <th className="num">Custo</th><th className="num">Score IA</th><th>Status</th><th>Motivo</th></tr>
            </thead>
            <tbody>
              {sessoes.map((s) => (
                <tr key={s.id}>
                  <td>{dataHora(s.inicio)}</td>
                  <td>{nomes[s.usuario_id]}</td>
                  <td className="num">{kwh(s.energia_kwh)}</td>
                  <td className="num">{((new Date(s.fim) - new Date(s.fim_recarga)) / 3600000).toFixed(1)} h</td>
                  <td className="num">{brl(s.custo)}</td>
                  <td className="num">{s.score_anomalia?.toFixed(3) ?? "—"}</td>
                  <td><Selo status={s.status} /></td>
                  <td className="suave" style={{ whiteSpace: "normal", minWidth: 220, fontSize: 13 }}>{s.motivo_revisao || ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
