from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile as StarletteUploadFile

from ..config import get_config
from ..db import get_db
from ..deps import get_username
from ..schemas import (
    ImageGenerationIn,
    ImageGenerationOut,
    ModelCapabilitiesOut,
    MultimodalHistoryOut,
    VideoAnalysisOut,
)
from ..services.asset_storage_service import AssetStorageService
from ..services.image_generation_service import ImageGenerationError, ImageGenerationService
from ..services.image_input_encoder import ImageInputEncoder, ImageInputEncoderError
from ..services.multimodal_service import HistoryService, ModelCatalogService
from ..services.openrouter_client import OpenRouterClient, OpenRouterHTTPError
from ..services.settings_service import SettingsService
from ..services.video_analysis_service import VideoAnalysisService
from ..services.video_input_encoder import VideoInputEncoderError

router = APIRouter(prefix="/api", tags=["multimodal"])
logger = logging.getLogger(__name__)


def _extract_uploaded_image(form_data) -> UploadFile | StarletteUploadFile | None:
    maybe_file = form_data.get("image")
    if isinstance(maybe_file, (UploadFile, StarletteUploadFile)):
        return maybe_file
    if hasattr(maybe_file, "read") and hasattr(maybe_file, "filename"):
        return maybe_file
    return None


@router.get("/models")
def list_models():
    try:
        return ModelCatalogService().get_capabilities()["models"]
    except Exception:  # noqa: BLE001
        return []


@router.get("/models/capabilities", response_model=ModelCapabilitiesOut)
def model_capabilities():
    try:
        return ModelCatalogService().get_capabilities()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Falha ao obter catálogo de modelos: {exc}") from exc


@router.post("/generate-image", response_model=ImageGenerationOut)
async def generate_image(request: Request, username: str = Depends(get_username), db: Session = Depends(get_db)):
    settings = SettingsService(db).get()
    if not settings.openrouter_api_key:
        raise HTTPException(status_code=400, detail="Configure a OpenRouter API key nas configurações")

    input_file: UploadFile | None = None
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        payload = ImageGenerationIn(
            prompt=str(form.get("prompt", "")).strip(),
            model=str(form.get("model", "")).strip(),
            mode=str(form.get("mode", "text_to_image")).strip(),
        )
        input_file = _extract_uploaded_image(form)
    else:
        body = await request.json()
        payload = ImageGenerationIn(**body)

    caps = ModelCatalogService().get_capabilities()
    image_model_ids = [m["id"] for m in caps["image_models"] if m.get("id")]
    safe_fallback_models = ["bytedance-seed/seedream-4.5"]

    requested_model = (payload.model or "").strip()
    configured_model = (settings.default_image_model or "").strip()
    default_catalog_model = (caps.get("default_image_model") or "").strip()

    selected_model = requested_model or configured_model or default_catalog_model
    if image_model_ids and selected_model not in image_model_ids:
        selected_model = configured_model if configured_model in image_model_ids else default_catalog_model or image_model_ids[0]
    if not selected_model:
        selected_model = safe_fallback_models[0]

    config = get_config()
    generated_storage = AssetStorageService(base_dir=config.generated_images_dir)
    input_storage = AssetStorageService(base_dir=config.input_images_dir, public_prefix="/input-images")
    input_encoder = ImageInputEncoder()

    raw_input_image = None
    input_mime_type = None
    if payload.mode == "image_to_image":
        if not input_file:
            raise HTTPException(status_code=400, detail="Adicione uma imagem para usar o modo imagem para imagem.")
        raw_input_image = await input_file.read()
        input_mime_type = input_file.content_type or ""
        try:
            input_encoder.validate_mime_type(input_mime_type)
            input_encoder.enforce_size_limit(image_bytes=raw_input_image, max_size_mb=config.max_image_upload_mb)
        except ImageInputEncoderError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        result = ImageGenerationService(
            client=OpenRouterClient(timeout_seconds=settings.request_timeout_seconds),
            generated_storage=generated_storage,
            input_storage=input_storage,
            input_encoder=input_encoder,
        ).generate(
            settings=settings,
            model=selected_model,
            prompt=payload.prompt,
            mode=payload.mode,
            input_image_bytes=raw_input_image,
            input_image_mime_type=input_mime_type,
        )
    except OpenRouterHTTPError as exc:
        raise HTTPException(status_code=502, detail=f"OpenRouter retornou erro HTTP {exc.status_code}") from exc
    except ImageGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if settings.persist_multimodal_history:
        subtype = payload.mode
        metadata = (
            f"subtype={subtype};mime_type={result['mime_type']};size_bytes={result['size_bytes']};"
            f"input_image_url={result.get('input_image_url', '')}"
        )
        HistoryService(db).add(
            username=username,
            item_type="image_generation",
            model_name=selected_model,
            prompt=payload.prompt,
            status="ok",
            response_text=result["text"],
            asset_url=result["image_url"],
            metadata_json=metadata,
        )

    return {"status": "ok", "mode": payload.mode, "model": selected_model, "prompt": payload.prompt, **result}


