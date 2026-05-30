"""Logging com rich. Substitui a UI no MVP — a demo toda roda no terminal.

Decisão: NÃO usamos logging.basicConfig nem o módulo logging padrão como cidadão
de primeira classe. Em vez disso, retornamos uma instância de `rich.console.Console`
porque a demo vai querer tabelas, painéis e ✓ / ✗ inline — coisas que `logging`
não oferece bem.

Para mensagens "system" (warning de erro de RPC, retry de tx) usamos o logger
nativo nivelado pela env var LOG_LEVEL.
"""

from __future__ import annotations

import logging
import os

from rich.console import Console
from rich.logging import RichHandler


_HANDLER_INSTALLED = False


def build_logger(name: str) -> tuple[Console, logging.Logger]:
    """Cria um Console rich + logger nomeado integrados.

    O console é o que você usa para qualquer "narrativa" da demo (cabeçalhos,
    tabelas, ✓ / ✗ inline). O logger é para mensagens estruturadas de sistema.
    """
    global _HANDLER_INSTALLED
    console = Console()

    if not _HANDLER_INSTALLED:
        # Instala o RichHandler uma única vez por processo. Idempotente: chamar
        # build_logger() de novo não duplica handlers (causa #1 de log duplicado).
        logging.basicConfig(
            level=os.environ.get("LOG_LEVEL", "INFO"),
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(console=console, rich_tracebacks=True, markup=True)],
        )
        _HANDLER_INSTALLED = True

    logger = logging.getLogger(name)
    return console, logger
