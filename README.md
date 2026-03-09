# KaiROS

KaiROS (Lightweight Robot Operating System for Edge Devices) é um projeto para robótica embarcada leve em hardware de baixo consumo.

Este repositório contém **dois módulos principais**:

1. **Bot Runtime V0 (`apps/bot`)**: tracking por cor HSV + stream MJPEG + controle de servo.
2. **LLM Web (`llm`)**: aplicação de chat web (FastAPI) isolada do módulo de visão/servo.

---

## Pré-requisitos

### Sistema operacional e pacotes base
- Linux (testado em SBCs como Orange Pi e também em desktop Linux para desenvolvimento)
- `python3` (recomendado 3.10+)
- `python3-venv`
- `gcc`
- `make` (opcional, para atalhos)

Para o módulo Bot com servo físico:
- biblioteca `wiringPi` instalada no sistema
- câmera acessível em `/dev/video*`
- permissões para acessar vídeo/GPIO

---

## Como rodar o projeto (visão geral)

Você pode rodar:
- somente o **Bot Runtime V0**
- somente o **LLM Web**
- ambos em paralelo (portas diferentes)

---

## 1) Rodando o Bot Runtime V0

### 1.1 Setup do ambiente Python (raiz do repositório)

```bash
./scripts/setup_venv.sh
```

Alternativa com Makefile:

```bash
make venv
```

### 1.2 Compilar daemon de servo (C)

```bash
./scripts/build_servo_daemon.sh
```

Alternativa com Makefile:

```bash
make build
```

### 1.3 Subir o daemon de servo

```bash
./scripts/run_servo_daemon.sh
```

Alternativa com Makefile:

```bash
make run-servo
```

> Mantenha esse processo em execução.

### 1.4 Subir aplicação web da bot (novo terminal)

```bash
./scripts/run_bot.sh
```

Alternativa com Makefile:

```bash
make run-web
```

Acesso:
- `http://localhost:8080`
- ou `http://<IP_DA_MAQUINA>:8080`

### 1.5 Overrides úteis em runtime

```bash
./scripts/run_bot.sh --color green --width 424 --height 240 --fps 15 --port 8080
./scripts/run_bot.sh --no-servo
```

### 1.6 Configuração principal

Arquivo: `apps/bot/config.yaml`.

Para detalhes completos da bot, consulte `apps/bot/README.md`.

---

## 2) Rodando o LLM Web

### 2.1 Criar ambiente virtual e instalar dependências

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r llm/requirements.txt
```

### 2.2 Subir aplicação

```bash
uvicorn llm.app.main:app --host 0.0.0.0 --port 8091
```

Acesso:
- `http://localhost:8091`
- `http://<IP_DA_MAQUINA>:8091`

### 2.3 Configurar OpenRouter

1. Abra `http://<host>:8091/settings`
2. Informe API key
3. Informe o modelo (texto livre, exemplo: `deepseek/deepseek-chat`)
4. Salve

Para detalhes completos do módulo LLM, consulte `llm/README.md`.

---

## 3) Rodando os dois módulos juntos

Execução simultânea recomendada:
- Bot em `:8080`
- LLM em `:8091`

Fluxo prático:
1. Terminal A: `./scripts/run_servo_daemon.sh`
2. Terminal B: `./scripts/run_bot.sh`
3. Terminal C: `uvicorn llm.app.main:app --host 0.0.0.0 --port 8091`

---

## Testes

Testes do projeto principal:

```bash
.venv/bin/python -m pytest -q tests
```

Testes do módulo LLM:

```bash
.venv/bin/python -m pytest -q llm/tests
```

Ou via Makefile (suite principal):

```bash
make test
```

---

## Troubleshooting rápido

- **`.venv` ausente**: rode `./scripts/setup_venv.sh`.
- **`servo_daemon` não encontrado**: rode `./scripts/build_servo_daemon.sh`.
- **Sem vídeo**: valide `camera.index` em `apps/bot/config.yaml` e permissões de `/dev/video*`.
- **Servo não responde**: confirme daemon ativo e escrita em `/tmp/kairos_servo_target`.
- **Porta ocupada**: ajuste com `--port` na bot ou `--port` no `uvicorn`.

---

## Roadmap

Consulte `docs/ROADMAP.md`.
