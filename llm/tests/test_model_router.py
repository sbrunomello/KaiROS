from llm.app.services.model_router import ModelRouter


def test_model_router_candidates():
    router = ModelRouter()
    router.config.fallback_models = "openrouter/auto,meta-llama/llama-3.1-8b-instruct"
    result = router.candidates("deepseek/deepseek-chat")
    assert result[0] == "deepseek/deepseek-chat"
    assert "openrouter/auto" in result
