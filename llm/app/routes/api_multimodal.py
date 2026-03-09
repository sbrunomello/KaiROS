from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

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
from ..services.multimodal_service import HistoryService, ModelCatalogService, VideoAnalysisService
from ..services.openrouter_client import OpenRouterClient, OpenRouterHTTPError
from ..services.settings_service import SettingsService

router = APIRouter(prefix="/api", tags=["multimodal"])


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
        maybe_file = form.get("image")
        input_file = maybe_file if isinstance(maybe_file, UploadFile) else None
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
    model: str = Form(...),
    video_file: UploadFile = File(...),
    username: str = Depends(get_username),
    db: Session = Depends(get_db),
):
    settings = SettingsService(db).get()
    if not settings.openrouter_api_key:
        raise HTTPException(status_code=400, detail="Configure a OpenRouter API key nas configurações")

    raw = await video_file.read()
    max_bytes = settings.max_video_upload_mb * 1024 * 1024
    if len(raw) > max_bytes:
        raise HTTPException(status_code=400, detail=f"Vídeo excede limite de {settings.max_video_upload_mb}MB")

    caps = ModelCatalogService().get_capabilities()
    selected_model = (settings.default_video_analysis_model or "").strip()
    if not selected_model:
        raise HTTPException(status_code=400, detail="Defina um modelo padrão de vídeo análise nas configurações.")

    model_ids = {m["id"] for m in caps["video_input_models"]}
    if selected_model not in model_ids:
        raise HTTPException(status_code=400, detail="O modelo padrão de vídeo análise não suporta análise de vídeo por input.")

    try:
        result = VideoAnalysisService().analyze(
            settings=settings,
            model=selected_model,
            prompt=prompt,
            filename=video_file.filename or "video.mp4",
            content_type=video_file.content_type or "video/mp4",
            raw_bytes=raw,
        )
    except OpenRouterHTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Falha OpenRouter ({exc.status_code}): {exc.response_text}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if settings.persist_multimodal_history:
        HistoryService(db).add(
            username=username,
            item_type="video_analysis",
            model_name=selected_model,
            prompt=prompt,
            status="ok",
            response_text=result,
            asset_url="",
            metadata_json=f"filename={video_file.filename}",
        )

    return {"status": "ok", "model": selected_model, "prompt": prompt, "result": result}


@router.get("/history/multimodal", response_model=list[MultimodalHistoryOut])
def list_multimodal_history(username: str = Depends(get_username), db: Session = Depends(get_db)):
    return HistoryService(db).list(username)


@router.post("/generate-video")
def generate_video_placeholder():
    raise HTTPException(status_code=501, detail="Geração de vídeo indisponível: recurso atual suporta análise de vídeo por input.")
