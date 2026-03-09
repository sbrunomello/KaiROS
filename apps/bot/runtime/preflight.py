"""Verificações de pré-voo para falhas comuns de runtime em SBCs."""

from __future__ import annotations

import signal
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class BinaryModuleCheck:
    """Representa um módulo binário crítico para o runtime do bot."""

    name: str
    rationale: str


# Dependências importadas em subprocesso para evitar que um SIGILL derrube o processo principal.
BINARY_MODULE_CHECKS: tuple[BinaryModuleCheck, ...] = (
    BinaryModuleCheck("cv2", "captura/render de vídeo"),
    BinaryModuleCheck("numpy", "operações numéricas"),
    BinaryModuleCheck("torch", "inferência YOLO"),
    BinaryModuleCheck("ultralytics", "pipeline de detecção"),
)


class PreflightError(RuntimeError):
    """Erro específico para falha de compatibilidade em pré-voo."""


def _run_import_check(module_name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", f"import {module_name}"],
        capture_output=True,
        text=True,
        check=False,
    )


def run_binary_dependency_preflight() -> None:
    """Valida se módulos binários críticos podem ser importados com segurança."""

    for check in BINARY_MODULE_CHECKS:
        result = _run_import_check(check.name)

        if result.returncode == 0:
            continue

        if result.returncode == -signal.SIGILL:
            raise PreflightError(
                "\n".join(
                    [
                        f"Dependência '{check.name}' falhou com Illegal instruction (SIGILL).",
                        "Isso normalmente indica wheel/binário incompatível com a CPU do Orange Pi.",
                        "Ação sugerida:",
                        "  1) Ative a venv correta (.venv).",
                        "  2) Reinstale dependências com build compatível ARM64:",
                        "     pip uninstall -y torch torchvision torchaudio opencv-python opencv-contrib-python",
                        "     pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio",
                        "     pip install --no-cache-dir opencv-python-headless",
                        "  3) Se necessário, use pacotes do sistema para OpenCV (python3-opencv).",
                        f"Contexto: módulo necessário para {check.rationale}.",
                    ]
                )
            )

        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        details = stderr or stdout or "sem detalhes"
        raise PreflightError(f"Falha ao importar '{check.name}': {details}")
