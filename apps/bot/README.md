# KaiROS Bot Runtime V0

## Visão geral

A Bot Runtime V0 mantém a lógica validada em hardware real:
- daemon C persistente controla o servo via softPWM
- app Python faz tracking HSV e stream web
- integração entre ambos ocorre por `target_file` compartilhado (`/tmp/kairos_servo_target`)

---

## Pré-requisitos

- Linux com acesso a `/dev/video*`
- Python 3 + `venv`
- `gcc`
- `wiringPi` (para build/execução do daemon de servo)
- câmera USB conectada

---

## Segurança elétrica (obrigatório)

- Use alimentação separada para o servo 9g.
- Mantenha **GND comum** entre fonte do servo e Orange Pi.
- Não alimente servo diretamente do pino 5V da placa em carga dinâmica.

---

## Como rodar

A partir da **raiz do repositório**:

1. Criar ambiente e instalar dependências:

```bash
./scripts/setup_venv.sh
```

2. Compilar daemon C:

```bash
./scripts/build_servo_daemon.sh
```

3. Iniciar daemon de servo:

```bash
./scripts/run_servo_daemon.sh
```

4. Em outro terminal, iniciar app web:

```bash
./scripts/run_bot.sh
```

Acesse: `http://localhost:8080` (ou `http://<IP_DA_MAQUINA>:8080`).

---

## Configuração

Arquivo principal: `apps/bot/config.yaml`.

Exemplos de override via CLI:

```bash
./scripts/run_bot.sh --color green --width 424 --height 240 --fps 15 --port 8080
./scripts/run_bot.sh --no-servo
```

Presets de cor suportados: `blue`, `green`, `red`, `yellow`.

---

## Operação em tempo real

- O target de tracking pode ser alterado pela web (`Target`).
- O device de vídeo também pode ser alterado pela web (`Device`: 0, 1, 2...).
- Configuração inicial continua vindo de `tracking.color` e `camera.index` no `config.yaml`.

---

## Endpoints

- `GET /`
- `GET /video_feed`
- `GET /mask_feed`
- `GET /health`
- `POST /api/mode/auto`
- `POST /api/mode/manual`
- `POST /api/servo/center`
- `POST /api/servo/angle` com JSON `{ "angle": 90 }`
- `POST /api/camera/index` com JSON `{ "index": 1 }`
- `POST /api/tracking/color` com JSON `{ "color": "red" }`

---

## Troubleshooting

- **Sem vídeo**: verifique `camera.index` e permissão em `/dev/video*`.
- **Servo não mexe**: confirme daemon C ativo e escrita em `/tmp/kairos_servo_target`.
- **Tremor no servo**: ajuste `write_interval_ms`, `min_angle_step`, `kp` e alimentação.
