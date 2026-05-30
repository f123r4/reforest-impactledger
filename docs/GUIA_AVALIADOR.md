# Guia do Avaliador — ReForest+ ImpactLedger

A ideia deste guia é deixar fácil pra banca conferir que o projeto funciona de verdade. Tem três caminhos, do mais rápido (só abrir o navegador) ao mais completo (rodar a bancada de testes).

| Caminho | O que precisa | O que mostra |
|---------|---------------|--------------|
| A — Basescan | Só o navegador | Contratos verificados, eventos reais, TreeNFT on-chain |
| B — Remix | Navegador | O fluxo de impacto ao vivo, passo a passo |
| C — Bancada de testes | Foundry + Python 3.11 | Ciclo completo M0→M36 + refund em ~2 minutos |

## Caminho A — Conferir sem instalar nada

### Contratos verificados na Base Sepolia

| Contrato | Endereço | Links |
|----------|----------|-------|
| ReforestVault | `0xc445823A43c857438bCdA289e8d713DFC183B463` | [código](https://sepolia.basescan.org/address/0xc445823A43c857438bCdA289e8d713DFC183B463#code) · [eventos](https://sepolia.basescan.org/address/0xc445823A43c857438bCdA289e8d713DFC183B463#events) |
| TreeNFT | `0xDd7b07dd2684c4881Df7B1Ba450B69fbc1ddE848` | [código](https://sepolia.basescan.org/address/0xDd7b07dd2684c4881Df7B1Ba450B69fbc1ddE848#code) · [tokens](https://sepolia.basescan.org/address/0xDd7b07dd2684c4881Df7B1Ba450B69fbc1ddE848#tokentxns) |
| MockUSDC | `0x7D3f460251dd9d04481de14B04507697B2bA36d2` | [código](https://sepolia.basescan.org/address/0x7D3f460251dd9d04481de14B04507697B2bA36d2#code) |

### Os atores da demo

| Papel | Endereço |
|-------|----------|
| deployer (admin + oracle) | `0x67c65f6e06a231203bE9DaE9e97F07F740e65e68` |
| planter1 — Comunidade Quilombola Mandira | `0x7540D78112D8063Ae805C15077BEc39EDcc0bcc5` |
| planter2 — ONG Cerrado Vivo | `0x52e79B204e3254C5CA6eF83752c7692974539a14` |
| alice — Ana Beatriz (doadora com NFT) | `0x69fB0Dd6A108d7c0605b0F2c4956ED3D8FAB8da9` |
| bruno — Bruno Ramos (doador sem NFT) | `0xdcC5E8242115cc5235f360c4EB18a7e94434bbfA` |

### O que olhar no Basescan

1. No **TreeNFT**, aba *Token Transfers*: a alice recebeu um NFT com GPS e espécie gravados on-chain.
2. Nos eventos `MilestoneReported` do **ReforestVault** (aba *Events*): aparece o `survivalBps` e o `dataSourceHash` (o SHA-256 da cena Sentinel-2).
3. Dá pra recalcular o hash no PowerShell e comparar com o que está on-chain:

   ```powershell
   $s = "S2A_MSIL2A_20260401T130251_N0500_R110_T23KPQ_20260401T163512"
   $b = [System.Text.Encoding]::UTF8.GetBytes($s)
   ([System.Security.Cryptography.SHA256]::Create().ComputeHash($b) | ForEach-Object { $_.ToString("x2") }) -join ""
   ```

   O resultado bate com o `dataSourceHash` do evento M0.

## Caminho B — Rodar o fluxo no Remix

O passo a passo completo (deploy, doação, milestone aprovado e reprovado, refund) está em [`guia-remix-navegador.md`](guia-remix-navegador.md). Roda inteiro no navegador.

## Caminho C — Bancada de testes

O tooling de teste fica em `test-bench/`. Roda no PowerShell (Windows). Precisa do Foundry e do Python 3.11.

```powershell
cd test-bench
.\run.ps1 setup      # cria o .env (uma vez)
.\run.ps1 install    # cria a .venv e instala as dependências
.\run.ps1 build      # compila os contratos
.\run.ps1 test       # 15 passed; 0 failed
.\run.ps1 anvil      # sobe a blockchain local em background
.\run.ps1 deploy     # deploya MockUSDC + TreeNFT + ReforestVault
.\run.ps1 demo       # fluxo completo M0→M36 + refund
.\run.ps1 dashboard  # painel de impacto
```

No fim, os saldos batem com isto:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┓
┃ Conta                               ┃     USDC ┃ TreeNFTs ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━┩
│ Ana Beatriz (alice)                 │ 22600.00 │        1 │
│ Bruno Ramos (bruno)                 │  7000.00 │        0 │
│ Comunidade Quilombola (planter1)    │ 10000.00 │        0 │
│ ONG Cerrado Vivo (planter2)         │   400.00 │        0 │
└─────────────────────────────────────┴──────────┴──────────┘
```

## Os 15 testes (Foundry)

`.\run.ps1 test` roda todos. O que cada um valida:

| Teste | O que valida |
|-------|--------------|
| `test_createProject` | GPS + espécie + evento ProjectCreated |
| `test_donateWithNft_mintsCertificate` | NFT com metadata on-chain |
| `test_donateWithoutNft` | Saldo exato depositado |
| `test_declarePlanted_setsTimestamp` | Timestamp imutável |
| `test_milestoneM0_approved_releases10Percent` | 10% de 10.000 = 1.000 USDC exatos |
| `test_milestoneM6_rejected_doesNotRelease` | Abaixo do threshold → zero liberado |
| `test_refund_proRataAfterM36Failed` | Matemática do refund proporcional |
| `testRevert_createProject_notAdmin` | Controle de acesso funciona |
| `testRevert_createProject_zeroPlanter` | Validação de entrada |
| `testRevert_declarePlanted_notPlanter` | Só o plantador registrado |
| `testRevert_donateAboveBudget` | Orçamento protegido |
| `testRevert_milestoneByNonOracle` | Só o oracle autorizado |
| `testRevert_milestoneOutOfWindow` | Oracle não antecipa milestone |
| `testRevert_milestoneTwice` | Sem pagamento duplicado |
| `testRevert_refundBeforeM36Resolved` | Refund só depois da resolução final |

## Problemas comuns

| Problema | Solução |
|----------|---------|
| `forge: command not found` | Foundry não está no PATH; revise a instalação e abra um novo PowerShell |
| `Connection refused` na demo | Rode `.\run.ps1 anvil` antes |
| `addresses.json` vazio `{}` | Rode `.\run.ps1 deploy` antes do `.\run.ps1 demo` |
| `venv nao encontrada` | Rode `.\run.ps1 install` para criar a `.venv` |
| Script bloqueado pela policy | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
</content>
