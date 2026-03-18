import pyodbc
import pandas as pd


def main() -> None:
    conn = pyodbc.connect("DSN=DatabricksTrinus", autocommit=True)

    sql_mli = """
    SELECT *
    FROM sandbox.tgcore_mesa_equity.mli_etapa
    WHERE mli_id = 713
      AND etapa_id = '0028-1'
    ORDER BY metric_date
    """

    sql_d2 = """
    SELECT *
    FROM gold_tgcore.equity.d2_projeto_hist
    WHERE project_id = 2579
    ORDER BY metric_date
    """

    sql_bal = """
    SELECT *
    FROM sandbox.tgcore_mesa_equity.incorrido_balancete_interno
    WHERE posicao_id = '0032'
    ORDER BY mes_fiscal
    """

    df_mli = pd.read_sql(sql_mli, conn)
    df_d2 = pd.read_sql(sql_d2, conn)
    df_bal = pd.read_sql(sql_bal, conn)

    df_mli.to_csv("cult_mli.csv", index=False)
    df_d2.to_csv("cult_d2.csv", index=False)
    df_bal.to_csv("cult_balancete.csv", index=False)

    conn.close()
    print("Arquivos salvos: cult_mli.csv, cult_d2.csv, cult_balancete.csv")


if __name__ == "__main__":
    main()

