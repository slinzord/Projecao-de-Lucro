"""
Serviço de projeção contábil (POC).
Lê MLI e D2 do Databricks e retorna base + projeção mensal em formato JSON-friendly.
Quando Databricks falha ou retorna vazio, retorna estrutura em branco para manter o layout.
"""
import pyodbc
import pandas as pd
from typing import Any
from datetime import date

# IDs do empreendimento Cult (default)
MLI_ID = 713
ETAPA_ID = "0028-1"
PROJECT_ID = 2579


def _fallback_response() -> dict[str, Any]:
    """Resposta com dados em branco quando Databricks está indisponível ou retorna vazio."""
    hoje = date.today().isoformat()
    return {
        "base": {
            "data_base": hoje,
            "orcamento_total": 0.0,
            "custo_acumulado": 0.0,
            "receita_contratada_total": 0.0,
            "poc": 0.0,
            "receita_ja_apropriada": 0.0,
            "saldo_restante_mli": 0.0,
        },
        "reference_date_d2": None,
        "restante_d2": 0.0,
        "estouro_obra": 0.0,
        "custo_total_projetado": 0.0,
        "realizado": [],
        "projecao": [],
        "vgv_total": 0.0,
        "modo_demonstracao": True,
    }


def get_projecao_cult(
    mli_id: int = MLI_ID,
    etapa_id: str = ETAPA_ID,
    project_id: int = PROJECT_ID,
    meses_futuros: int = 24,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Retorna base (último MLI) e projeção mensal para o Cult.
    Datas em ISO (YYYY-MM-DD); números como float.
    Se Databricks falhar ou retornar vazio, retorna dados em branco (modo_demonstracao=True).
    """
    try:
        conn = pyodbc.connect("DSN=DatabricksTrinus", autocommit=True)
    except Exception:
        return _fallback_response()

    try:
        sql_mli = f"""
        SELECT *
        FROM sandbox.tgcore_mesa_equity.mli_etapa
        WHERE mli_id = {mli_id}
          AND etapa_id = '{etapa_id}'
        ORDER BY metric_date
        """
        mli = pd.read_sql(sql_mli, conn)
        if mli.empty:
            conn.close()
            return _fallback_response()
        mli["metric_date"] = pd.to_datetime(mli["metric_date"])
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return _fallback_response()

    try:
        sql_d2 = f"""
        SELECT *
        FROM gold_tgcore.equity.d2_projeto_hist
        WHERE project_id = {project_id}
        ORDER BY reference_date, metric_date
        """
        d2 = pd.read_sql(sql_d2, conn)
        d2["metric_date"] = pd.to_datetime(d2["metric_date"])
        d2["reference_date"] = pd.to_datetime(d2["reference_date"])
    except Exception:
        conn.close()
        return _fallback_response()
    conn.close()

    mli_sorted = mli.sort_values("metric_date").reset_index(drop=True)
    n_mli = len(mli_sorted)
    if n_mli == 0:
        return _fallback_response()
    ultimo_mli = mli_sorted.iloc[n_mli - 1]
    data_base = ultimo_mli["metric_date"]
    orcamento_total = float(ultimo_mli["orcamento_total"])
    if overrides and overrides.get("orcamento_total") is not None:
        orcamento_total = float(overrides["orcamento_total"])
    custo_acumulado = float(ultimo_mli["custo_acumulado_total"])
    receita_contratada_total = float(ultimo_mli["valor_receita_total"])
    poc_anterior = float(ultimo_mli["mli_poc_ponderado"])
    receita_ja_apropriada = float(ultimo_mli["receita_poc_total"])

    def row_get_float(row: pd.Series, *keys: str, default: float = 0.0) -> float:
        for k in keys:
            if k in row.index:
                v = row[k]
                if pd.isna(v):
                    continue
                return float(v)
        return default

    # Permuta total reconhecida por destravamento conforme evolução do POC
    permuta_total = row_get_float(ultimo_mli, "valor_permuta_total", "mli_valor_total_permuta", "valor_permuta", default=0.0)

    # Saldo restante no MLI = quanto ainda "sobra" de orçamento para gastar (visão MLI)
    saldo_restante_mli = orcamento_total - custo_acumulado

    base = {
        "data_base": data_base.strftime("%Y-%m-%d"),
        "orcamento_total": orcamento_total,
        "custo_acumulado": custo_acumulado,
        "receita_contratada_total": receita_contratada_total,
        "poc": poc_anterior,
        "receita_ja_apropriada": receita_ja_apropriada,
        "saldo_restante_mli": round(saldo_restante_mli, 2),
    }

    # =====================================================================================
    # Terrain e % vendido (VGV) para aproximar o mesmo princípio do MLI/PDF
    # =====================================================================================
    ref_max = d2["reference_date"].max()
    d2_ref = d2[d2["reference_date"] == ref_max].sort_values("metric_date")
    vgv_total_d2 = float(d2_ref["pure_gsv"].fillna(0).sum())

    def vgv_acum_until(mes_dt: Any) -> float:
        """Soma pure_gsv acumulada na D2 até (inclusive) a data do mês."""
        return float(d2_ref.loc[d2_ref["metric_date"] <= mes_dt, "pure_gsv"].fillna(0).sum())

    # Terreno usado na memória do MLI para POC e apropriação não está nas colunas "custo/orçamento".
    # Inferimos o terreno implícito para fazer o POC base casar com o MLI.
    terreno_inferido = 0.0
    if abs(1.0 - poc_anterior) > 1e-9:
        terreno_inferido = (poc_anterior * orcamento_total - custo_acumulado) / (1.0 - poc_anterior)
    if terreno_inferido < 0 and "land_costs" in d2_ref.columns:
        terreno_inferido = float(d2_ref["land_costs"].fillna(0).sum())
    terreno_total = max(0.0, float(terreno_inferido))

    # Realizado: série histórica do MLI (mesmo formato da projeção para a tabela)
    mli_sorted = mli.sort_values("metric_date")
    realizado = []
    receita_poc_anterior = 0.0
    poc_anterior_mli = 0.0
    custo_aprop_prev_acum = 0.0
    for _, row in mli_sorted.iterrows():
        dt = row["metric_date"]
        receita_poc = float(row["receita_poc_total"])
        receita_mes = receita_poc - receita_poc_anterior
        receita_poc_anterior = receita_poc
        custo_mes = float(row["custo_mes_total"]) if pd.notna(row.get("custo_mes_total")) else 0.0
        custo_mes = abs(custo_mes)
        poc = float(row["mli_poc_ponderado"])
        custo_acum = float(row["custo_acumulado_total"])
        orc_mes = float(row["orcamento_total"]) if pd.notna(row.get("orcamento_total")) else orcamento_total
        # Custo reconhecido no mês: delta de custo apropriado acumulado (mesma ideia de "+ LAG mensal")
        pct_vendido_acum = (vgv_acum_until(dt) / vgv_total_d2) if vgv_total_d2 else 0.0
        custo_aprop_acum = (custo_acum + terreno_total) * pct_vendido_acum
        custo_rec_mes = custo_aprop_acum - custo_aprop_prev_acum
        custo_aprop_prev_acum = custo_aprop_acum
        # Permuta entra na receita por evolução do POC (delta de POC no mês)
        delta_poc_mli = poc - poc_anterior_mli
        receita_permuta_mes = permuta_total * delta_poc_mli
        resultado_mes = (receita_mes + receita_permuta_mes) - custo_rec_mes
        realizado.append({
            "metric_date": dt.strftime("%Y-%m-%d"),
            "orcamento_total": round(orc_mes, 2),
            "poc": round(poc, 6),
            "custo_obra_mes": round(custo_mes, 2),
            "custo_rec_mes": round(custo_rec_mes, 2),
            "vgv_mes": 0.0,
            "despesa_mes": 0.0,
            "receita_mes": round(receita_mes + receita_permuta_mes, 2),
            "resultado_mes": round(resultado_mes, 2),
            "custo_acum": round(custo_acum, 2),
            # Receita acumulada = contrato apropriado (receita_poc_total) + permuta destravada pelo POC
            "receita_acum": round(receita_poc + permuta_total * poc, 2),
        })
        poc_anterior_mli = poc

    ref_max = d2["reference_date"].max()
    serie_d2_full = d2[d2["reference_date"] == ref_max].sort_values("metric_date")

    # D2 (pure_gsv) é a fonte exclusiva do % vendido
    vgv_acum_base_d2 = float(serie_d2_full.loc[serie_d2_full["metric_date"] <= data_base, "pure_gsv"].fillna(0).sum())

    serie_d2 = serie_d2_full[serie_d2_full["metric_date"] > data_base].head(meses_futuros)

    if serie_d2.empty:
        return {
            "base": base,
            "reference_date_d2": ref_max.strftime("%Y-%m-%d") if pd.notna(ref_max) else None,
            "restante_d2": 0.0,
            "estouro_obra": -saldo_restante_mli,
            "custo_total_projetado": custo_acumulado,
            "realizado": realizado,
            "projecao": [],
            "modo_demonstracao": False,
        }

    serie_d2 = serie_d2.copy()
    serie_d2["custo_obra_mes"] = (
        serie_d2["construction_costs"].fillna(0) + serie_d2["construction_administration_costs"].fillna(0)
    )
    serie_d2["vgv_mes"] = serie_d2["pure_gsv"].fillna(0)
    # Colunas de despesa: nomes podem variar (interest vs interests)
    def col_or_zero(df: pd.DataFrame, *names: str) -> pd.Series:
        for n in names:
            if n in df.columns:
                return df[n].fillna(0)
        return pd.Series(0.0, index=df.index)
    serie_d2["despesa_mes"] = (
        col_or_zero(serie_d2, "operating_expenses")
        + col_or_zero(serie_d2, "interests", "interest")
        + col_or_zero(serie_d2, "income_deductions")
    )

    # Restante D2 (ou simulado): soma do custo de obra; se houver overrides, usa os valores por mês
    custo_obra_override = (overrides or {}).get("custo_obra_mes") or {}
    vgv_override = (overrides or {}).get("vgv_mes") or {}
    despesa_override = (overrides or {}).get("despesa_mes") or {}

    def get_custo_obra(mes_dt, row):
        key = mes_dt.strftime("%Y-%m-%d")
        if key in custo_obra_override and custo_obra_override[key] is not None:
            return abs(float(custo_obra_override[key]))
        return abs(float(row["custo_obra_mes"]))

    def get_vgv(mes_dt, row):
        key = mes_dt.strftime("%Y-%m-%d")
        if key in vgv_override and vgv_override[key] is not None:
            return float(vgv_override[key])
        return float(row["vgv_mes"])

    def get_despesa(mes_dt, row):
        key = mes_dt.strftime("%Y-%m-%d")
        if key in despesa_override and despesa_override[key] is not None:
            return abs(float(despesa_override[key]))
        return abs(float(row["despesa_mes"]))

    restante_d2 = 0.0
    for _, row in serie_d2.iterrows():
        restante_d2 += get_custo_obra(row["metric_date"], row)

    # VGV total (para % vendido): D2 (pure_gsv total do horizonte do reference_date)
    vgv_total = float(vgv_total_d2)

    saldo_restante_mli = orcamento_total - custo_acumulado
    estouro_obra = max(0.0, restante_d2 - saldo_restante_mli)
    custo_total_projetado = custo_acumulado + restante_d2 + terreno_total

    projecao = []
    custo_acum_proj = custo_acumulado
    # Receita acumulada no base inclui permuta destravada pelo POC do base
    receita_acum_proj = receita_ja_apropriada + permuta_total * poc_anterior
    receita_contratada_proj = receita_contratada_total
    vgv_acum = vgv_acum_base_d2
    pct_vendido_anterior = (vgv_acum / vgv_total) if vgv_total else 0.0
    custo_aprop_prev_acum_proj = (custo_acumulado + terreno_total) * pct_vendido_anterior
    orcamento_efetivo = orcamento_total
    revisao_ja_aplicada = False

    for _, row in serie_d2.iterrows():
        mes = row["metric_date"]
        custo_obra_mes = get_custo_obra(mes, row)
        vgv_mes = get_vgv(mes, row)
        despesa_mes = get_despesa(mes, row)

        receita_contratada_proj += vgv_mes
        vgv_acum += vgv_mes
        custo_acum_proj += custo_obra_mes

        # No primeiro mês em que o custo acumulado ultrapassar o orçamento, aplica o estouro total de uma vez
        if not revisao_ja_aplicada and estouro_obra > 0 and custo_acum_proj > orcamento_efetivo:
            orcamento_efetivo = orcamento_total + estouro_obra
            revisao_ja_aplicada = True

        # POC com terreno: (custo incorrido acumulado + terreno) / (orcamento + terreno)
        poc_atual = min(
            ((custo_acum_proj + terreno_total) / (orcamento_efetivo + terreno_total)) if (orcamento_efetivo + terreno_total) else 0,
            1.0,
        )
        delta_poc = poc_atual - poc_anterior
        # Receita mês = delta_poc * (contrato + permuta + VGV futuro via receita_contratada_proj)
        receita_mes = delta_poc * (receita_contratada_proj + permuta_total)
        receita_acum_proj += receita_mes
        pct_vendido_atual = (vgv_acum / vgv_total) if vgv_total else 0.0

        # Custo reconhecido no mês via "+ LAG": delta do custo apropriado acumulado
        custo_aprop_acum_atual = (custo_acum_proj + terreno_total) * pct_vendido_atual
        custo_rec_mes = custo_aprop_acum_atual - custo_aprop_prev_acum_proj
        custo_aprop_prev_acum_proj = custo_aprop_acum_atual
        resultado_mes = receita_mes - custo_rec_mes - despesa_mes

        projecao.append({
            "metric_date": mes.strftime("%Y-%m-%d"),
            "orcamento_total": round(orcamento_efetivo, 2),
            "poc": round(poc_atual, 6),
            "custo_obra_mes": round(custo_obra_mes, 2),
            "custo_rec_mes": round(custo_rec_mes, 2),
            "vgv_mes": round(vgv_mes, 2),
            "vgv_pct_mes": round((vgv_mes / vgv_total) if vgv_total else 0.0, 8),
            "vgv_acum": round(vgv_acum, 2),
            "vgv_total": round(vgv_total, 2),
            "pct_vendido": round(pct_vendido_atual, 8),
            "despesa_mes": round(despesa_mes, 2),
            "receita_mes": round(receita_mes, 2),
            "resultado_mes": round(resultado_mes, 2),
            "custo_acum": round(custo_acum_proj, 2),
            "receita_acum": round(receita_acum_proj, 2),
        })
        poc_anterior = poc_atual
        pct_vendido_anterior = pct_vendido_atual

    # Enriquecer histórico realizado com métricas comerciais (aprox. constante no passado)
    # realizado já vem com custo_rec_mes calculado; o resto de métricas comerciais pode ser enriquecido depois

    return {
        "base": base,
        "reference_date_d2": ref_max.strftime("%Y-%m-%d"),
        "restante_d2": round(restante_d2, 2),
        "estouro_obra": round(estouro_obra, 2),
        "custo_total_projetado": round(custo_total_projetado, 2),
        "realizado": realizado,
        "projecao": projecao,
        "vgv_total": round(vgv_total, 2),
        "modo_demonstracao": False,
    }
