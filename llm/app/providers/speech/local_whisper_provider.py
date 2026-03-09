from __future__ import annotations

import subprocess
from pathlib import Path

from ..base import SpeechResult


class LocalWhisperProvider:
    def transcribe(self, audio_path: str, options: dict) -> SpeechResult:
        binary = Path(options.get("whisper_cpp_binary_path", "")).expanduser()
        model = Path(options.get("whisper_cpp_model_path", "")).expanduser()
        if not binary.exists():
            raise ValueError("whisper.cpp binary não encontrado. Configure whisper_cpp_binary_path")
        if not model.exists():
            raise ValueError("Modelo whisper.cpp não encontrado. Configure whisper_cpp_model_path")

        cmd = [str(binary), "-m", str(model), "-f", audio_path, "-otxt", "-of", audio_path]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise ValueError(f"Falha no whisper.cpp: {proc.stderr.strip() or proc.stdout.strip()}")

        output_txt = Path(f"{audio_path}.txt")
        if not output_txt.exists():
            raise ValueError("whisper.cpp executou, mas não gerou arquivo de transcrição")
        text = output_txt.read_text(encoding="utf-8").strip()
        return SpeechResult(text=text, model_used="local-whisper.cpp")
