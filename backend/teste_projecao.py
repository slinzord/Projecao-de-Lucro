"""
Teste de projeção contábil (POC) para o empreendimento Cult Oxford.
Usa projecao_service e imprime no console (e opcionalmente salva CSV).
"""
from pathlib import Path
import pandas as pd

from projecao_service import get_projecao_cult


def main() -> None:
    data = get_projecao_cult()

    base = data["base"]
    print("--- Base (último mês MLI) ---")
    print(f"Data base: {base['data_base']}")
    print(f"Custo orçado total: {base['orcamento_total']:,.0f}")
    print(f"Custo incorrido acumulado: {base['custo_acumulado']:,.0f}")
    print(f"Receita contratada total: {base['receita_contratada_total']:,.0f}")
    print(f"POC: {base['poc']:.4f}")
    print(f"Receita já apropriada (acum.): {base['receita_ja_apropriada']:,.0f}")
    print()

    proj = data["projecao"]
    if not proj:
        print("D2 não tem meses futuros após a base do MLI.")
        return

    print("--- Projeção ---")
    print(f"reference_date D2: {data['reference_date_d2']}")
    print()
    for r in proj:
        print(
            f"{r['metric_date'][:7]}  POC:{r['poc']:.4f}  Receita:{r['receita_mes']:,.0f}  "
            f"Custo obra:{r['custo_obra_mes']:,.0f}  VGV:{r['vgv_mes']:,.0f}  Desp:{r['despesa_mes']:,.0f}  "
            f"Resultado:{r['resultado_mes']:,.0f}"
        )

    out = Path(__file__).resolve().parent / "projecao_cult_teste.csv"
    pd.DataFrame(proj).to_csv(out, index=False)
    print()
    print(f"Projeção salva em: {out}")


if __name__ == "__main__":
    main()
