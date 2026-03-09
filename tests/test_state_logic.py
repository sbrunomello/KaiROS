from apps.bot.runtime.settings import RuntimeSettingsStore, VisionRuntimeSettings
from apps.bot.state import SharedState


def test_runtime_settings_update_infer_n():
    store = RuntimeSettingsStore(VisionRuntimeSettings(infer_every_n_frames=1))
    store.update(infer_every_n_frames=5)
    assert store.snapshot().infer_every_n_frames == 5


def test_shared_state_exposes_runtime_settings():
    store = RuntimeSettingsStore(VisionRuntimeSettings(target_class="all"))
    state = SharedState(jpeg_quality=50, show_mask=True, runtime_settings=store)
    assert state.get_runtime_settings_snapshot().target_class == "all"
