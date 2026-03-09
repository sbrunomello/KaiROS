from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_username
from ..schemas import (
    ImageGenerationIn,
    ImageGenerationOut,
    ModelCapabilitiesOut,
    MultimodalHistoryOut,
    VideoAnalysisOut,
)
from ..services.multimodal_service import HistoryService, ImageGenerationService, ModelCatalogService, VideoAnalysisService
from ..services.openrouter_client import OpenRouterHTTPError
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
def generate_image(payload: ImageGenerationIn, username: str = Depends(get_username), db: Session = Depends(get_db)):
    settings = SettingsService(db).get()
    if not settings.openrouter_api_key:
        raise HTTPException(status_code=400, detail="Configure a OpenRouter API key nas configurações")

    caps = ModelCatalogService().get_capabilities()
    # A geração de imagem deve usar exclusivamente o modelo definido nas configurações.
    selected_model = (settings.default_image_model or "").strip()
    if not selected_model:
        raise HTTPException(status_code=400, detail="Defina um modelo padrão de imagem nas configurações.")

    model_ids = {m["id"] for m in caps["image_models"]}
    if selected_model not in model_ids:
        raise HTTPException(status_code=400, detail="O modelo selecionado não suporta geração de imagem.")

    try:
        result = ImageGenerationService().generate(settings=settings, model=selected_model, prompt=payload.prompt)
    except OpenRouterHTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Falha OpenRouter ({exc.status_code}): {exc.response_text}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if settings.persist_multimodal_history:
        HistoryService(db).add(
            username=username,
            item_type="image_generation",
            model_name=selected_model,
            prompt=payload.prompt,
            status="ok",
            response_text=result["text"],
            asset_url=result["image_url"],
        )

    return {"status": "ok", "model": selected_model, "prompt": payload.prompt, **result}


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
    # A análise de vídeo deve usar exclusivamente o modelo definido nas configurações.
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
