# Roadmap KaiROS

- **v0.1**: bot tracking por cor + stream web + servo horizontal
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

## Próximas tasks (visão computacional) — backlog priorizado

> Foco: aumentar robustez do tracking em produção sem perder desempenho em hardware embarcado.

### Sprint 1 — estabilidade e observabilidade

1. **Instrumentar métricas por estágio do pipeline**
   - Capturar latência de `capture`, `preprocess`, `detect_hsv`, `detect_motion`, `control`.
   - Publicar agregados (p50/p95) no health endpoint para diagnóstico rápido.
2. **Criar dataset de regressão local (offline)**
   - Salvar pequenos clipes com cenários reais: variação de luz, oclusão parcial e múltiplos objetos.
   - Definir suíte de replay para comparar `target_found`, jitter e tempo de reacquisição.
3. **Histerese de decisão no lock do alvo**
   - Requerer score mínimo para entrar em `TRACKING` e um score menor para sair (evita oscilação).
4. **Guard rails de servo por software**
   - Clamp de velocidade angular máxima por frame.
   - Cooldown curto após perda de alvo para reduzir caça agressiva.

### Sprint 2 — robustez em cenário real

1. **Auto-ajuste dinâmico de HSV por região de interesse (ROI)**
   - Ajustar limiares com base em estatísticas locais quando confiança cair de forma contínua.
2. **Validação geométrica do alvo**
   - Adicionar filtros de razão de aspecto, área relativa e estabilidade do centróide.
3. **Mecanismo de re-identificação simplificado**
   - Cache de assinatura visual leve (histograma HSV compactado) para evitar troca de alvo.
4. **Modo degradação controlada**
   - Quando FPS cair abaixo do limite, reduzir resolução/ROI progressivamente.

### Sprint 3 — preparação para detector por IA leve

1. **Arquitetura plugável de detectores**
   - Interface única para `HSV`, `Motion` e `Neural` com contrato de confiança padronizado.
2. **Pipeline assíncrono (frame queue)**
   - Separar captura, inferência e controle para reduzir bloqueio em picos.
3. **Benchmark embarcado**
   - Medir consumo de CPU/RAM/temperatura por detector e por resolução.
4. **Critérios de go/no-go para YOLO-nano/MobileNet**
   - Só promover para produção se atender metas de FPS mínimo e latência máxima.

### Definition of Done (DoD) para cada task

- Código com testes unitários e de regressão para regras de estado.
- Logs estruturados com campos consistentes para telemetria.
- Configuração documentada em `config.yaml` com valores padrão seguros.
- Resultado comparado com baseline anterior (métrica e evidência no PR).
