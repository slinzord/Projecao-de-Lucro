export interface BaseProjecao {
  data_base: string
  orcamento_total: number
  custo_acumulado: number
  receita_contratada_total: number
  poc: number
  receita_ja_apropriada: number
  saldo_restante_mli: number
}

export interface LinhaProjecao {
  metric_date: string
  orcamento_total?: number
  poc: number
  custo_obra_mes: number
  /** Custo reconhecido no resultado do mês */
  custo_rec_mes?: number
  vgv_mes: number
  /** VGV do mês / VGV total (0-1) */
  vgv_pct_mes?: number
  /** VGV acumulado (contratado base + vendas futuras acumuladas) */
  vgv_acum?: number
  /** VGV total (contratado base + vendas futuras totais) */
  vgv_total?: number
  /** % vendido acumulado (vgv_acum/vgv_total) */
  pct_vendido?: number
  despesa_mes: number
  receita_mes: number
  resultado_mes: number
  custo_acum: number
  receita_acum: number
}

export interface ProjecaoCultResponse {
  base: BaseProjecao
  reference_date_d2: string | null
  restante_d2: number
  estouro_obra: number
  custo_total_projetado: number
  realizado: LinhaProjecao[]
  projecao: LinhaProjecao[]
  vgv_total?: number
  /** true quando Databricks falhou ou retornou vazio; dados exibidos são placeholders */
  modo_demonstracao?: boolean
}
