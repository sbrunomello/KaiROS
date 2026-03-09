# Arquitetura atual (V0)

## Componentes

1. **Daemon C (`servo_daemon.c`)**
   - Processo persistente com `wiringPi` + `softPwm`.
   - Lê alvo de ângulo do arquivo compartilhado e move servo suavemente.

2. **App Python (`apps/bot`)**
   - Captura câmera, roda tracking HSV, disponibiliza MJPEG e APIs Flask.
   - Em modo auto, tracking calcula alvo angular e escreve no backend de servo.
   - Em modo manual, tracking não mexe no servo; apenas endpoints manuais controlam.

3. **Servo backend (arquivo)**
   - Encapsulado em `servo_backend.py`.
   - Implementação V0 via `target_file` para manter baseline funcional validado.

## Modularização aplicada

Para separar claramente percepção e atuação, o serviço Python foi dividido em módulos de domínio:

- **`vision_service.py`**: responsável exclusivamente por captura, processamento de visão e publicação de frames/telemetria.
- **`servo_service.py`**: camada de aplicação para comandos de servo, desacoplando regras de negócio do backend físico.
- **`web.py`**: camada de apresentação/API, com status de módulos (`vision` e `servo`) exposto no `/health` e no dashboard.

Essa divisão permite evoluir a visão computacional primeiro (pipeline, filtros e métricas) sem quebrar o controle físico.

## Motivo da escolha no V0

A separação daemon C + app Python reduz latência de controle do servo e mantém o comportamento já validado no Orange Pi.

## Próxima evolução

`FileServoBackend` foi isolado para futura troca por backend PCA9685 sem alterar tracking/web.
