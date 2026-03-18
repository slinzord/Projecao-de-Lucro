"""
Teste de conexão e leitura das tabelas do Databricks (MLI, D2, balancete).
"""
import pyodbc


def main() -> None:
    conn = pyodbc.connect("DSN=DatabricksTrinus", autocommit=True)
    cursor = conn.cursor()

    # Teste simples
    cursor.execute("SELECT 1 AS teste")
    print("Conexão OK:", cursor.fetchall())

    # Contagem nas tabelas (opcional)
    for nome, sql in [
        ("mli_etapa", "SELECT COUNT(*) FROM sandbox.tgcore_mesa_equity.mli_etapa WHERE mli_id = 713 AND etapa_id = '0028-1'"),
        ("d2_projeto_hist", "SELECT COUNT(*) FROM gold_tgcore.equity.d2_projeto_hist WHERE project_id = 2579"),
        ("incorrido_balancete", "SELECT COUNT(*) FROM sandbox.tgcore_mesa_equity.incorrido_balancete_interno WHERE posicao_id = '0032'"),
    ]:
        try:
            cursor.execute(sql)
            n = cursor.fetchone()[0]
            print(f"  {nome}: {n} linhas")
        except Exception as e:
            print(f"  {nome}: erro - {e}")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
