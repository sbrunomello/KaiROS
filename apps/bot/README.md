# KaiROS Bot Runtime V1 (YOLO Nano Segmentation)

## Arquitetura da pipeline de visão

A runtime agora usa segmentação por instância com **YOLO nano da Ultralytics** (`yolo11n-seg.pt`) como padrão obrigatório.

### Módulos principais
- `apps/bot/detector/base.py`: interface e DTOs de detecção (classe, máscara, centróide, área etc.).
- `apps/bot/detector/yolo_nano_seg.py`: integração oficial Python Ultralytics para task `segment`.
- `apps/bot/tracking_runtime/target_selector.py`: seleção de alvo por classe (`all` ou classe específica).
- `apps/bot/tracking_runtime/temporal_tracker.py`: tracking temporal leve entre inferências.
- `apps/bot/render/mask_overlay.py`: overlay semitransparente da máscara (saída visual principal).
- `apps/bot/runtime/settings.py`: runtime settings mutáveis sem restart.
- `apps/bot/telemetry/pipeline_metrics.py`: métricas online + agregados (`avg/p50/p95`).
- `apps/bot/web.py`: endpoints e painel frontend para operação e benchmark.

## Decisão técnica

A implementação nasce padronizada em **YOLO nano segmentation** (Ultralytics) com arquitetura aberta para troca futura do arquivo do modelo.

## Configuração

Arquivo: `apps/bot/config.yaml`

Campos principais:
- `detector.enabled`
- `detector.model_path`
- `detector.conf_threshold`
- `detector.iou_threshold`
- `detector.imgsz`
- `detector.retina_masks`
- `detector.infer_every_n_frames_default`
- `detector.target_class_default`
- `render.overlay_alpha`
- `render.draw_bbox_default`
- `render.draw_mask_default`
- `render.draw_contour_default`
- `render.draw_label_default`
- `tracking.ema_alpha`
- `tracking.tracking_timeout_ms`

## Runtime settings (frontend)

Alteráveis em tempo real:
- `target_class`
- `infer_every_n_frames`
- `draw_bbox`
- `draw_mask`
- `draw_contour`
- `draw_label`
- `retina_masks`
- `conf_threshold`

## Endpoints de visão

- `GET /api/vision/classes`
- `GET /api/vision/config`
- `GET /api/vision/runtime`
- `POST /api/vision/runtime`
- `POST /api/vision/target`
- `POST /api/vision/infer_every_n_frames`
- `GET /api/vision/metrics`

## Frontend: operação/benchmark

No painel web, você pode:
1. Selecionar classe alvo (inclui `all`).
2. Definir inferência a cada N frames (`N=1,2,5,10,...`).
3. Ligar/desligar: máscara, box, contorno e label.
4. Observar métricas online para medir limite do Orange Pi.

## Interpretação das métricas

- `frame_fps`: taxa do pipeline de frames processados.
- `inference_fps`: taxa efetiva de inferências.
- `inference_ms`: latência da última inferência.
- `inference_avg_ms/p50/p95`: estabilidade e cauda de latência.
- `target_found`: alvo encontrado/perdido (`target not found` quando ausente).
- `class_confidence` e `tracking_confidence`: confiança de detecção e estabilidade temporal.
- `mask_area`: área visível da máscara (pixels).
- `infer_every_n_frames` e `current_target_class`: estado runtime atual.
