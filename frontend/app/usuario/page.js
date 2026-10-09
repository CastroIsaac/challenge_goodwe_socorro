"use client";

import { useEffect, useState } from "react";
import { Assistente, Kpi, Selo } from "@/components/Componentes";
import { api, brl, dataHora, kwh, mesAtual } from "@/lib/api";

export default function AreaMorador() {
  const [usuarios, setUsuarios] = useState([]);
  const [usuarioId, setUsuarioId] = useState("");
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(null);
  const mes = mesAtual();

  useEffect(() => {
    api("/usuarios")
      .then((lista) => { setUsuarios(lista); setUsuarioId(lista[0]?.id || ""); })
      .catch((e) => setErro(e.message));
  }, []);

  useEffect(() => {
    if (!usuarioId) return;
    setDados(null);
    Promise.all([
      api(`/rateio/${mes}`),
      api(`/sessoes?mes=${mes}&usuario_id=${usuarioId}`),
      api(`/ia/perfis/${usuarioId}`).catch(() => null),
    ]).then(([rateio, sessoes, perfil]) => {
      setDados({ fatura: rateio.itens.find((i) => i.usuario_id === usuarioId), sessoes, perfil });
    }).catch((e) => setErro(e.message));
  }, [usuarioId, mes]);

  if (erro) return <div className="erro">Erro ao falar com a API: {erro}</div>;
  const usuario = usuarios.find((u) => u.id === usuarioId);

  return (
    <>
      <div className="cabecalho">
        <div>
          <h1>Área do morador</h1>
          <p className="subtitulo">O que cada morador vê: consumo, fatura detalhada, perfil e assistente.</p>
        </div>
        <label>
          Visualizando como
          <select value={usuarioId} onChange={(e) => setUsuarioId(e.target.value)}>
            {usuarios.map((u) => <option key={u.id} value={u.id}>{u.nome} · ap. {u.apartamento}</option>)}
          </select>
        </label>
      </div>

      {!dados ? <p className="suave">Carregando…</p> : (
        <>
          <div className="grade grade-kpi">
            <Kpi rotulo={`Consumo em ${mes}`} valor={kwh(dados.fatura?.energia_kwh)} detalhe={`${dados.fatura?.sessoes || 0} recargas faturáveis`} />
            <Kpi rotulo="Valor parcial do mês" valor={brl(dados.fatura?.valor_total)} detalhe="atualizado a cada sessão" />
            <Kpi rotulo="Perfil de uso (IA)" valor={dados.perfil?.nome || "—"}
                 detalhe={dados.perfil ? `início médio às ${Math.round(dados.perfil.habitos.hora_media)}h` : "histórico insuficiente"} />
          </div>

          <div className="grade grade-2">
            <div className="cartao">
              <h2>Composição da fatura</h2>
              {dados.fatura ? (
                <>
                  <div className="linha-detalhe"><span>Energia (kWh × tarifa do horário)</span><span>{brl(dados.fatura.valor_energia)}</span></div>
                  <div className="linha-detalhe"><span>Ocupação (tempo conectado sem carregar)</span><span>{brl(dados.fatura.valor_ocupacao)}</span></div>
                  <div className="linha-detalhe"><span>Cota de manutenção compartilhada</span><span>{brl(dados.fatura.valor_manutencao)}</span></div>
                  <div className="linha-detalhe"><span>Total</span><span>{brl(dados.fatura.valor_total)}</span></div>
                  {dados.fatura.sessoes_em_revisao > 0 && (
                    <p className="aviso" style={{ marginTop: 12 }}>
                      {dados.fatura.sessoes_em_revisao} sessão(ões) em revisão ainda não estão incluídas.
                    </p>
                  )}
                </>
              ) : <p className="suave">Sem recargas faturáveis neste mês.</p>}
              {dados.perfil && (
                <p className="sucesso" style={{ marginTop: 16, marginBottom: 0 }}>
                  <strong>Dica para seu perfil:</strong> {dados.perfil.recomendacao}
                </p>
              )}
            </div>
            <div className="cartao">
              <h2>Assistente</h2>
              {usuario && <Assistente key={usuario.id} usuarioId={usuario.id} />}
            </div>
          </div>

          <div className="cartao">
            <h2>Minhas sessões em {mes}</h2>
            <div className="tabela-container">
              <table>
                <thead>
                  <tr><th>Início</th><th>Fim da recarga</th><th>Desconexão</th><th className="num">Energia</th>
                    <th className="num">Energia R$</th><th className="num">Ocupação R$</th><th className="num">Total</th><th>Status</th></tr>
                </thead>
                <tbody>
                  {dados.sessoes.map((s) => (
                    <tr key={s.id}>
                      <td>{dataHora(s.inicio)}</td><td>{dataHora(s.fim_recarga)}</td><td>{dataHora(s.fim)}</td>
                      <td className="num">{kwh(s.energia_kwh)}</td><td className="num">{brl(s.custo_energia)}</td>
                      <td className="num">{brl(s.custo_ocupacao)}</td><td className="num">{brl(s.custo)}</td>
                      <td><Selo status={s.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </>
  );
}