@router.post("/analyze-video", response_model=VideoAnalysisOut)
async def analyze_video(
    prompt: str = Form(...),
    model: str = Form(""),
    reasoning_enabled: bool = Form(False),
    video_file: UploadFile | None = File(None),
    username: str = Depends(get_username),
    db: Session = Depends(get_db),
):
    started_at = time.perf_counter()
    settings = SettingsService(db).get()
    if not settings.openrouter_api_key:
        raise HTTPException(status_code=400, detail="Configure a OpenRouter API key nas configurações")

    if not video_file:
        raise HTTPException(status_code=400, detail="Adicione um vídeo para análise.")

    raw = await video_file.read()
    max_bytes = settings.max_video_upload_mb * 1024 * 1024
    if len(raw) > max_bytes:
        raise HTTPException(status_code=400, detail="O arquivo excede o limite permitido.")

    selected_model = (model or "").strip() or (settings.default_video_analysis_model or "").strip() or "nvidia/nemotron-nano-12b-v2-vl:free"
    if not selected_model:
        raise HTTPException(status_code=400, detail="modelo ausente")

    caps = ModelCatalogService().get_capabilities()
    model_ids = {m["id"] for m in caps["video_input_models"]}
    if model_ids and selected_model not in model_ids:
        raise HTTPException(status_code=400, detail="O modelo selecionado não suporta análise de vídeo por input.")

    content_type = (video_file.content_type or "").strip() or "video/mp4"
    config = get_config()
    video_storage = AssetStorageService(base_dir=config.input_videos_dir, public_prefix="/input-videos")

    logger.info(
        "video_analysis_start op=analyze_video model=%s reasoning_enabled=%s file_size=%s mime=%s url=%s",
        selected_model,
        reasoning_enabled,
        len(raw),
        content_type,
        "https://openrouter.ai/api/v1/chat/completions",
    )

    try:
        result = VideoAnalysisService(client=OpenRouterClient(timeout_seconds=settings.request_timeout_seconds)).analyze(
            settings=settings,
            model=selected_model,
            prompt=prompt.strip() or "Descreva o que acontece neste vídeo.",
            filename=video_file.filename or "video.mp4",
            content_type=content_type,
            raw_bytes=raw,
            reasoning_enabled=reasoning_enabled,
        )
    except VideoInputEncoderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OpenRouterHTTPError as exc:
        logger.error("video_analysis_error status_code=%s response=%s", exc.status_code, exc.response_text[:500])
        raise HTTPException(status_code=502, detail=f"OpenRouter retornou erro HTTP {exc.status_code}.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    persisted_video = video_storage.save_input_video(video_bytes=raw, mime_type=content_type, filename_prefix="input_video")

    if settings.persist_multimodal_history:
        metadata = (
            f"filename={video_file.filename or ''};mime_type={content_type};size_bytes={len(raw)};"
            f"reasoning_enabled={str(reasoning_enabled).lower()};video_url={persisted_video['public_url']};"
            f"reasoning_details={result.reasoning_details if result.reasoning_details is not None else ''}"
        )
        HistoryService(db).add(
            username=username,
            item_type="video_analysis",
            model_name=selected_model,
            prompt=prompt,
            status="ok",
            response_text=result.text,
            asset_url=str(persisted_video["public_url"]),
            metadata_json=metadata,
        )

    elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
    logger.info("video_analysis_done model=%s reasoning_enabled=%s status_code=200 latency_ms=%s", selected_model, reasoning_enabled, elapsed_ms)

    return {
        "status": "ok",
        "model": selected_model,
        "prompt": prompt,
        "result": result.text,
        "reasoning_enabled": reasoning_enabled,
    }


@router.get("/history/multimodal", response_model=list[MultimodalHistoryOut])
def list_multimodal_history(username: str = Depends(get_username), db: Session = Depends(get_db)):
    return HistoryService(db).list(username)


@router.post("/generate-video")
def generate_video_placeholder():
    raise HTTPException(status_code=501, detail="Geração de vídeo indisponível: recurso atual suporta análise de vídeo por input.")
