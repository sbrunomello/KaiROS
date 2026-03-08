# KaiROS LLM (subprojeto isolado)

Aplicação web de chat estilo ChatGPT, **isolada em `./llm`**, com FastAPI + Jinja + SQLite, pronta para rodar 24/7 em Orange Pi.

## Recursos
- Chat web responsivo (desktop/celular)
- Sidebar com histórico de conversas
- Botão **Novo chat**
- Página de configurações
- Configuração de API key OpenRouter
- Campo de modelo **livre** (sem dropdown fixo)
- Persistência local de conversas, mensagens e settings
- Healthcheck (`/healthz`) e status (`/status`)
- Testes automatizados com `pytest`

## Arquitetura
- `app/main.py`: bootstrap da aplicação
- `app/routes/`: rotas web + APIs
- `app/services/`: regras de negócio, prompt/contexto, router de modelo, provider LLM
- `app/templates/`: interface HTML
- `app/static/`: CSS/JS leve
- `data/`: banco SQLite
- `deploy/`: systemd + install
- `tests/`: suíte automatizada

---

## Pré-requisitos

- Python 3.10+
- `python3-venv`
- acesso de rede para chamar provider LLM (quando usar OpenRouter)

---

## Como rodar localmente (desenvolvimento)

Na raiz do repositório:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r llm/requirements.txt
```

Suba a aplicação:

```bash
uvicorn llm.app.main:app --host 0.0.0.0 --port 8091
```

Acesse:
- Local: `http://localhost:8091`
- Rede local: `http://<IP_DA_MAQUINA>:8091`

---

## Configuração OpenRouter

1. Abra `http://<host>:8091/settings`
2. Preencha API key
3. Informe o modelo em texto livre (ex.: `deepseek/deepseek-chat`)
4. Salve

---

## Rodar com systemd (produção)

Arquivos em `llm/deploy/`:
- `env.example`
- `llm.service`
- `install.sh`

Instalação automatizada:

```bash
bash llm/deploy/install.sh
```

Após instalação:
- ajuste `llm/deploy/.env` conforme necessário
- valide com `systemctl status llm.service`

---

## Testes

```bash
.venv/bin/python -m pytest -q llm/tests
```

## Limitações atuais
- Sem autenticação/multiusuário
- Sem streaming de tokens
- Sem integração com robô (proposital)

## Próximos passos sugeridos
- Streaming SSE para UX melhor
- Backup/exportação de conversas
- Observabilidade (métricas)
