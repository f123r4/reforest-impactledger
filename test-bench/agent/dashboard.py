"""Dashboard terminal de impacto do ReForest+.

Exibe um painel visual com o estado atual dos projetos de reflorestamento
registrados on-chain, incluindo estimativas de impacto ambiental.
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from agent import load_addresses, load_config
from agent.chain import ChainClient
from agent.ndvi_oracle import Milestone
from agent.registry import ReforestVaultClient

# Estimativas de impacto por espécie (simplificado)
_CO2_T_POR_ARVORE_ANO = {
    "Ipê-amarelo (Handroanthus albus)": 0.05,
    "Ipe-amarelo": 0.05,
    "Pequi (Caryocar brasiliense)": 0.03,
    "Pequi": 0.03,
}
_CO2_DEFAULT = 0.04  # fallback genérico
_AGUA_L_POR_ARVORE_DIA = 300

_MILESTONE_LABELS = {
    Milestone.M0:  ("M0  — Plantio",    0),
    Milestone.M6:  ("M6  — 6 meses",  180),
    Milestone.M12: ("M12 — 12 meses", 365),
    Milestone.M36: ("M36 — 36 meses", 1095),
}
_STATUS_SYMBOL = {0: "⏳", 1: "✅", 2: "❌"}

app = typer.Typer(add_completion=False, help="ReForest+ — painel de impacto")


@app.command()
def main(use_local: bool = typer.Option(True, "--local/--remote")):
    console = Console()
    console.print()
    console.rule("[bold green]ReForest+ ImpactLedger — Painel de Impacto")
    console.print("[dim]Dados lidos diretamente dos contratos on-chain[/dim]\n")

    config = load_config(prefer_local=use_local)
    chain = ChainClient(config)
    addrs = load_addresses(config.addresses_path).get(str(config.chain_id), {})
    vault_addr = addrs.get("ReforestVault")
    if not vault_addr:
        console.print("[red]ReforestVault não encontrado em addresses.json. Rode make deploy primeiro.[/red]")
        raise typer.Exit(1)

    deployer = chain.account_from_key(config.deployer_private_key)
    vault = ReforestVaultClient(chain, vault_addr, deployer, config.repo_root)

    next_id = int(vault._handle.call("nextProjectId"))
    project_ids = list(range(1, next_id))

    if not project_ids:
        console.print("[yellow]Nenhum projeto registrado ainda. Rode make demo para criar projetos de exemplo.[/yellow]")
        return

    total_trees = 0
    total_raised = 0
    total_released = 0
    total_co2 = 0.0
    total_agua_kl = 0.0

    for pid in project_ids:
        try:
            proj = vault.get_project(pid)
        except Exception:
            continue

        total_trees += proj.planned_trees
        total_raised += proj.budget_raised
        total_released += proj.budget_released
        co2_rate = _CO2_T_POR_ARVORE_ANO.get(proj.species, _CO2_DEFAULT)
        total_co2 += proj.planned_trees * co2_rate
        total_agua_kl += proj.planned_trees * _AGUA_L_POR_ARVORE_DIA * 365 / 1_000

        milestone_line = ""
        for ms, (label, _) in _MILESTONE_LABELS.items():
            status_int = int(vault._handle.call("milestoneStatus", pid, int(ms)))
            sym = _STATUS_SYMBOL[status_int]
            milestone_line += f"  {sym} {label}"

        planted_info = (
            f"Plantado em bloco {proj.planted_at}" if proj.planted_at > 0
            else "Aguardando declaração de plantio"
        )

        panel_content = (
            f"[bold]Espécie:[/bold] {proj.species}\n"
            f"[bold]Plantador:[/bold] {proj.planter[:10]}...{proj.planter[-6:]}\n"
            f"[bold]Árvores planejadas:[/bold] {proj.planned_trees:,}\n"
            f"[bold]Orçamento:[/bold] {proj.budget_total/1e6:.0f} USDC meta | "
            f"{proj.budget_raised/1e6:.2f} USDC arrecadado | "
            f"{proj.budget_released/1e6:.2f} USDC liberado ao plantador\n"
            f"[bold]Status do plantio:[/bold] {planted_info}\n"
            f"[bold]Milestones:[/bold]{milestone_line}\n"
            f"[bold]CO₂ estimado:[/bold] ~{proj.planned_trees * co2_rate:.1f} t/ano\n"
            f"[bold]Água retida:[/bold] ~{proj.planned_trees * _AGUA_L_POR_ARVORE_DIA * 365 / 1_000:.0f} kL/ano"
        )

        border_color = "green" if proj.budget_released > 0 else "yellow"
        console.print(Panel(
            panel_content,
            title=f"[bold]Projeto #{pid}",
            border_style=border_color,
            expand=True,
        ))
        console.print()

    summary = Table(title="Totais Consolidados", box=box.ROUNDED)
    summary.add_column("Métrica", style="cyan")
    summary.add_column("Valor", justify="right", style="bold")
    summary.add_row("Projetos registrados", str(len(project_ids)))
    summary.add_row("Total de árvores planejadas", f"{total_trees:,}")
    summary.add_row("USDC arrecadado", f"{total_raised/1e6:.2f}")
    summary.add_row("USDC liberado aos plantadores", f"{total_released/1e6:.2f}")
    summary.add_row("CO₂ sequestrado (estimativa)", f"~{total_co2:.1f} t/ano")
    summary.add_row("Água retida (estimativa)", f"~{total_agua_kl:.0f} kL/ano")
    console.print(summary)

    network = "Anvil local (31337)" if use_local else "Base Sepolia (84532)"
    console.print(f"\n[dim]Rede: {network} | Vault: {vault_addr}[/dim]")
    console.print("[dim]Dados auditáveis em tempo real via oracle Sentinel-2/NDVI.[/dim]\n")


if __name__ == "__main__":
    app()
