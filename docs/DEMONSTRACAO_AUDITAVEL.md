# Demonstração Auditável — ReForest+ ImpactLedger

## Por que "auditável" importa aqui

Em reflorestamento, auditável quer dizer que qualquer pessoa de fora consegue refazer a conta de sobrevivência das árvores sem depender da palavra de quem reportou.

O oracle satelital grava o SHA-256 do scene ID da imagem Sentinel-2 dentro do evento `MilestoneReported`. Com esse hash, quem quiser pode ir no portal público da ESA Copernicus, baixar exatamente a mesma cena e recalcular o NDVI no mesmo polígono geográfico.

## Contratos publicados na Base Sepolia

| Contrato | Endereço | Código verificado |
|----------|----------|-------------------|
| ReforestVault | `0xc445823A43c857438bCdA289e8d713DFC183B463` | [Basescan](https://sepolia.basescan.org/address/0xc445823A43c857438bCdA289e8d713DFC183B463#code) |
| TreeNFT | `0xDd7b07dd2684c4881Df7B1Ba450B69fbc1ddE848` | [Basescan](https://sepolia.basescan.org/address/0xDd7b07dd2684c4881Df7B1Ba450B69fbc1ddE848#code) |
| MockUSDC | `0x7D3f460251dd9d04481de14B04507697B2bA36d2` | [Basescan](https://sepolia.basescan.org/address/0x7D3f460251dd9d04481de14B04507697B2bA36d2#code) |

## Conferindo o hash satelital

No PowerShell:

```powershell
$scene = "S2A_MSIL2A_20260401T130251_N0500_R110_T23KPQ_20260401T163512"
$bytes = [System.Text.Encoding]::UTF8.GetBytes($scene)
$hash  = [System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
($hash | ForEach-Object { $_.ToString("x2") }) -join ""
```

Em Python:

```python
import hashlib
scene_id = "S2A_MSIL2A_20260401T130251_N0500_R110_T23KPQ_20260401T163512"
print(hashlib.sha256(scene_id.encode()).hexdigest())
```

O resultado tem que bater com o `dataSourceHash` do evento `MilestoneReported` M0 do projeto #1 (aba *Events* do Basescan).

## Como recalcular o NDVI por conta própria

1. Acesse [browser.dataspace.copernicus.eu](https://browser.dataspace.copernicus.eu/)
2. Procure a cena `S2A_MSIL2A_20260401T130251_N0500_R110_T23KPQ_20260401T163512`
3. Baixe as bandas NIR (B8) e RED (B4)
4. Aplique `NDVI = (NIR - RED) / (NIR + RED)`
5. Calcule a média no polígono do projeto (o geoHash está on-chain)
6. Compare com `survivalBps = 9500` (95%) do evento

## Conferindo o refund proporcional

A fórmula está no próprio contrato (`contracts/ReforestVault.sol`):

```solidity
uint256 totalUndistributed = p.budgetRaised - p.budgetReleased;
uint256 share = (userDonation * totalUndistributed) / p.budgetRaised;
```

Exemplo do teste `test_refund_proRataAfterM36Failed`:
- donorA: doou 7.000 de 10.000 → recebe `9.000 × 7000/10000 = 6.300 USDC`
- donorB: doou 3.000 de 10.000 → recebe `9.000 × 3000/10000 = 2.700 USDC`

Para ver esses valores exatos rodando:

```powershell
cd test-bench
.\run.ps1 test
```

## Conferindo o controle de acesso

Tente reportar um milestone com uma conta que não é o oracle. Com o Anvil rodando depois do `.\run.ps1 deploy`:

```powershell
# Conta #1 do Anvil — NÃO é o oracle configurado
$VAULT = (Get-Content deploy\addresses.json | ConvertFrom-Json).'31337'.ReforestVault
cast send $VAULT `
  "reportMilestone(uint256,uint8,uint256,bytes32)" `
  1 0 9000 0x0000000000000000000000000000000000000000000000000000000000000000 `
  --private-key 0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d `
  --rpc-url http://127.0.0.1:8545
# Esperado: execution reverted
```

## Resumo das evidências

| Critério | Evidência |
|----------|-----------|
| Auditável | SHA-256 da cena Sentinel-2 no evento; dá pra reproduzir pela ESA ou no PowerShell |
| Verificável | O hash calculado localmente bate com o bytes32 on-chain |
| Transparente | Código verificado no Basescan e eventos públicos |
| Confiável | Controle de acesso (`setOracle`), padrão CEI e 15 testes passando |
| Mensurável | `survivalBps` em basis points, threshold 7500, payout proporcional |
| Rastreável | TreeNFT com GPS, espécie e doador; histórico de milestones |
</content>
