"""Agente Python do ReForest+: cliente web3, oracle NDVI e a demo CLI.

Tudo que a demo precisa importar de forma "rasa" é re-exportado aqui para os
imports ficarem curtos (`from agent import load_config, build_logger`).
"""

from agent.chain import ChainClient, ContractHandle, load_addresses
from agent.config import AgentConfig, load_config
from agent.logging import build_logger

__all__ = [
    "AgentConfig",
    "ChainClient",
    "ContractHandle",
    "build_logger",
    "load_addresses",
    "load_config",
]
