# Projeção Lucro

Sistema de projeção de resultado contábil (POC) para empreendimentos de incorporação.

## Como rodar

### Backend (API + Databricks)

```bash
cd backend
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

A API fica em `http://localhost:8000`. Endpoints:

- `GET /api/projecao/cult` — projeção do Cult Oxford (base MLI + meses projetados)
- `GET /api/health` — saúde da API

### Frontend (React)

```bash
cd frontend
npm install
npm run dev
```

Acesse `http://localhost:5173`. O Vite faz proxy de `/api` para o backend na porta 8000.

**Ordem:** subir o backend primeiro; depois o frontend.

## Layout previsto

- **Sidebar:** Projeção Cult, Empreendimentos, Configuração (itens ainda placeholder).
- **Conteúdo:** base (último mês MLI) em card; tabela com projeção mensal (POC, receita, custo obra, VGV, despesas, resultado).

## Regras da projeção (Cult)

- Base: último mês do MLI (custo orçado, custo acumulado, receita contratada, POC).
- D2: último `reference_date`; custo de obra = `construction_costs` + `construction_administration_costs`; VGV = `pure_gsv`.
- Despesas: `operating_expenses` + `interests` + `income_deductions`.
