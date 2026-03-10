# Otimização de custos de providers de IA (foco: custo zero)

## 1) Inventário atual do projeto

Este repositório concentra as integrações de IA no subprojeto `llm/` (FastAPI).
A arquitetura atual é **fortemente acoplada ao OpenRouter**, com endpoint central de `chat/completions` para múltiplas modalidades.

### 1.1 Mapa de uso atual do OpenRouter

| Arquivo | Função/classe | Endpoint interno | Capacidade | Modelo atual (default/seleção) | Endpoint externo | Dependência OpenRouter | Complexidade de migração |
|---|---|---|---|---|---|---|---|
| `llm/app/services/llm_service.py` | `OpenRouterProvider.generate` | `POST /api/chat/{conversation_id}/messages` (via `api_chat`) | Chat texto | `settings.model_name` (default `openrouter/auto`) | `POST /chat/completions` | Total (provider único real) | Baixa (já existe abstração `LLMProvider`) |
| `llm/app/services/openrouter_client.py` | `OpenRouterClient.chat_completion` | Usado por imagem/vídeo | Cliente base para multimodal | Dinâmico | `POST /chat/completions` | Total | Média (trocar cliente + shape de payload/resposta por provider) |
| `llm/app/services/openrouter_client.py` | `OpenRouterClient.get_models` | `GET /api/models`, `GET /api/models/capabilities` | Catálogo de modelos/capacidades | N/A | `GET /models` | Total | Média (cada provider expõe catálogo diferente) |
| `llm/app/routes/api_multimodal.py` + `llm/app/services/image_generation_service.py` | `generate_image` / `ImageGenerationService.generate` | `POST /api/generate-image` | Text → image e image → image | `settings.default_image_model` (default `bytedance-seed/seedream-4.5`) + fallback | `POST /chat/completions` com `modalities=["image"]` | Total | Média/Alta (geração de imagem varia bastante entre providers) |
| `llm/app/routes/api_multimodal.py` + `llm/app/services/video_analysis_service.py` | `analyze_video` / `VideoAnalysisService.analyze` | `POST /api/analyze-video` | Video → text | `settings.default_video_analysis_model` (default `nvidia/nemotron-nano-12b-v2-vl:free`) | `POST /chat/completions` com `video_url` em Data URL | Total | Alta (Groq/HF/local têm fluxos diferentes para vídeo) |
| `llm/app/services/multimodal_service.py` | `ModelCatalogService.get_capabilities` | `GET /api/models/capabilities` | Classificação de capacidades (`image`, `video`) | Detectado via `architecture.*_modalities` | `GET /models` | Total | Média |
| `llm/app/models.py` / `llm/app/schemas.py` / templates | `Settings.openrouter_api_key`, `model_name` etc. | `GET/PUT /api/settings` + UI | Configuração e UX | Defaults OpenRouter | N/A | Alta (nome/campo explícito OpenRouter) | Baixa/Média (renomear para provider genérico) |

### 1.2 Capacidades realmente implementadas hoje

Implementadas e em produção local:
- **Chat texto**.
- **Text → image**.
- **Image → image**.
- **Video → text**.

Não implementadas (ou apenas placeholder):
- **Image → text** (não há endpoint dedicado no backend hoje).
- **Audio → text** (não há endpoint dedicado).
- **Video generation** (`/api/generate-video`) retorna 501.

### 1.3 Observações de acoplamento

- A chave de API e nomenclatura ainda são centradas em `openrouter_api_key`.
- Para multimodal, o contrato esperado é o do OpenRouter (`choices[0].message`, `images[].image_url`, Data URL etc.).
- Catálogo de modelos assume formato de `architecture.input_modalities` / `output_modalities` do OpenRouter.

---

## 2) Matriz por capacidade (foco em gratuito/free tier)

> Legenda rápida de custo esperado:
> - **Zero**: possível operar sem custo recorrente razoável.
> - **Baixo/variável**: geralmente free tier cobre dev, mas pode exigir fallback pago em escala.

