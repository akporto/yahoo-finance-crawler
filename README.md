# Yahoo Finance Equity Screener Crawler

![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)
![Tests](https://img.shields.io/badge/tests-57%20passed-success)
![Coverage](https://img.shields.io/badge/coverage-97%25-brightgreen)
![Lint](https://img.shields.io/badge/lint-flake8-orange)

Pipeline ETL em Python que extrai **símbolo, nome e preço intraday** de todas as ações listadas no [Yahoo Finance Screener](https://finance.yahoo.com/research-hub/screener/equity/) filtradas por região, exportando os resultados para CSV.

> **TL;DR** — Crawler que intercepta a API JSON interna do Yahoo Finance Screener (em vez de fazer scraping HTML), com paginação automática, exponential backoff em falhas transientes e abort imediato em bloqueios de IP. 57 testes unitários, 97% de cobertura, CI/CD com quality gate bloqueante.

---

## Sumário

- [Decisões Arquiteturais](#decisões-arquiteturais)
- [Garantia de Qualidade](#garantia-de-qualidade)
- [Como Executar](#como-executar)
- [Regiões Suportadas](#regiões-suportadas)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Trade-offs do Case](#trade-offs-do-case)
- [Próximos Passos](#próximos-passos)
- [Autora](#autora)

---

## Decisões Arquiteturais

### API Interception vs. HTML Scraping

O Yahoo Finance Screener é renderizado via React — um scraper HTML com BeautifulSoup receberia uma página vazia. Em vez de depender de Selenium (pesado, frágil e lento), o crawler **intercepta diretamente o endpoint JSON interno** que o próprio browser utiliza:

```
POST https://query2.finance.yahoo.com/v1/finance/screener
```

Isso garante:
- **Performance** — resposta em JSON puro, sem overhead de parsing HTML
- **Estabilidade** — imune a quebras de layout do frontend
- **Paginação simples** — o endpoint retorna `total` de registros, permitindo iteração direta

### Autenticação — `session.py`

A API interna exige um token dinâmico chamado **crumb**, vinculado a cookies de sessão válidos. O `YahooSession` gerencia esse handshake de forma transparente:

1. Realiza um GET em `finance.yahoo.com` para obter os cookies de sessão
2. Aceita o consent de GDPR caso haja redirecionamento para `consent.yahoo.com`
3. Extrai o crumb via `GET /v1/test/getcrumb`

O crumb é inicializado **lazily** — obtido apenas na primeira requisição, evitando autenticações desnecessárias.

### Resiliência — `client.py`

O `YahooFinanceScreenerClient` foi construído para ambientes de produção:

- **Paginação automática** — itera páginas de 100 registros até que `offset >= total`
- **Exponential Backoff** — em falhas de rede transientes, realiza até 3 tentativas com pausas progressivas de 1s → 2s entre elas
- **Abort em 401/403** — interrompe imediatamente ao detectar bloqueio, evitando banimento permanente de IP
- **Delay entre páginas** — pausa de 500ms entre requisições para respeitar rate limits

### Imutabilidade — `models.py`

O `StockData` é definido como `@dataclass(frozen=True)`, garantindo que nenhum dado seja mutado após a extração. Isso previne efeitos colaterais silenciosos no pipeline de transformação e torna os objetos naturalmente **hashable** e thread-safe.

### Parser tolerante a falhas — `parser.py`

O `YahooFinanceParser` retorna `None` para registros inválidos em vez de lançar exceções. Isso permite que o pipeline processe milhares de registros sem interrupção, registrando cada falha individualmente via `logging`. Registros sem nome (derivativos e opções argentinas, por exemplo) são descartados com rastreabilidade completa nos logs.

---

## Garantia de Qualidade

### Testes Unitários

O projeto possui **57 testes unitários** cobrindo todos os módulos do pacote `crawler/`:

| Módulo | Cobertura |
|---|---|
| `models.py` | 100% |
| `client.py` | 99% |
| `main.py` | 98% |
| `session.py` | 97% |
| `parser.py` | 91% |
| **Total** | **97%** |

Todas as dependências externas (HTTP, filesystem, CLI) são isoladas com `unittest.mock` — nenhum teste realiza chamadas reais de rede.

### Quality Gate — CI/CD

O pipeline de CI/CD (GitHub Actions) executa em todo Pull Request para `develop` e `main`:

1. **Flake8** — análise estática de qualidade de código (bloqueia o build em violações)
2. **Pytest + Coverage** — exige cobertura mínima de **90%** (`--cov-fail-under=90`)

O build **falha automaticamente** em violações de lint ou queda de cobertura abaixo do threshold, prevenindo regressões de qualidade.

---

## Como Executar

### Pré-requisitos

- **Python 3.10+** (o projeto usa sintaxe de tipos `str | None` introduzida nessa versão)
- Acesso à internet (necessário para o crawler consumir a API do Yahoo Finance)

### Instalação

```bash
git clone https://github.com/akporto/yahoo-finance-crawler.git
cd yahoo-finance-crawler
pip install -r requirements.txt
```

### Execução

```bash
# Buscar ações da Argentina (saída padrão: market_data.csv)
python run.py --region Argentina

# Especificar arquivo de saída
python run.py --region Brazil --output br_stocks.csv

# Usando código ISO da região
python run.py --region us --output us_market.csv
```

### Exemplo de log

Durante a execução, o crawler emite logs estruturados para acompanhamento e auditoria:

```text
2026-05-01 14:08:21 - INFO - Starting pipeline for region 'Argentina' (code: 'ar')
2026-05-01 14:08:23 - INFO - Authenticating with Yahoo Finance...
2026-05-01 14:08:25 - INFO - Fetched 100 records (offset=0, total=1170)
2026-05-01 14:08:26 - INFO - Fetched 100 records (offset=100, total=1170)
...
2026-05-01 14:12:18 - INFO - Extraction complete: 1153 valid, 17 skipped.
2026-05-01 14:12:22 - INFO - Exported 1153 records to 'market_data.csv'.
2026-05-01 14:12:22 - INFO - Pipeline finished successfully.
```

Registros sem nome (derivativos e opções, por exemplo) são descartados com rastreabilidade individual em `WARNING`.

### Formato de saída

```csv
"symbol","name","price"
"AMX.BA","América Móvil, S.A.B. de C.V.","2089.00"
"NOKA.BA","Nokia Corporation","557.50"
```

### Testes e Cobertura

```bash
python -m pytest --cov=crawler --cov-fail-under=90 tests/ -v
```

---

## Regiões Suportadas

O parâmetro `--region` aceita tanto o nome completo quanto o código ISO:

| Região | Código | Região | Código |
|---|---|---|---|
| Argentina | ar | Mexico | mx |
| Australia | au | Netherlands | nl |
| Austria | at | New Zealand | nz |
| Belgium | be | Norway | no |
| Brazil | br | Pakistan | pk |
| Canada | ca | Peru | pe |
| Chile | cl | Philippines | ph |
| China | cn | Poland | pl |
| Czech Republic | cz | Portugal | pt |
| Denmark | dk | Qatar | qa |
| Egypt | eg | Russia | ru |
| Finland | fi | Saudi Arabia | sa |
| France | fr | Singapore | sg |
| Germany | de | South Africa | za |
| Greece | gr | South Korea | kr |
| Hong Kong | hk | Spain | es |
| Hungary | hu | Sweden | se |
| India | in | Switzerland | ch |
| Indonesia | id | Taiwan | tw |
| Ireland | ie | Thailand | th |
| Israel | il | Turkey | tr |
| Italy | it | United Kingdom | gb |
| Japan | jp | United States | us |
| Malaysia | my | Venezuela | ve |
| | | Vietnam | vn |

---

## Estrutura do Projeto

```
yahoo-finance-crawler/
├── .github/
│   └── workflows/
│       └── ci.yml          # GitHub Actions: lint + cobertura em PRs
├── crawler/                # Pacote principal — lógica de negócio isolada
│   ├── __init__.py
│   ├── session.py          # Autenticação: cookies GDPR + crumb token
│   ├── client.py           # Screener API: paginação + exponential backoff
│   ├── parser.py           # Transformação: JSON → StockData
│   ├── models.py           # Domínio: StockData imutável
│   └── main.py             # Orquestração do pipeline ETL
├── tests/
│   ├── test_session.py
│   ├── test_client.py
│   ├── test_parser.py
│   ├── test_models.py
│   └── test_main.py
├── run.py                  # Ponto de entrada CLI
├── pyproject.toml          # Configuração do pytest
└── requirements.txt        # Dependências de produção, lint e testes
```

---

## Trade-offs do Case

### Por que não foram utilizados Testes de Integração reais?

Neste case, foram priorizados testes unitários com `unittest.mock` para isolar chamadas HTTP e autenticação. Em APIs sem ambiente de Sandbox, testes de integração reais tendem a sofrer com `flakiness` por variáveis externas, como instabilidade de rede, alterações no provedor e disponibilidade do serviço. Além disso, a execução recorrente no CI pode gerar bloqueio temporário por `rate limit`, tornando o pipeline imprevisível.

Com mocks, o CI/CD se mantém determinístico: o comportamento esperado da regra de negócio é validado de forma estável em todas as execuções, reduzindo falhas intermitentes e aumentando a confiabilidade do build.

### Dependências em Produção

Para facilitar a experiência de avaliação técnica, as ferramentas de desenvolvimento (testes e lint) foram mantidas no `requirements.txt` principal, evitando passos adicionais de setup para quem for executar o projeto.

Em um deploy produtivo real, o recomendado é separar dependências de runtime e desenvolvimento em arquivos/ambientes distintos. Essa separação reduz a superfície de ataque, diminui o tamanho do pacote distribuído e simplifica o ciclo de atualização de segurança do ambiente de produção.

---

## Próximos Passos

Para evoluir este script para um ecossistema corporativo em nuvem, o caminho natural seria:

1. Substituir o acionamento manual por uma DAG em um orquestrador de pipelines, como **Apache Airflow** ou **AWS Step Functions**, com agendamento, retentativas e monitoramento centralizado.
2. Migrar o armazenamento local em CSV para a nuvem, salvando os dados crus em formato **Parquet**, particionados por região e data de extração, no Amazon S3 como camada inicial do Data Lake.
3. Integrar catálogo e consulta analítica com serviços gerenciados, usando o **AWS Glue Data Catalog** para metadados e o **Amazon Athena** para consultas serverless sobre os dados no S3, com consumo direto por ferramentas de BI como **Amazon QuickSight** ou **Tableau**.
4. Adicionar uma camada de observabilidade com **logs estruturados em JSON** (via `python-json-logger`), métricas de execução (taxa de sucesso, latência média da API, registros extraídos por região) emitidas para **Amazon CloudWatch** ou **Datadog**, e alertas em falhas críticas como autenticação inválida e queda da API. Em ambiente orquestrado, essas métricas alimentariam dashboards de SLO/SLI da pipeline.

---

## Autora

**Ana Kellen Porto**

[![GitHub](https://img.shields.io/badge/GitHub-akporto-181717?style=flat&logo=github)](https://github.com/akporto)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-ana--kellen--nogueira--porto-0A66C2?style=flat&logo=linkedin)](https://www.linkedin.com/in/ana-kellen-nogueira-porto/)
