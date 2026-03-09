# KaiROS LLM (subprojeto isolado)

Aplicação web multimodal em `./llm` com FastAPI + Jinja + SQLite.

## Recursos
- Abas: **Chat**, **Imagem**, **Vídeo**, **Configurações**
- Chat original preservado (histórico por usuário local)
- Geração de imagem via provider configurável (`openrouter` legado ou `hf`) em `/api/generate-image`
- Análise de vídeo com modo `legacy` (OpenRouter) ou `pipeline` desacoplado (`/api/analyze-video`)
- Análise de imagem via vision provider configurável (`groq` ou `openrouter`) em `/api/analyze-image`
- Speech-to-text via Groq/local whisper.cpp (`/api/transcribe-audio`)
- Catálogo dinâmico de modelos e capacidades (`/api/models/capabilities`)
- Histórico multimodal (`/api/history/multimodal`)
- Configurações avançadas (modelos padrão, timeout, limite upload, persistência)

## Pesquisa oficial utilizada (OpenRouter)
Foram consultadas fontes oficiais antes da implementação:
- API Reference de Chat Completions (endpoint `/api/v1/chat/completions`)
- Models API (`/api/v1/models`) para descoberta de capacidades por `architecture.input_modalities` e `architecture.output_modalities`
- Documentação oficial de multimodal, image generation e video inputs no portal OpenRouter

### Capacidades confirmadas
- **Image generation**: suportada para modelos com `output_modalities` contendo `image`.
- **Video analysis (input)**: suportada para modelos com `input_modalities` contendo `video`, enviando conteúdo multimodal com `video_url` (ex.: data URL base64).
- **Video generation output**: **não habilitado** nesta entrega por ausência de contrato oficial implementável estável no fluxo atual deste projeto (endpoint/payload/retorno/polling com garantia).

## Uso das novas abas
1. Abra `/`.
2. Em **Configurações**, informe API key e modelos padrão.
3. Clique em **Atualizar catálogo de modelos** para carregar capacidades reais.
4. Em **Imagem**, escolha modelo compatível e clique **Gerar**.
5. Em **Vídeo**, selecione arquivo + prompt e clique **Analisar**.

## Endpoints internos
- `GET /api/models`
- `GET /api/models/capabilities`
- `POST /api/generate-image`
- `POST /api/analyze-video`
- `POST /api/generate-video` (placeholder com 501)
- `GET /api/history/multimodal`

## Limitações atuais
- Geração de vídeo está explícita como **experimental/indisponível** até suporte oficial utilizável.
- Upload de vídeo limitado por configuração (`max_video_upload_mb`).

## Testes
```bash
python -m pytest -q llm/tests
```

## Relatório técnico (curto)
- **Causa raiz do 404**: envio de payload/modelo incompatível para image generation no endpoint de chat completions, com seleção indevida de modelos text-only na UI/validação.
- **Modelos que realmente suportam imagem**: apenas os retornados pela Models API com `architecture.output_modalities` contendo `image`.
- **Modelos que realmente suportam vídeo input**: apenas os retornados pela Models API com `architecture.input_modalities` contendo `video`.
- **Correções aplicadas**: filtro estrito por capabilities oficiais, validação de compatibilidade antes da chamada, fallback só para imagem gratuita real, e logs estruturados de erro HTTP com status/url/payload sanitizado/body.

## Migração de providers

Veja `docs/provider-migration.md` para o plano incremental e novas configurações.

## Comportamento de fallback/retry

- Chat usa **fallback entre providers** (primário + fallback configurável).
- Não há retry automático por provider nesta etapa; o comportamento é tentativa no provider primário e fallback entre providers quando aplicável.