| Capacidade | Groq free tier | Hugging Face free inference | Local (Ollama/llama.cpp/whisper.cpp/SD) | Outros providers free | Custo esperado | Dificuldade |
|---|---|---|---|---|---|---|
| Chat texto | **Sim** (forte candidato principal) | **Sim** (latência/limites variam) | **Sim** (Llama/Qwen quantizados) | OpenRouter free models, Cloudflare AI | Zero a baixo | Baixa |
| Image → text (vision) | **Sim** (modelos VLM suportados) | **Sim** (VLMs em endpoints serverless/inference) | **Parcial** (LLaVA/Ollama, qualidade depende do hardware) | OpenRouter free VLMs | Zero a baixo | Média |
| Audio → text (STT) | **Sim** (Whisper API) | **Parcial** (ASR modelos, limites variam) | **Sim** (whisper.cpp/faster-whisper) | Replicate free credits ocasionais | Zero | Baixa/Média |
| Text → image | **Não** (Groq não é foco primário de image gen) | **Sim** (diffusers endpoints, nem sempre estável no free) | **Parcial** (Stable Diffusion local; pesado para Orange Pi) | Fal.ai/Replicate (normalmente pago após créditos) | Baixo/variável | Média/Alta |
| Image → image | **Não nativo** | **Sim** (diffusers img2img/instruct-pix2pix, com limites) | **Parcial** (ComfyUI/SD local; pesado) | APIs de SD com créditos | Baixo/variável | Alta |
| Video → text | **Parcial** (normalmente via pipeline, não “upload vídeo direto” universal) | **Parcial** (alguns modelos de vídeo, limites severos) | **Sim** via pipeline (ffmpeg + whisper + amostragem de frames + VLM) | OpenRouter/free VLM ocasional | Zero a baixo | Média |

### 2.1 Conclusão objetiva da matriz

1. **Chat** e **STT** são as vitórias mais fáceis para custo quase zero (Groq + fallback local).
2. **Image generation/edit** são os pontos mais difíceis de manter 100% gratuitos com estabilidade alta.
3. **Video → text** deve virar pipeline híbrido (áudio local + visão opcional remota/local), em vez de depender de um único endpoint multimodal remoto.

---

## 3) Alternativas gratuitas recomendadas por capacidade

## 3.1 Chat texto

Recomendação principal:
- **Primário: Groq** (latência excelente, free tier útil para produção leve).
- **Fallback 1: local Ollama/llama.cpp** com modelo pequeno quantizado (8B/4B) para contingência.
- **Fallback 2: HF Inference** para baixa prioridade.

## 3.2 Speech-to-text (audio → text)

Recomendação principal:
- **Primário: Groq Whisper API** (rápido, integração simples).
- **Fallback local: whisper.cpp / faster-whisper** (offline, custo zero recorrente).

Observação Orange Pi:
- STT local em CPU é viável para clipes curtos e/ou processamento assíncrono.

## 3.3 Image understanding (image → text)

Recomendação principal:
- **Primário: Groq Vision** quando disponível para o modelo escolhido.
- **Fallback: HF VLM**.
- **Fallback local: LLaVA/Ollama** apenas para baixa carga e aceitando menor qualidade/latência.

## 3.4 Text → image

Recomendação principal (custo zero preferencial):
- **Primário: Hugging Face Inference (modelos diffusers)**.
- **Fallback remoto free**: outro endpoint com créditos free estáveis (quando existir).
- **Fallback local**: SD/ComfyUI **somente fora do Orange Pi** (máquina com GPU dedicada).

## 3.5 Image → image

Recomendação principal:
- **Primário: HF Inference img2img**.
- **Fallback local**: ComfyUI/SD em host com GPU (não no Orange Pi).

## 3.6 Video → text

Pipeline recomendado gratuito:
1. Extrair áudio com ffmpeg.
2. STT (Groq Whisper ou local whisper.cpp).
3. Opcional: amostrar frames (1 frame a cada N segundos).
4. Rodar image → text nos frames (Groq Vision/HF/local VLM).
5. Fundir transcript + descrições visuais em um resumo final (chat).

---

## 4) Viabilidade no hardware embarcado (Orange Pi Zero 3)

### 4.1 O que é viável localmente

- **Orquestração de pipeline** (ffmpeg, split de tarefas, filas): viável.
- **STT local com whisper.cpp** (modelos pequenos): viável com latência moderada.
- **LLM local pequeno quantizado** (para fallback simples): viável, mas qualidade limitada.

