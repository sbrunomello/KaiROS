# Provider migration (incremental)

Este documento descreve a migração incremental de OpenRouter para uma arquitetura multi-provider com foco em custo.

## Implementado nesta etapa

- Camada de providers em `llm/app/providers/`:
  - chat: Groq + OpenRouter (legado)
  - speech: Groq + whisper.cpp local
  - vision: Groq + OpenRouter (configurável)
  - image generation: Hugging Face + OpenRouter (legado)
  - image edit: Hugging Face (feature flag) + OpenRouter (legado)
- `ProviderRegistry` para resolução simples por capability.
- Chat agora usa seleção por `chat_provider` com fallback opcional `chat_fallback_provider`.
- Novo endpoint `POST /api/transcribe-audio`.
- Novo endpoint `POST /api/analyze-image`.
- `video_analysis_mode` com suporte a `pipeline` (ffmpeg + speech + vision opcional + chat), mantendo `legacy`.

## Configuração principal

- `chat_provider=groq|openrouter`
- `chat_fallback_provider=openrouter|groq|""`
- `groq_api_key`
- `speech_provider=groq|local`
- `speech_model_name`
- `whisper_cpp_binary_path`
- `whisper_cpp_model_path`
- `vision_provider=groq|openrouter`
- `vision_model_name`
- `image_gen_provider=openrouter|hf`
- `openrouter_default_image_model`
- `hf_default_image_model`
- `huggingface_api_key`
- `image_edit_enabled=true|false`
- `video_analysis_mode=legacy|pipeline`
- `video_enable_vision=true|false`
- `video_frame_sample_seconds`
- `ffmpeg_binary_path`

## Compatibilidade

- OpenRouter permanece suportado no chat (fallback) e fluxo legado de vídeo.
- Campos OpenRouter foram mantidos para compatibilidade retroativa.

## Política de retry/fallback de chat

- O chat usa fallback entre providers (primário/fallback configuráveis).
- Não há retry automático por provider nesta etapa para manter o comportamento simples e previsível.
