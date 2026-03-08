# KaiROS

KaiROS (Lightweight Robot Operating System for Edge Devices) é um projeto para robótica embarcada leve em hardware de baixo consumo.

## KaiROS Turret V0

Nesta versão inicial, o projeto entrega uma torreta com:
- webcam USB
- tracking por cor HSV em tempo real
- stream web MJPEG
- daemon C persistente para servo horizontal (softPWM)
- controle de modo auto/manual via API web

## Stack atual

- Orange Pi Zero 3 (Linux headless)
- Daemon C com wiringPi/softPwm
- Python 3 + Flask + OpenCV headless + NumPy + PyYAML

## Setup rápido

```bash
./scripts/setup_venv.sh
./scripts/build_servo_daemon.sh
./scripts/run_servo_daemon.sh
# em outro terminal
./scripts/run_turret.sh
```

Abra no navegador: `http://<IP_DO_ORANGE_PI>:8080`

## Configuração

Arquivo principal: `apps/turret/config.yaml`.

Exemplos de override por CLI:

```bash
./scripts/run_turret.sh --color green --width 424 --height 240 --fps 15 --port 8080
./scripts/run_turret.sh --no-servo
```

## Limitações atuais

- backend de servo via arquivo (`/tmp/kairos_servo_target`) é provisório
- softPWM é funcional para V0, mas não é solução final para múltiplos servos
- WebRTC e PCA9685 ficam para próximos marcos

## Roadmap resumido

Consulte `docs/ROADMAP.md`.