### 4.2 O que é limítrofe/inviável no Orange Pi

- **Text → image e image → image local com SD/ComfyUI**: na prática, inviável para experiência responsiva sem GPU robusta.
- **VLMs maiores (vision local de boa qualidade)**: tipicamente pesados para RAM/CPU de SBC.

### 4.3 Decisão prática de arquitetura

- **Manter remoto**: chat principal, visão principal, image generation/edit.
- **Local obrigatório como fallback**: STT (whisper.cpp) e chat pequeno (Ollama/llama.cpp) para resiliência offline.

---

## 5) Arquitetura ideal focada em custo zero

## 5.1 Mapeamento alvo

- **Chat** → Groq (fallback local pequeno).
- **Speech-to-text** → Groq Whisper (fallback whisper.cpp).
- **Image understanding** → Groq Vision (fallback HF).
- **Text → image** → HF Inference (fallback outro free tier; pago apenas quando necessário).
- **Image → image** → HF Inference / ComfyUI remoto com GPU.
- **Video → text** → pipeline desacoplado (áudio + frames + fusão).

## 5.2 Pipeline detalhado de vídeo

1. `POST /api/analyze-video` recebe arquivo.
2. Persistir arquivo local (`/input-videos`) para rastreabilidade.
3. Executar:
   - `ffmpeg` extrai trilha de áudio mono 16k.
   - STT provider (`GroqSpeechProvider` -> fallback `LocalWhisperProvider`).
4. Em paralelo (opcional):
   - extrair frames periódicos;
   - enviar cada frame para `VisionProvider`;
   - reduzir descrições em um sumário visual curto.
5. Montar prompt final:
   - transcript + sumário visual + pergunta do usuário.
6. Enviar para `ChatProvider` para resposta final contextualizada.

Vantagem: evita depender de “upload de vídeo multimodal” de um único vendor.

---

## 6) Camada simples de providers (mínima)

Objetivo: trocar provider sem reescrever rotas.

### 6.1 Interfaces propostas

- `ChatProvider.generate(messages, settings) -> ChatResult`
- `VisionProvider.describe(image, prompt, settings) -> VisionResult`
- `SpeechProvider.transcribe(audio, settings) -> SpeechResult`
- `ImageGenProvider.generate(prompt, settings) -> ImageResult`
- `ImageEditProvider.edit(image, prompt, settings) -> ImageResult`
- `VideoUnderstandingProvider.analyze(video, prompt, settings) -> VideoResult`

### 6.2 Implementação mínima sugerida

- Começar por **3 providers concretos**:
  - `GroqChatProvider`, `GroqSpeechProvider`, `GroqVisionProvider`.
  - `HFImageGenProvider`, `HFImageEditProvider`.
  - `LocalWhisperProvider` (fallback).
- Um `ProviderRegistry` simples com prioridade por capacidade:
  - `primary`, `secondary`, `local_fallback`.
- Roteamento por capability, sem meta-framework pesado.

### 6.3 Mudanças de schema/config (sem implementar agora)

Trocar campos específicos (`openrouter_api_key`) por chaves por provider:
- `groq_api_key`
- `huggingface_api_key`
- `provider_defaults` (modelos por capacidade)

Manter compatibilidade retroativa por migração gradual.

---

## 7) Ranking de providers por custo (foco no cenário deste projeto)

> Observação: limites de free tier mudam com frequência; validar periodicamente em produção.

| Provider | Capacidades mais úteis aqui | Free tier | Limite típico | Latência | Qualidade | Estabilidade operacional |
|---|---|---|---|---|---|---|
| **Groq** | Chat, vision, STT | Sim | Moderado (quota por conta) | Muito baixa | Alta para chat/STT | Boa |
| **Hugging Face Inference** | Text→image, image→image, vision, chat (backup) | Sim | Variável por modelo/carga | Média/alta | Variável por modelo | Média |
| **Local (whisper.cpp + llama.cpp/Ollama)** | STT fallback, chat fallback | Sim (100% local) | Limitado por hardware | Alta (CPU) | Média/baixa em modelos pequenos | Muito alta (sem dependência externa) |
| **OpenRouter (somente free models)** | Multimodal agregada | Parcial | Pode oscilar com disponibilidade/rate limits | Média | Variável | Média/baixa (para seu cenário atual) |
| **Outros com créditos free (Replicate/Fal etc.)** | Imagem/vídeo específicos | Parcial | Créditos iniciais/limitados | Média | Alta (modelos de ponta) | Média (risco de custo ao escalar) |

