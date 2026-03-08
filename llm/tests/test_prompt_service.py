from llm.app.services.prompt_service import PromptService


def test_prompt_service_context_window():
    service = PromptService()
    history = [{'role': 'user', 'content': f'msg{i}'} for i in range(40)]
    out = service.build_messages('sys', history, 'final')
    assert out[0]['role'] == 'system'
    assert out[-1]['content'] == 'final'
    assert len(out) <= service.config.context_window_messages + 2
