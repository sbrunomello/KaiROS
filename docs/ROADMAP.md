# Roadmap KaiROS

- **v0.1**: turret tracking por cor + stream web + servo horizontal
- **v0.2**: modo manual/auto + scan mode + health melhorado
- **v0.3**: backend PCA9685
- **v0.4**: pan+tilt
- **v0.5**: rover base
- **v0.6**: WebRTC
- **v1.0**: módulo KaiROS padronizado

## Próximo passo recomendado para visão computacional

### Objetivo imediato (1 sprint)
Evoluir de **tracking apenas por HSV** para um pipeline **híbrido e resiliente**:

1. **Detecção primária por cor (HSV)** para manter baixo custo computacional.
2. **Confirmação temporal** (N frames consecutivos) antes de acionar o servo.
3. **Fallback por movimento (background subtraction/MOG2)** quando a cor alvo se perde.
4. **Suavização de alvo** com filtro exponencial (EMA) para reduzir jitter.

> Resultado esperado: menos falso-positivo, rastreamento mais estável e recuperação automática quando iluminação variar.

### Critérios técnicos de pronto

- Perda do alvo recuperada em até **2 segundos** em cenário indoor.
- Redução de jitter perceptível no servo (medido por desvio angular médio).
- Queda de FPS menor que **15%** versus baseline atual.
- Logs com métricas por frame: `fps`, `confidence`, `target_found`, `target_age_ms`.

### Plano de implementação sugerido

1. **Adicionar confiança de detecção no `tracking.py`**
   - score por área, circularidade e persistência temporal.
2. **Criar estado de rastreamento explícito**
   - `SEARCHING`, `LOCKING`, `TRACKING`, `LOST`.
3. **Implementar fallback por movimento**
   - ativado apenas quando HSV falhar por janela configurável.
4. **Expor parâmetros no `config.yaml`**
   - thresholds HSV, janela temporal, ganho do EMA e timeout de perda.
5. **Adicionar testes de regressão do estado de tracking**
   - validar transições de estado e anti-oscilação.

### Riscos previstos e mitigação

- **Mudança de iluminação**: usar auto-calibração simples de V (canal Value) + fallback de movimento.
- **Ruído visual**: combinar área mínima e persistência temporal.
- **Oscilação de servo**: limitar variação angular por frame + EMA.

### Evolução seguinte (depois deste passo)
Após estabilizar o híbrido HSV+movimento, o próximo salto é detector por IA leve (ex.: MobileNet/YOLO-nano em ROI), mantendo HSV como fallback de baixo custo.
