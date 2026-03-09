"""Camada de domínio para controle de servo.

Esta camada isola a aplicação dos detalhes do backend físico (arquivo, PCA9685 etc.).
Assim, o módulo de visão pode evoluir sem acoplamento ao mecanismo de atuação.
"""

from __future__ import annotations

from .servo_backend import FileServoBackend


class ServoService:
    """Serviço de alto nível para comandos de servo.

    A classe centraliza regras simples de negócio e mantém uma API estável para o restante
    do sistema, independentemente de qual backend concreto esteja em uso.
    """

    def __init__(self, backend: FileServoBackend):
        self._backend = backend

    @property
    def enabled(self) -> bool:
        return self._backend.enabled

    def center(self, angle: float) -> float:
        """Centraliza forçando escrita imediata no backend."""
        return self._backend.set_angle(angle, force=True)

    def set_angle(self, angle: float, force: bool = False) -> float:
        """Ajusta o ângulo respeitando constraints e rate-limit do backend."""
        return self._backend.set_angle(angle, force=force)
