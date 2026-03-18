import { useEffect, useState } from 'react'
import type { ProjecaoCultResponse } from './types'
import './App.css'

function formatMoney(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'decimal',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

function formatPct(value: number): string {
  return `${(value * 100).toFixed(2)}%`
}

function formatMesCurto(isoDate: string): string {
  // isoDate: YYYY-MM-DD
  const d = new Date(`${isoDate}T00:00:00`)
  const meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
  const mm = meses[d.getMonth()] ?? '—'
  const yy = String(d.getFullYear()).slice(-2)
  return `${mm}/${yy}`
}

function parsePtBrNumber(input: string): number {
  // Aceita "1.234.567", "1.234.567,89", "1234567", "-123"
  const s = (input ?? '').trim()
  if (!s) return NaN
  const normalized = s
    .replace(/\./g, '')
    .replace(/,/g, '.')
    .replace(/[^\d.-]/g, '')
  return Number.parseFloat(normalized)
}

const MESES_REALIZADO_VISIVEIS_RECOLHIDO = 3

function ProjecaoCult() {
  const [baseData, setBaseData] = useState<ProjecaoCultResponse | null>(null)
  const [data, setData] = useState<ProjecaoCultResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isSimulacao, setIsSimulacao] = useState(false)
  const [simuladorLigado, setSimuladorLigado] = useState(false)
  const [realizadoRecolhido, setRealizadoRecolhido] = useState(true)
  const [orcamentoManual, setOrcamentoManual] = useState<string>('') // orçamento total simulação
  const [custoObraManual, setCustoObraManual] = useState<Record<string, string>>({})
  const [vgvManual, setVgvManual] = useState<Record<string, string>>({})
  const [despesaManual, setDespesaManual] = useState<Record<string, string>>({})
  const [focusedInput, setFocusedInput] = useState<string | null>(null)

  const loadBase = () => {
    setLoading(true)
    setError(null)
    fetch('/api/projecao/cult')
      .then(async (res) => {
        if (!res.ok) {
          let msg = `HTTP ${res.status}`
          try {
            const body = await res.json() as { detail?: string }
            if (body.detail) msg = body.detail
          } catch {
            // body não é JSON
          }
          throw new Error(msg)
        }
        return res.json()
      })
      .then((d) => {
        setBaseData(d)
        setData(d)
        setIsSimulacao(false)
        setSimuladorLigado(false)
        setOrcamentoManual(d.base?.orcamento_total != null ? formatMoney(d.base.orcamento_total) : '')
        const custo: Record<string, string> = {}
        const vgv: Record<string, string> = {}
        const desp: Record<string, string> = {}
        ;(d.projecao || []).forEach((r: { metric_date: string; custo_obra_mes: number; vgv_mes: number; despesa_mes: number }) => {
          custo[r.metric_date] = r.custo_obra_mes != null ? formatMoney(r.custo_obra_mes) : ''
          vgv[r.metric_date] = r.vgv_mes != null ? formatMoney(r.vgv_mes) : ''
          desp[r.metric_date] = r.despesa_mes != null ? formatMoney(r.despesa_mes) : ''
        })
        setCustoObraManual(custo)
        setVgvManual(vgv)
        setDespesaManual(desp)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadBase()
  }, [])

  const handleRecalcularSimulacao = () => {
    const payload: { orcamento_total?: number; custo_obra_mes?: Record<string, number>; vgv_mes?: Record<string, number>; despesa_mes?: Record<string, number> } = {}
    const orc = parsePtBrNumber(orcamentoManual)
    if (!Number.isNaN(orc)) payload.orcamento_total = orc
    const custo: Record<string, number> = {}
    const vgv: Record<string, number> = {}
    const desp: Record<string, number> = {}
    Object.entries(custoObraManual).forEach(([k, v]) => {
      const n = parsePtBrNumber(v)
      if (!Number.isNaN(n)) custo[k] = n
    })
    Object.entries(vgvManual).forEach(([k, v]) => {
      const n = parsePtBrNumber(v)
      if (!Number.isNaN(n)) vgv[k] = n
    })
    Object.entries(despesaManual).forEach(([k, v]) => {
      const n = parsePtBrNumber(v)
      if (!Number.isNaN(n)) desp[k] = n
    })
    if (Object.keys(custo).length) payload.custo_obra_mes = custo
    if (Object.keys(vgv).length) payload.vgv_mes = vgv
    if (Object.keys(desp).length) payload.despesa_mes = desp

    setLoading(true)
    fetch('/api/projecao/cult/simular', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
      .then(async (res) => {
        if (!res.ok) {
          let msg = `HTTP ${res.status}`
          try {
            const body = await res.json() as { detail?: string }
            if (body.detail) msg = body.detail
          } catch {
            // body não é JSON
          }
          throw new Error(msg)
        }
        return res.json()
      })
      .then(setData)
      .then(() => setIsSimulacao(true))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }

  if (loading && !data) {
    return <div className="loading">Carregando projeção...</div>
  }
  if (error) {
    return <div className="error">Erro: {error}</div>
  }
  if (!data) return null
  const baseRef = baseData ?? data

  const {
    base,
    reference_date_d2,
    restante_d2 = 0,
    estouro_obra = 0,
    custo_total_projetado = 0,
    realizado = [],
    projecao = [],
  } = data
  const dataBase = base.data_base

  const realizadoVisivel = realizadoRecolhido
    ? realizado.slice(-MESES_REALIZADO_VISIVEIS_RECOLHIDO)
    : realizado
  const realizadoOcultos = realizado.length - realizadoVisivel.length

  const linhas = [
    ...realizadoVisivel.map((r) => ({ ...r, isRealizado: true })),
    ...projecao.map((r) => ({ ...r, isRealizado: false })),
  ]

  const baseProjPorMes = new Map((baseRef.projecao || []).map((r) => [r.metric_date, r]))

  return (
    <section className="projecao-cult">
      {data.modo_demonstracao && (
        <div className="aviso-demonstracao">
          Databricks indisponível ou sem dados — exibindo layout em branco. Você pode ajustar o layout; os números voltam quando a conexão estiver ok.
        </div>
      )}
      <div className="section-header">
        <h2>Realizado + Projeção — Cult Oxford</h2>
        {isSimulacao && <span className="badge simulacao">Cenário simulado</span>}
        <span className="ref-date">
          Base {formatMesCurto(base.data_base)} · D2 {reference_date_d2 ? formatMesCurto(reference_date_d2) : '—'}
        </span>
        {isSimulacao && (
          <button type="button" className="btn-voltar" onClick={loadBase}>
            Voltar aos dados base
          </button>
        )}
      </div>

      <div className="cards-grid">
        <div className="base-card">
          <h3>Base (último mês realizado)</h3>
          <dl>
            <dt>Orçamento total (Base)</dt>
            <dd>{formatMoney(baseRef.base.orcamento_total)}</dd>
            {simuladorLigado && (
              <>
                <dt>Orçamento total (Sim)</dt>
                <dd>
                  <input
                    type="text"
                    inputMode="numeric"
                    value={orcamentoManual}
                    onChange={(e) => setOrcamentoManual(e.target.value)}
                    onFocus={() => {
                      setFocusedInput('orcamento')
                      const n = parsePtBrNumber(orcamentoManual)
                      setOrcamentoManual(Number.isNaN(n) ? '' : String(Math.trunc(n)))
                    }}
                    onBlur={() => {
                      setFocusedInput(null)
                      const n = parsePtBrNumber(orcamentoManual)
                      setOrcamentoManual(Number.isNaN(n) ? '' : formatMoney(n))
                    }}
                    className="input-simulacao"
                  />
                </dd>
              </>
            )}
            <dt>Custo acumulado</dt>
            <dd>{formatMoney(base.custo_acumulado)}</dd>
            <dt>Saldo restante</dt>
            <dd>{formatMoney(base.saldo_restante_mli ?? base.orcamento_total - base.custo_acumulado)}</dd>
            <dt>POC</dt>
            <dd>{formatPct(base.poc)}</dd>
          </dl>
        </div>

        <div className={`estouro-card ${estouro_obra > 0 ? 'com-estouro' : ''}`}>
          <h3>Estouro de obra</h3>
          <dl>
            <dt>Restante (D2)</dt>
            <dd>{formatMoney(restante_d2)}</dd>
            <dt>Custo total projetado</dt>
            <dd>{formatMoney(custo_total_projetado)}</dd>
            <dt>Estouro</dt>
            <dd className={estouro_obra > 0 ? 'negativo' : 'positivo'}>
              {estouro_obra > 0 ? '+' : ''}{formatMoney(estouro_obra)}
            </dd>
          </dl>
          <p className="estouro-legenda">
            {estouro_obra > 0
              ? 'Projeção acima do saldo. Considere ajuste de orçamento.'
              : 'Projeção dentro do saldo.'}
          </p>
        </div>
      </div>

      <div className="tabela-wrapper">
        <div className="tabela-toolbar">
          <h3>Realizado e projeção mensal</h3>
          <div className="tabela-buttons">
            <button
              type="button"
              onClick={() => setSimuladorLigado((v) => !v)}
              className="btn-secundario"
            >
              {simuladorLigado ? 'Fechar simulador' : 'Simular'}
            </button>
            <button
              type="button"
              onClick={() => setRealizadoRecolhido(!realizadoRecolhido)}
              className="btn-secundario"
            >
              {realizadoRecolhido
                ? `Expandir realizado (${realizado.length} meses)`
                : `Recolher (últimos ${MESES_REALIZADO_VISIVEIS_RECOLHIDO} meses)`}
            </button>
            {simuladorLigado && (
              <button type="button" onClick={handleRecalcularSimulacao} className="btn-recalcular">
                Recalcular simulação
              </button>
            )}
          </div>
        </div>

        <table className="tabela-projecao">
          <thead>
            <tr>
              <th>Tipo</th>
              <th>Mês</th>
              <th className="num">Orçamento</th>
              <th>POC</th>
              {simuladorLigado ? (
                <>
                  <th className="num th-base">Custo obra (Base)</th>
                  <th className="num th-sim">Custo obra (Sim)</th>
                  <th className="num th-base">VGV mês (Base)</th>
                  <th className="num th-sim">VGV mês (Sim)</th>
                  <th className="num th-base">Despesa (Base)</th>
                  <th className="num th-sim">Despesa (Sim)</th>
                  <th className="num th-base">VGV % (Base)</th>
                  <th className="num th-sim">VGV % (Sim)</th>
                  <th className="num th-base">% vendido (Base)</th>
                  <th className="num th-sim">% vendido (Sim)</th>
                  <th className="num th-base">Receita mês (Base)</th>
                  <th className="num th-sim">Receita mês (Sim)</th>
                  <th className="num th-base">Custo (Base)</th>
                  <th className="num th-sim">Custo (Sim)</th>
                  <th className="num th-base">Resultado (Base)</th>
                  <th className="num th-sim">Resultado (Sim)</th>
                </>
              ) : (
                <>
                  <th className="num">Custo obra</th>
                  <th className="num">VGV mês</th>
                  <th className="num">Despesas</th>
                  <th className="num">VGV %</th>
                  <th className="num">% vendido</th>
                  <th className="num">Receita mês</th>
                  <th className="num">Custo</th>
                  <th className="num">Resultado</th>
                </>
              )}
              <th className="num">Receita acum.</th>
            </tr>
          </thead>
          <tbody>
            {realizadoRecolhido && realizadoOcultos > 0 && (
              <tr className="row-recolhido">
                <td colSpan={simuladorLigado ? 20 : 13}>… {realizadoOcultos} meses de realizado (expandir acima)</td>
              </tr>
            )}
            {linhas.map((r) => {
              const isUltimoRealizado = r.isRealizado && r.metric_date === dataBase
              const baseLinha = r.isRealizado ? null : (baseProjPorMes.get(r.metric_date) ?? null)
              return (
                <tr key={`${r.metric_date}-${r.isRealizado ? 'r' : 'p'}`} className={isUltimoRealizado ? 'ultimo-realizado' : ''}>
                  <td>
                    {r.isRealizado ? (
                      <span className="badge realizado">Realizado</span>
                    ) : (
                      <span className="badge projecao">Projeção</span>
                    )}
                  </td>
                  <td>{formatMesCurto(r.metric_date)}</td>
                  <td className="num">{r.orcamento_total != null ? formatMoney(r.orcamento_total) : '—'}</td>
                  <td>{formatPct(r.poc)}</td>
                  {simuladorLigado ? (
                    <>
                      <td className="num">{r.isRealizado ? formatMoney(r.custo_obra_mes) : formatMoney(baseLinha?.custo_obra_mes ?? r.custo_obra_mes)}</td>
                      <td className="num">
                        {r.isRealizado ? '—' : (
                          <input
                            type="text"
                            inputMode="numeric"
                            value={
                              focusedInput === `custo:${r.metric_date}`
                                ? (custoObraManual[r.metric_date] ?? '')
                                : (() => {
                                    const n = parsePtBrNumber(custoObraManual[r.metric_date] ?? '')
                                    return Number.isNaN(n) ? '' : formatMoney(n)
                                  })()
                            }
                            onChange={(e) => setCustoObraManual((prev) => ({ ...prev, [r.metric_date]: e.target.value }))}
                            onFocus={() => {
                              setFocusedInput(`custo:${r.metric_date}`)
                              const n = parsePtBrNumber(custoObraManual[r.metric_date] ?? '')
                              setCustoObraManual((prev) => ({ ...prev, [r.metric_date]: Number.isNaN(n) ? '' : String(Math.trunc(n)) }))
                            }}
                            onBlur={() => {
                              setFocusedInput(null)
                              const n = parsePtBrNumber(custoObraManual[r.metric_date] ?? '')
                              setCustoObraManual((prev) => ({ ...prev, [r.metric_date]: Number.isNaN(n) ? '' : formatMoney(n) }))
                            }}
                            className="input-celula"
                          />
                        )}
                      </td>
                      <td className="num">{r.isRealizado ? formatMoney(r.vgv_mes) : formatMoney(baseLinha?.vgv_mes ?? r.vgv_mes)}</td>
                      <td className="num">
                        {r.isRealizado ? '—' : (
                          <input
                            type="text"
                            inputMode="numeric"
                            value={
                              focusedInput === `vgv:${r.metric_date}`
                                ? (vgvManual[r.metric_date] ?? '')
                                : (() => {
                                    const n = parsePtBrNumber(vgvManual[r.metric_date] ?? '')
                                    return Number.isNaN(n) ? '' : formatMoney(n)
                                  })()
                            }
                            onChange={(e) => setVgvManual((prev) => ({ ...prev, [r.metric_date]: e.target.value }))}
                            onFocus={() => {
                              setFocusedInput(`vgv:${r.metric_date}`)
                              const n = parsePtBrNumber(vgvManual[r.metric_date] ?? '')
                              setVgvManual((prev) => ({ ...prev, [r.metric_date]: Number.isNaN(n) ? '' : String(Math.trunc(n)) }))
                            }}
                            onBlur={() => {
                              setFocusedInput(null)
                              const n = parsePtBrNumber(vgvManual[r.metric_date] ?? '')
                              setVgvManual((prev) => ({ ...prev, [r.metric_date]: Number.isNaN(n) ? '' : formatMoney(n) }))
                            }}
                            className="input-celula"
                          />
                        )}
                      </td>
                      <td className="num">{r.isRealizado ? formatMoney(r.despesa_mes) : formatMoney(baseLinha?.despesa_mes ?? r.despesa_mes)}</td>
                      <td className="num">
                        {r.isRealizado ? '—' : (
                          <input
                            type="text"
                            inputMode="numeric"
                            value={
                              focusedInput === `desp:${r.metric_date}`
                                ? (despesaManual[r.metric_date] ?? '')
                                : (() => {
                                    const n = parsePtBrNumber(despesaManual[r.metric_date] ?? '')
                                    return Number.isNaN(n) ? '' : formatMoney(n)
                                  })()
                            }
                            onChange={(e) => setDespesaManual((prev) => ({ ...prev, [r.metric_date]: e.target.value }))}
                            onFocus={() => {
                              setFocusedInput(`desp:${r.metric_date}`)
                              const n = parsePtBrNumber(despesaManual[r.metric_date] ?? '')
                              setDespesaManual((prev) => ({ ...prev, [r.metric_date]: Number.isNaN(n) ? '' : String(Math.trunc(n)) }))
                            }}
                            onBlur={() => {
                              setFocusedInput(null)
                              const n = parsePtBrNumber(despesaManual[r.metric_date] ?? '')
                              setDespesaManual((prev) => ({ ...prev, [r.metric_date]: Number.isNaN(n) ? '' : formatMoney(n) }))
                            }}
                            className="input-celula"
                          />
                        )}
                      </td>
                      <td className="num">{formatPct((baseLinha?.vgv_pct_mes ?? r.vgv_pct_mes ?? 0))}</td>
                      <td className="num">{formatPct((r.vgv_pct_mes ?? 0))}</td>
                      <td className="num">{formatPct((baseLinha?.pct_vendido ?? r.pct_vendido ?? 0))}</td>
                      <td className="num">{formatPct((r.pct_vendido ?? 0))}</td>
                      <td className="num">{formatMoney(baseLinha?.receita_mes ?? r.receita_mes)}</td>
                      <td className="num">{formatMoney(r.receita_mes)}</td>
                      <td className="num">{formatMoney(baseLinha?.custo_rec_mes ?? 0)}</td>
                      <td className="num">{formatMoney(r.custo_rec_mes ?? 0)}</td>
                      <td className={`num ${(baseLinha?.resultado_mes ?? r.resultado_mes) >= 0 ? 'positivo' : 'negativo'}`}>
                        {formatMoney(baseLinha?.resultado_mes ?? r.resultado_mes)}
                      </td>
                      <td className={`num ${r.resultado_mes >= 0 ? 'positivo' : 'negativo'}`}>
                        {formatMoney(r.resultado_mes)}
                      </td>
                    </>
                  ) : (
                    <>
                      <td className="num">{formatMoney(r.custo_obra_mes)}</td>
                      <td className="num">{formatMoney(r.vgv_mes)}</td>
                      <td className="num">{formatMoney(r.despesa_mes)}</td>
                      <td className="num">{formatPct(r.vgv_pct_mes ?? 0)}</td>
                      <td className="num">{formatPct(r.pct_vendido ?? 0)}</td>
                      <td className="num">{formatMoney(r.receita_mes)}</td>
                      <td className="num">{formatMoney(r.custo_rec_mes ?? 0)}</td>
                      <td className={`num ${r.resultado_mes >= 0 ? 'positivo' : 'negativo'}`}>
                        {formatMoney(r.resultado_mes)}
                      </td>
                    </>
                  )}
                  <td className="num">{formatMoney(r.receita_acum)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
        <p className="tabela-dica">Custo obra e VGV editáveis nas linhas de Projeção. Ajuste e clique em Recalcular simulação.</p>
      </div>
    </section>
  )
}

export default function App() {
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="logo">Projeção Lucro</div>
        <nav>
          <a href="#" className="nav-item active">Projeção Cult</a>
          <a href="#" className="nav-item">Empreendimentos</a>
          <a href="#" className="nav-item">Configuração</a>
        </nav>
      </aside>
      <main className="main">
        <header className="header">
          <h1>Projeção de resultado contábil</h1>
          <p className="subtitle">Visão por etapa · POC e projeção mensal</p>
        </header>
        <ProjecaoCult />
      </main>
    </div>
  )
}
