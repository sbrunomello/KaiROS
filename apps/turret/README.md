# KaiROS Turret V0

## Visão geral

A turret V0 mantém a lógica validada em hardware real:
- daemon C persistente controla o servo via softPWM
- app Python faz tracking HSV e stream web
- integração entre ambos acontece por `target_file` compartilhado

## Segurança elétrica

- Use alimentação separada para o servo 9g.
- Mantenha **GND comum** entre fonte do servo e Orange Pi.
- Não alimente servo diretamente do pino 5V da placa em carga dinâmica.

## Execução

```bash
./scripts/setup_venv.sh
./scripts/build_servo_daemon.sh
./scripts/run_servo_daemon.sh
./scripts/run_turret.sh
```

## Escolha de cor e câmera

- O target de tracking pode ser alterado em tempo real pela web (`Target`).
- O device de vídeo também pode ser trocado em tempo real pela web (`Device`: 0, 1, 2...).
- Configuração inicial continua vindo de `tracking.color` e `camera.index` no `config.yaml`.

Presets disponíveis: `blue`, `green`, `red`, `yellow`.

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

## Troubleshooting

- Sem vídeo: verifique `camera.index` e permissão em `/dev/video*`.
- Servo não mexe: confirme daemon C ativo e escrita em `/tmp/kairos_servo_target`.
- Tremor no servo: ajuste `write_interval_ms`, `min_angle_step`, `kp` e alimentação.
