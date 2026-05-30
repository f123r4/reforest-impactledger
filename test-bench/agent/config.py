"""Carregamento de configuração a partir do .env.

A premissa é: o agente lê o ambiente UMA vez no boot, valida tipos, e a partir
daí trabalha com um objeto imutável. Isso evita "magic getenv()" espalhado pelo
código, que é fonte clássica de bug em produção quando uma variável muda de nome.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


# A raiz do projeto é resolvida a partir deste arquivo (agent/config.py → ../).
# Assim dá pra rodar `python -m agent.demo` de qualquer cwd sem quebrar os caminhos.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_ENV_PATH = _REPO_ROOT / ".env"


@dataclass(frozen=True)
class AgentConfig:
    """Configuração do agente, carregada do .env e tratada como imutável."""

    rpc_url: str
    chain_id: int
    deployer_private_key: str
    addresses_path: Path
    repo_root: Path

    @property
    def is_local(self) -> bool:
        """True quando estamos rodando contra o Anvil (decisões de UX dependem disso)."""
        return self.chain_id == 31_337


def load_config(*, prefer_local: bool = False) -> AgentConfig:
    """Lê o .env e devolve um AgentConfig validado.

    Args:
        prefer_local: se True, prioriza ANVIL_RPC_URL sobre BASE_SEPOLIA_RPC_URL.
            É o que a demo usa por padrão para rodar local.
    """
    if not _ENV_PATH.exists():
        raise RuntimeError(
            f".env não encontrado em {_ENV_PATH}. "
            "Copie .env.example para .env e preencha as variáveis (ou rode `make setup`)."
        )
    load_dotenv(_ENV_PATH, override=False)

    if prefer_local:
        rpc_url = os.environ.get("ANVIL_RPC_URL", "http://127.0.0.1:8545")
        chain_id = int(os.environ.get("ANVIL_CHAIN_ID", "31337"))
    else:
        rpc_url = _require_env("BASE_SEPOLIA_RPC_URL")
        chain_id = int(os.environ.get("BASE_SEPOLIA_CHAIN_ID", "84532"))

    deployer_pk = _require_env("DEPLOYER_PRIVATE_KEY")
    if not deployer_pk.startswith("0x") or len(deployer_pk) != 66:
        raise ValueError(
            "DEPLOYER_PRIVATE_KEY deve ser uma chave hex de 32 bytes prefixada com 0x."
        )

    return AgentConfig(
        rpc_url=rpc_url,
        chain_id=chain_id,
        deployer_private_key=deployer_pk,
        addresses_path=_REPO_ROOT / "deploy" / "addresses.json",
        repo_root=_REPO_ROOT,
    )


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Variável de ambiente obrigatória ausente: {name}")
    return value
