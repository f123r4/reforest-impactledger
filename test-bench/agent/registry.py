"""Wrappers sobre ReforestVault.sol, TreeNFT.sol e MockUSDC.sol.

Cada client carrega o ABI do artifact compilado pelo Foundry (out/...) e expõe
métodos de leitura/escrita para a demo não fazer encoding manual de transação.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from eth_account.signers.local import LocalAccount

from agent.chain import ChainClient, ContractHandle
from agent.ndvi_oracle import Milestone


_VAULT_ARTIFACT = "out/ReforestVault.sol/ReforestVault.json"
_NFT_ARTIFACT   = "out/TreeNFT.sol/TreeNFT.json"
_USDC_ARTIFACT  = "out/MockUSDC.sol/MockUSDC.json"


@dataclass(frozen=True)
class ProjectView:
    planter: str
    species: str
    planned_trees: int
    budget_total: int
    budget_raised: int
    budget_released: int
    planted_at: int


class ReforestVaultClient:
    def __init__(
        self,
        chain: ChainClient,
        contract_address: str,
        signer: LocalAccount,
        artifact_root: Path,
    ):
        self._handle: ContractHandle = chain.load_contract(
            address=contract_address,
            abi_artifact_path=artifact_root / _VAULT_ARTIFACT,
            signer=signer,
        )

    # ----- escrita -----
    def set_oracle(self, addr: str) -> None:
        self._handle.send("setOracle", addr)

    def create_project(
        self,
        planter: str,
        geo_hash: bytes,
        species: str,
        gps_coords: str,
        planned_trees: int,
        budget_total: int,
    ) -> int:
        receipt = self._handle.send(
            "createProject",
            planter,
            geo_hash,
            species,
            gps_coords,
            planned_trees,
            budget_total,
        )
        events = self._handle.contract.events.ProjectCreated().process_receipt(receipt)  # type: ignore[arg-type]
        return int(events[0]["args"]["projectId"])

    def donate(self, project_id: int, amount: int, mint_nft: bool) -> int:
        receipt = self._handle.send("donate", project_id, amount, mint_nft)
        events = self._handle.contract.events.Donated().process_receipt(receipt)  # type: ignore[arg-type]
        if events:
            return int(events[0]["args"]["nftTokenId"])
        return 0

    def declare_planted(self, project_id: int) -> None:
        self._handle.send("declarePlanted", project_id)

    def report_milestone(
        self,
        project_id: int,
        milestone: Milestone,
        survival_bps: int,
        data_source_hash: bytes = b"\x00" * 32,
    ) -> None:
        self._handle.send("reportMilestone", project_id, int(milestone), survival_bps, data_source_hash)

    def refund(self, project_id: int) -> None:
        self._handle.send("refund", project_id)

    # ----- leitura -----
    def get_project(self, project_id: int) -> ProjectView:
        raw = self._handle.call("projects", project_id)
        # struct: planter(0), geoHash(1), species(2), gpsCoords(3),
        #         plannedTrees(4), budgetTotal(5), budgetRaised(6),
        #         budgetReleased(7), plantedAt(8), exists(9)
        return ProjectView(
            planter=str(raw[0]),
            species=str(raw[2]),
            planned_trees=int(raw[4]),
            budget_total=int(raw[5]),
            budget_raised=int(raw[6]),
            budget_released=int(raw[7]),
            planted_at=int(raw[8]),
        )

    def is_milestone_ready(self, project_id: int, milestone: Milestone) -> bool:
        return bool(self._handle.call("isMilestoneReady", project_id, int(milestone)))

    @property
    def address(self) -> str:
        return self._handle.contract.address


class TreeNftClient:
    def __init__(
        self,
        chain: ChainClient,
        contract_address: str,
        signer: LocalAccount,
        artifact_root: Path,
    ):
        self._handle: ContractHandle = chain.load_contract(
            address=contract_address,
            abi_artifact_path=artifact_root / _NFT_ARTIFACT,
            signer=signer,
        )

    def set_minter(self, addr: str) -> None:
        self._handle.send("setMinter", addr)

    def balance_of(self, addr: str) -> int:
        return int(self._handle.call("balanceOf", addr))

    @property
    def address(self) -> str:
        return self._handle.contract.address


class UsdcClient:
    """Wrapper sobre o MockUSDC — mint/approve/saldo para a demo local."""

    def __init__(
        self,
        chain: ChainClient,
        contract_address: str,
        signer: LocalAccount,
        artifact_root: Path,
    ):
        self._handle: ContractHandle = chain.load_contract(
            address=contract_address,
            abi_artifact_path=artifact_root / _USDC_ARTIFACT,
            signer=signer,
        )

    def balance_of(self, addr: str) -> int:
        return int(self._handle.call("balanceOf", addr))

    def mint(self, to: str, amount: int) -> None:
        self._handle.send("mint", to, amount)

    def approve(self, spender: str, amount: int) -> None:
        self._handle.send("approve", spender, amount)
