import pyodbc


def main() -> None:
    # Usa o DSN já configurado no Windows e força autocommit,
    # pois o driver do Databricks não suporta transações.
    conn = pyodbc.connect("DSN=DatabricksTrinus", autocommit=True)
    cursor = conn.cursor()

    cursor.execute("SELECT 1 AS teste")
    rows = cursor.fetchall()

    print("Resultado do teste de conexão:", rows)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()