Ranking recomendado por custo total e simplicidade:
1. **Groq + Local fallback**
2. **Hugging Face Inference (somente para imagem)**
3. **OpenRouter apenas como fallback terciário**

---

## 8) Plano de migração incremental (sem quebrar produção)

## Fase 0 — Observabilidade e baseline

- Medir volume por capacidade (chat, imagem, vídeo).
- Registrar falhas por provider e custo por requisição.

## Fase 1 — Chat e STT fora do OpenRouter

- Introduzir `ChatProvider` + `SpeechProvider` com Groq como primário.
- Adicionar fallback local (mock -> local real).
- Manter OpenRouter apenas para rotas legadas enquanto estabiliza.

## Fase 2 — Vision e vídeo por pipeline

- Criar endpoint `POST /api/analyze-image` (image → text).
- Refatorar `analyze-video` para pipeline (ffmpeg + STT + vision opcional + chat).

## Fase 3 — Imagem (gen/edit) em HF

- Substituir dependência de `chat/completions` para image gen/edit por provider dedicado HF.
- Cachear resultados e limitar resolução para conter custo/latência.

## Fase 4 — Desacoplamento final

- Renomear campos de settings para `provider-agnostic`.
- Descontinuar `openrouter_api_key` do frontend e backend (com migração de dados).

---

## 9) Estimativa de custo (alvo: zero)

Cenário alvo recomendado:
- Chat: Groq free.
- STT: Groq free + whisper.cpp local fallback.
- Vision: Groq free (fallback HF/local).
- Text/image gen-edit: HF free quando disponível, com limitação de uso.
- Video→text: pipeline com forte componente local.

Estimativa qualitativa:
- **Operação de baixo volume**: custo próximo de **zero**.
- **Picos de uso de imagem/vídeo**: possível necessidade de rate limiting/filas para não estourar free tier.
- **Quando não for possível manter grátis com qualidade aceitável**:
  - text→image e image→image em escala contínua;
  - workloads de vídeo com alta frequência e baixa latência.

Nesses casos, definir política explícita:
1. degradar qualidade/resolução,
2. enfileirar,
3. só então ativar provider pago.

---

## 10) Próximos passos sugeridos (ainda sem implementar)

1. Aprovar a estratégia `Groq + HF + fallback local`.
2. Definir modelos-alvo por capacidade (1 primário + 1 fallback).
3. Planejar migração de settings para configuração por provider.
4. Executar POC do pipeline de vídeo desacoplado (áudio + frames).
5. Só depois iniciar alterações de código em etapas pequenas e reversíveis.

---

## 11) Status de implementação incremental (update)

Implementado parcialmente nesta iteração:
- Camada mínima de providers (`llm/app/providers/*`) com registry por capability.
- Chat com provider configurável (`groq` primário, `openrouter` fallback).
- STT com Groq e opção local via whisper.cpp.
- Endpoint de image understanding (`POST /api/analyze-image`).
- Migração progressiva de text->image para provider dedicado (`hf`) com compatibilidade OpenRouter.
- `image->image` sob feature flag (`image_edit_enabled`).
- `video->text` com modo `pipeline` opcional, preservando modo `legacy`.

## Atualização de implementação

- Chat multi-provider ativo: `groq`, `openrouter`, `cloudflare`, `together`, `deepinfra` com fallback primário/secundário.
- Vision multi-provider ativo: `groq`, `openrouter`, `cloudflare`, `together`, `deepinfra` com fallback opcional.
- Speech: `groq` com fallback local `whisper.cpp` quando configurado.
- Image generation: `openrouter`, `hf`, `cloudflare`, `together`, `deepinfra` com fallback opcional.
- Image edit segue conservador: `openrouter` legado e `hf`.
