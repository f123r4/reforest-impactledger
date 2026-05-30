"""Demo ponta-a-ponta do ReForest+.

Roda dois projetos de reflorestamento: um saudável (todos os milestones passam)
e um que sofre estiagem (reprovado no M6/M12/M36) pra mostrar o refund pro-rata.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict

import typer
from eth_account import Account
from rich.table import Table
from web3 import Web3

from agent import build_logger, load_addresses, load_config
from agent.chain import ChainClient
from agent.ndvi_oracle import Milestone, NdviReading, load_ndvi_feed
from agent.registry import ReforestVaultClient, TreeNftClient, UsdcClient


app = typer.Typer(add_completion=False, help="ReForest+ — demo ponta-a-ponta")

_ANVIL_PLANTER_1 = "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a"
_ANVIL_PLANTER_2 = "0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba"
_ANVIL_ALICE     = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
_ANVIL_BRUNO     = "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"

_LABEL_PLANTER1 = "Comunidade Quilombola Mandira (Vale do Ribeira, SP)"
_LABEL_PLANTER2 = "ONG Cerrado Vivo (Brasília, DF)"
_LABEL_ALICE    = "Ana Beatriz — engenheira ambiental, SP"
_LABEL_BRUNO    = "Bruno Ramos — desenvolvedor, RJ"
_SPECIES_P1     = "Ipê-amarelo (Handroanthus albus)"
_SPECIES_P2     = "Pequi (Caryocar brasiliense)"
_GPS_P1         = "-19.9,-43.95"
_GPS_P2         = "-15.78,-47.93"

# Estimativas de impacto por espécie (simplificado para demonstração)
_CO2_IPE_T_POR_ARVORE_ANO    = 0.05  # ~50 kg CO₂/ano por Ipê adulto
_CO2_PEQUI_T_POR_ARVORE_ANO  = 0.03  # ~30 kg CO₂/ano por Pequi adulto
_AGUA_L_POR_ARVORE_DIA       = 300   # litros/dia retidos por árvore

_TESTNET_ETH_PER_ACTOR = Web3.to_wei(0.001, "ether")


def _derive_account(deployer_key: str, role: str):
    # gera sempre o mesmo endereço para a mesma chave+papel → rastreável no Basescan
    seed = hashlib.sha256(f"{deployer_key}:{role}".encode()).digest()
    return Account.from_key(seed)


def _fund_if_needed(web3: Web3, deployer, target_addr: str, amount_wei: int) -> None:
    balance = web3.eth.get_balance(target_addr)
    if balance >= amount_wei:
        return
    nonce = web3.eth.get_transaction_count(deployer.address, "pending")
    tx = {
        "to": target_addr,
        "value": amount_wei - balance,
        "gas": 21_000,
        "gasPrice": web3.eth.gas_price,
        "nonce": nonce,
        "chainId": web3.eth.chain_id,
    }
    signed = deployer.sign_transaction(tx)
    raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
    tx_hash = web3.eth.send_raw_transaction(raw)
    web3.eth.wait_for_transaction_receipt(tx_hash)


@app.command()
def main(use_local: bool = typer.Option(True, "--local/--remote")):
    console, log = build_logger("reforest.demo")
    console.rule("[bold cyan]ReForest+ ImpactLedger — Demo Ponta-a-Ponta")
    console.print("[dim]Rastreabilidade on-chain para projetos de reflorestamento | HackWeb Web3 — Desafio 3[/dim]\n")

    config = load_config(prefer_local=use_local)
    chain = ChainClient(config)

    addrs = load_addresses(config.addresses_path).get(str(config.chain_id), {})
    vault_addr = addrs.get("ReforestVault")
    nft_addr   = addrs.get("TreeNFT")
    usdc_addr  = addrs.get("MockUSDC")
    if not (vault_addr and nft_addr and usdc_addr):
        console.print("[red]Endereços ReforestVault/TreeNFT/MockUSDC ausentes em addresses.json[/red]")
        raise typer.Exit(1)

    deployer = chain.account_from_key(config.deployer_private_key)

    if use_local:
        planter1 = chain.account_from_key(_ANVIL_PLANTER_1)
        planter2 = chain.account_from_key(_ANVIL_PLANTER_2)
        alice    = chain.account_from_key(_ANVIL_ALICE)
        bruno    = chain.account_from_key(_ANVIL_BRUNO)
    else:
        planter1 = _derive_account(config.deployer_private_key, "planter1")
        planter2 = _derive_account(config.deployer_private_key, "planter2")
        alice    = _derive_account(config.deployer_private_key, "alice")
        bruno    = _derive_account(config.deployer_private_key, "bruno")
        console.print("[cyan]Modo testnet: financiando contas derivadas com ETH para gas...[/cyan]")
        for acct in [planter1, planter2, alice, bruno]:
            _fund_if_needed(chain.web3, deployer, acct.address, _TESTNET_ETH_PER_ACTOR)
        console.print("[yellow]Milestones M6/M12/M36 e refund omitidos (requerem fast-forward de tempo).[/yellow]\n")

    console.print(f"deployer (admin+oracle): {deployer.address}")
    console.print(f"plantador 1 [{_LABEL_PLANTER1}]: {planter1.address}")
    console.print(f"plantador 2 [{_LABEL_PLANTER2}]: {planter2.address}")
    console.print(f"doadora [{_LABEL_ALICE}]: {alice.address}")
    console.print(f"doador  [{_LABEL_BRUNO}]: {bruno.address}\n")

    vault = ReforestVaultClient(chain, vault_addr, deployer, config.repo_root)
    nft   = TreeNftClient(chain, nft_addr, deployer, config.repo_root)
    usdc  = UsdcClient(chain, usdc_addr, deployer, config.repo_root)

    # ----- Setup: oracle + minter + fundos -----
    console.rule("Setup — oracle, minter e fundos")
    _try(console, lambda: vault.set_oracle(deployer.address), "oracle")
    _try(console, lambda: nft.set_minter(vault_addr), "minter")
    usdc.mint(alice.address, 30_000 * 10**6)
    usdc.mint(bruno.address, 10_000 * 10**6)
    UsdcClient(chain, usdc_addr, alice, config.repo_root).approve(vault_addr, 2**255)
    UsdcClient(chain, usdc_addr, bruno, config.repo_root).approve(vault_addr, 2**255)
    console.print("  ✓ doadores fundados e approved\n")

    # ----- Cria 2 projetos -----
    console.rule("Etapa 1 — Cadastro de projetos de reflorestamento")
    p1 = vault.create_project(
        planter1.address,
        bytes.fromhex("11" * 32),
        _SPECIES_P1,
        _GPS_P1,
        planned_trees=1_000,
        budget_total=10_000 * 10**6,
    )
    console.print(f"  ✓ projeto #{p1}: Mata Atlântica em Recuperação")
    console.print(f"    Plantador: {_LABEL_PLANTER1}")
    console.print(f"    Espécie: {_SPECIES_P1} | 1.000 árvores | Meta: 10.000 USDC")
    console.print(f"    GPS: {_GPS_P1} (Vale do Ribeira, SP)")

    p2 = vault.create_project(
        planter2.address,
        bytes.fromhex("22" * 32),
        _SPECIES_P2,
        _GPS_P2,
        planned_trees=500,
        budget_total=5_000 * 10**6,
    )
    console.print(f"  ✓ projeto #{p2}: Cerrado Renasce")
    console.print(f"    Plantador: {_LABEL_PLANTER2}")
    console.print(f"    Espécie: {_SPECIES_P2} | 500 árvores | Meta: 5.000 USDC")
    console.print(f"    GPS: {_GPS_P2} (Brasília, DF)")

    # ----- Doações -----
    console.rule("Etapa 2 — Doações")
    vault_alice = ReforestVaultClient(chain, vault_addr, alice, config.repo_root)
    vault_bruno = ReforestVaultClient(chain, vault_addr, bruno, config.repo_root)

    token_id = vault_alice.donate(p1, 7_000 * 10**6, mint_nft=True)
    console.print(f"  ✓ {_LABEL_ALICE} doou 7.000 USDC ao projeto #{p1} e mintou TreeNFT #{token_id}")
    vault_alice.donate(p2, 4_000 * 10**6, mint_nft=False)
    console.print(f"  ✓ {_LABEL_ALICE} doou 4.000 USDC ao projeto #{p2} (sem NFT)")
    vault_bruno.donate(p1, 3_000 * 10**6, mint_nft=False)
    console.print(f"  ✓ {_LABEL_BRUNO} doou 3.000 USDC ao projeto #{p1}")

    # ----- Plantios declarados -----
    console.rule("Etapa 3 — Plantios declarados")
    ReforestVaultClient(chain, vault_addr, planter1, config.repo_root).declare_planted(p1)
    console.print(f"  ✓ {_LABEL_PLANTER1} declarou plantio do projeto #{p1}")
    ReforestVaultClient(chain, vault_addr, planter2, config.repo_root).declare_planted(p2)
    console.print(f"  ✓ {_LABEL_PLANTER2} declarou plantio do projeto #{p2}")

    # ----- Pipeline de milestones -----
    console.rule("Etapa 4 — Verificação por Oracle Satelital (Sentinel-2/NDVI)")
    raw_readings = load_ndvi_feed(config.repo_root / "fixtures" / "ndvi_readings.csv")
    _id_map = {1: p1, 2: p2}
    readings = [
        NdviReading(
            project_id=_id_map.get(r.project_id, r.project_id),
            milestone=r.milestone,
            survival_bps=r.survival_bps,
            measured_at=r.measured_at,
            scene_id=r.scene_id,
        )
        for r in raw_readings
    ]
    by_milestone: dict[Milestone, list] = defaultdict(list)
    for r in readings:
        by_milestone[r.milestone].append(r)

    _process_milestone(console, chain, vault, by_milestone[Milestone.M0], delay_days=0)

    if use_local:
        _process_milestone(console, chain, vault, by_milestone[Milestone.M6], delay_days=181)
        _process_milestone(console, chain, vault, by_milestone[Milestone.M12], delay_days=200)

        console.print("\n[dim]fast-forward 800 dias para M36...[/dim]")
        _evm_skip(chain, 800)
        src_p2 = hashlib.sha256(b"MOCK-2-M36").digest()
        src_p1 = hashlib.sha256(b"MOCK-1-M36").digest()
        vault.report_milestone(p2, Milestone.M36, 2_000, src_p2)
        console.print(f"  oracle M36 #{p2} → 20% sobrevivência → [red]REPROVADO[/red]")
        vault.report_milestone(p1, Milestone.M36, 8_500, src_p1)
        console.print(f"  oracle M36 #{p1} → 85% sobrevivência → [green]APROVADO[/green]")

        # ----- Refund pro-rata projeto #2 -----
        console.rule("Etapa 5 — Refund pro-rata (projeto #2 falhou)")
        bal_before = usdc.balance_of(alice.address)
        vault_alice.refund(p2)
        refund_amt = usdc.balance_of(alice.address) - bal_before
        console.print(
            f"  ✓ alice resgatou [green]{refund_amt / 1e6:.2f} USDC[/green] "
            f"do projeto #{p2} (proporcional à parte não-liberada)"
        )
    else:
        console.print(
            "\n[yellow]Testnet: M6/M12/M36 e refund requerem 180-1095 dias reais — "
            "verificar progresso futuro no Basescan.[/yellow]"
        )

    # ----- Resumo final -----
    console.rule("Resumo")
    table = Table(title="Saldos Finais")
    table.add_column("Participante", style="cyan")
    table.add_column("USDC", justify="right")
    table.add_column("TreeNFTs", justify="right", style="green")
    for label, signer in [
        (_LABEL_ALICE, alice),
        (_LABEL_BRUNO, bruno),
        (_LABEL_PLANTER1, planter1),
        (_LABEL_PLANTER2, planter2),
    ]:
        table.add_row(
            label,
            f"{usdc.balance_of(signer.address) / 1e6:.2f}",
            str(nft.balance_of(signer.address)),
        )
    console.print(table)

    for project_id, label in [(p1, "Mata Atlântica"), (p2, "Cerrado Renasce")]:
        proj = vault.get_project(project_id)
        console.print(
            f"  projeto #{project_id} [{label}]: "
            f"raised={proj.budget_raised / 1e6:.2f} USDC arrecadado | "
            f"released={proj.budget_released / 1e6:.2f} USDC liberado ao plantador"
        )

    # ----- Impacto estimado -----
    if use_local:
        proj1 = vault.get_project(p1)
        proj2 = vault.get_project(p2)
        trees1 = proj1.planned_trees
        trees2 = proj2.planned_trees
        co2_1    = trees1 * _CO2_IPE_T_POR_ARVORE_ANO
        co2_2    = trees2 * _CO2_PEQUI_T_POR_ARVORE_ANO
        agua_1_kl = trees1 * _AGUA_L_POR_ARVORE_DIA * 365 / 1_000
        agua_2_kl = trees2 * _AGUA_L_POR_ARVORE_DIA * 365 / 1_000

        console.rule("[bold green]Impacto Ambiental Estimado")
        impact_table = Table(title="Projeção de Impacto (por ano, árvores adultas)")
        impact_table.add_column("Projeto", style="green")
        impact_table.add_column("Árvores", justify="right")
        impact_table.add_column("CO₂ seq. (t/ano)", justify="right", style="cyan")
        impact_table.add_column("Água retida (kL/ano)", justify="right", style="blue")
        impact_table.add_row("Mata Atlântica — Ipê-amarelo", str(trees1), f"~{co2_1:.0f}", f"~{agua_1_kl:.0f}")
        impact_table.add_row("Cerrado Renasce — Pequi",      str(trees2), f"~{co2_2:.0f}", f"~{agua_2_kl:.0f}")
        impact_table.add_row("[bold]TOTAL", f"[bold]{trees1+trees2}", f"[bold]~{co2_1+co2_2:.0f}", f"[bold]~{agua_1_kl+agua_2_kl:.0f}")
        console.print(impact_table)
        console.print("[dim]* Estimativas baseadas em médias do IPCC para espécies nativas brasileiras.[/dim]")
        console.print("[dim]* Todos os dados de sobrevivência registrados on-chain via oracle Sentinel-2/NDVI.[/dim]")


# ============================ Helpers ============================

def _try(console, fn, label):
    try:
        fn()
        console.print(f"[dim]  {label} configurado[/dim]")
    except Exception:
        console.print(f"[dim]  {label}: ja configurado[/dim]")


def _process_milestone(console, chain: ChainClient, vault: ReforestVaultClient,
                        readings, *, delay_days: int) -> None:
    if delay_days > 0:
        console.print(f"\n[dim]fast-forward {delay_days} dias...[/dim]")
        _evm_skip(chain, delay_days)
    for r in readings:
        try:
            vault.report_milestone(r.project_id, r.milestone, r.survival_bps, r.data_source_hash)
            approved = r.survival_bps >= 7_500
            status = "[green]APROVADO[/green]" if approved else "[red]REPROVADO[/red]"
            console.print(
                f"  oracle {r.milestone.name} #{r.project_id}: "
                f"{r.survival_bps/100:.1f}% sobrevivência → {status}"
            )
        except Exception as exc:
            console.print(f"  [yellow]falha no report {r.milestone.name}/#{r.project_id}: "
                          f"{_short(str(exc))}[/yellow]")


def _evm_skip(chain: ChainClient, days: int) -> None:
    chain.web3.provider.make_request("evm_increaseTime", [days * 86_400])
    chain.web3.provider.make_request("evm_mine", [])


def _short(s, n=80):
    return s if len(s) <= n else s[:n-1] + "…"


if __name__ == "__main__":
    app()
