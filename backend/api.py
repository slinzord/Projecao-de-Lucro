"""
API FastAPI para projeção contábil.
Expõe a projeção do Cult para o frontend React.
"""
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from projecao_service import get_projecao_cult

app = FastAPI(title="Projeção Lucro", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SimularBody(BaseModel):
    """Override manual para simulação de cenários."""
    orcamento_total: float | None = None
    custo_obra_mes: dict[str, float] | None = None
    vgv_mes: dict[str, float] | None = None
    despesa_mes: dict[str, float] | None = None


@app.get("/api/projecao/cult")
def projecao_cult():
    """Retorna base MLI + projeção mensal do empreendimento Cult Oxford."""
    try:
        return get_projecao_cult()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projecao/cult/simular")
def projecao_cult_simular(body: SimularBody):
    """Recalcula a projeção com valores manuais (obra e VGV mês a mês, orçamento total)."""
    try:
        overrides: dict[str, Any] = {}
        if body.orcamento_total is not None:
            overrides["orcamento_total"] = body.orcamento_total
        if body.custo_obra_mes:
            overrides["custo_obra_mes"] = body.custo_obra_mes
        if body.vgv_mes:
            overrides["vgv_mes"] = body.vgv_mes
        if body.despesa_mes:
            overrides["despesa_mes"] = body.despesa_mes
        return get_projecao_cult(overrides=overrides if overrides else None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/debug/mli")
def debug_mli():
    """
    Diagnóstico: lista combinações (mli_id, etapa_id) na tabela MLI
    para conferir se os filtros do Cult estão corretos.
    """
    import pyodbc
    import pandas as pd
    try:
        conn = pyodbc.connect("DSN=DatabricksTrinus", autocommit=True)
        # Ver quais mli_id e etapa_id existem na tabela
        sql = """
        SELECT DISTINCT mli_id, etapa_id
        FROM sandbox.tgcore_mesa_equity.mli_etapa
        ORDER BY mli_id, etapa_id
        LIMIT 100
        """
        df = pd.read_sql(sql, conn)
        conn.close()
        # Converter para lista de dict para JSON
        combos = df.to_dict(orient="records")
        for r in combos:
            for k, v in r.items():
                if hasattr(v, "item"):
                    r[k] = v.item()
                elif pd.isna(v):
                    r[k] = None
        return {
            "tabela": "sandbox.tgcore_mesa_equity.mli_etapa",
            "filtro_atual": {"mli_id": 713, "etapa_id": "0028-1"},
            "combinacoes_encontradas": combos,
            "total": len(combos),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
