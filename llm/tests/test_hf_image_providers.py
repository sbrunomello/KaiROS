import httpx
import pytest

from llm.app.providers.image.hf_image_edit_provider import HFImageEditProvider
from llm.app.providers.image.hf_image_gen_provider import HFImageGenProvider


def test_hf_image_gen_uses_router_endpoint(monkeypatch):
    captured = {}

    def fake_post(self, url, **kwargs):
        captured["url"] = url
        request = httpx.Request("POST", url)
        return httpx.Response(200, request=request, content=b"img", headers={"content-type": "image/png"})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    provider = HFImageGenProvider()
    result = provider.generate(
        "cat",
        {"huggingface_api_key": "hf-key", "hf_default_image_model": "stabilityai/stable-diffusion-xl-base-1.0"},
    )

    assert captured["url"] == (
        "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0"
    )
    assert result.mime_type == "image/png"


def test_hf_image_edit_uses_router_endpoint(tmp_path, monkeypatch):
    image_path = tmp_path / "input.png"
    image_path.write_bytes(b"fake-image")

    captured = {}

    def fake_post(self, url, **kwargs):
        captured["url"] = url
        request = httpx.Request("POST", url)
        return httpx.Response(200, request=request, content=b"img", headers={"content-type": "image/png"})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    provider = HFImageEditProvider()
    result = provider.edit(
        str(image_path),
        "enhance",
        {
            "image_edit_enabled": True,
            "huggingface_api_key": "hf-key",
            "image_edit_model_name": "stabilityai/stable-diffusion-xl-base-1.0",
        },
    )

    assert captured["url"] == (
        "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0"
    )
    assert result.mime_type == "image/png"


def test_hf_image_edit_410_is_mapped_to_value_error(tmp_path, monkeypatch):
    image_path = tmp_path / "input.png"
    image_path.write_bytes(b"fake-image")

    def fake_post(self, url, **kwargs):
        request = httpx.Request("POST", url)
        response = httpx.Response(410, request=request)
        raise httpx.HTTPStatusError("gone", request=request, response=response)

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    provider = HFImageEditProvider()
    with pytest.raises(ValueError, match="410 Gone"):
        provider.edit(
            str(image_path),
            "enhance",
            {
                "image_edit_enabled": True,
                "huggingface_api_key": "hf-key",
                "image_edit_model_name": "stabilityai/stable-diffusion-xl-base-1.0",
            },
        )
