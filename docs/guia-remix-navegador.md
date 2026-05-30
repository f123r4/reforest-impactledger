# Passo a Passo — Remix IDE (Navegador)

> ReForest+ · ImpactLedger · HackWeb Web3 — Desafio 3
> **Zero instalação.** Tudo roda no navegador. Use este guia para a demonstração ao vivo na apresentação.

Versão em PDF: [`guia-remix-navegador.pdf`](guia-remix-navegador.pdf).

---

## O que você vai demonstrar

| Etapa | O que prova | Critério |
|-------|-------------|----------|
| Deploy dos contratos | Smart contracts funcionais na blockchain | Uso de blockchain |
| Cadastro de projeto | Ação de impacto registrada on-chain (GPS, espécie) | Registro verificável |
| Doação + TreeNFT | Certificado digital imutável para o doador | Rastreável |
| Declaração de plantio | Timestamp on-chain — prova que o plantio ocorreu | Auditável |
| Oracle aprova M0 | Payout automático — contrato libera 10% sem burocracia | Mensurável |
| Oracle reprova projeto | Sistema registra honestamente a falha (estiagem) | Confiável |
| Refund pro-rata | Doador recupera automaticamente — sem depender de ninguém | Transparente |

---

## Pré-requisito — MetaMask (opcional, só para testnet)

Para rodar na **Remix VM** (recomendado para ensaiar) não precisa de MetaMask. Para publicar na **Base Sepolia** e mostrar no Basescan, instale a extensão MetaMask e adicione a rede:

| Campo | Valor |
|-------|-------|
| Nome | Base Sepolia |
| RPC URL | https://sepolia.base.org |
| Chain ID | 84532 |
| Símbolo | ETH |
| Explorador | https://sepolia.basescan.org |

**Faucet de ETH de teste:** `faucet.quicknode.com/base/sepolia` — cole seu endereço e receba ~0,01 ETH (suficiente para ~10 deploys).

---

## Parte 1 — Carregar os contratos no Remix

1. **Abrir o Remix** — acesse `remix.ethereum.org`. No painel esquerdo, clique em **File Explorer**.
2. **Criar pasta de trabalho** — crie a pasta `reforest` e, dentro dela, `contracts`.
3. **Carregar os 3 contratos** — com a pasta `contracts` selecionada, use **Upload files** e envie `MockUSDC.sol`, `TreeNFT.sol` e `ReforestVault.sol` (estão na pasta `contracts/` deste repositório).

> Os imports `@openzeppelin/contracts` são resolvidos automaticamente pelo Remix via CDN — não precisa instalar nada.

## Parte 2 — Compilar

4. **Abrir o compilador** — ícone **Solidity Compiler**.
5. **Selecionar versão** — selecione exatamente **0.8.24** (ou superior). Marque **Auto compile**.
6. **Definir o EVM como Cancun** — em *Advanced Configurations*, campo *EVM Version*, selecione `cancun` (nas versões novas do Remix o `default` já é Cancun).

   > **Por que isso importa.** O OpenZeppelin v5.1+ usa a instrução `mcopy` em `Bytes.sol`, introduzida na hard fork **Cancun** e suportada a partir do Solidity 0.8.24. Com EVM `paris`/`shanghai` a compilação falha com `DeclarationError: Function "mcopy" not found`.

7. **Compilar ReforestVault.sol** — com o arquivo aberto, clique em *Compile ReforestVault.sol*. O ícone do compilador deve ficar verde.

> **Atenção ao fazer deploy:** `mcopy` só funciona em redes pós-Cancun. Base Sepolia, Sepolia, Holesky e Ethereum mainnet já suportam. Por isso, no próximo passo use **Remix VM (Cancun)** — e não versões mais antigas da Remix VM.

## Parte 3 — Deploy dos contratos

Abra a aba **Deploy & Run Transactions**.

> **Environment:** selecione **Remix VM (Cancun)** para demo local instantânea, ou **Injected Provider — MetaMask** para publicar na Base Sepolia.

8. **Deploy MockUSDC** — selecione `MockUSDC`, clique em **Deploy** (sem parâmetros). Anote o endereço → `USDC_ADDR`.
9. **Deploy TreeNFT** — selecione `TreeNFT`. No construtor, cole o endereço da conta selecionada no topo (será o admin). **Deploy** → `NFT_ADDR`.
10. **Deploy ReforestVault** — selecione `ReforestVault` e preencha o construtor:

    ```
    admin:         [endereço da sua conta]
    paymentToken_: [USDC_ADDR]
    treeNft_:      [NFT_ADDR]
    ```

    **Deploy** → `VAULT_ADDR`.

## Parte 4 — Configurar papéis

11. **Autorizar o oracle** — em *Deployed Contracts*, expanda **ReforestVault** → função `setOracle` → cole o endereço da sua conta (será o oracle na demo) → **transact**.
12. **Autorizar o Vault a mintar NFTs** — expanda **TreeNFT** → função `setMinter` → cole `VAULT_ADDR` → **transact**.

## Parte 5 — Registrar projeto de impacto

13. **Criar projeto de reflorestamento** — em ReforestVault, função `createProject` (clique na setinha para abrir campo por parâmetro):

    ```
    planter:      [endereço de uma segunda conta do Remix]
    geoHash:      0x1111111111111111111111111111111111111111111111111111111111111111
    species:      Ipe-amarelo
    gpsCoords:    "-19.9,-43.95"
    plannedTrees: 1000
    budgetTotal:  10000000000
    ```

    **transact** → o evento `ProjectCreated` aparece no log.

    > **As aspas em `gpsCoords` são obrigatórias.** O valor `-19.9,-43.95` tem uma vírgula que o Remix interpretaria como separador de argumentos. Entre aspas, ele trata como texto único.
    >
    > `budgetTotal: 10000000000` = 10.000 USDC (6 decimais). `createProject` é `onlyOwner` — a conta no topo deve ser a **admin** que fez o deploy.

## Parte 6 — Doação e emissão do TreeNFT

14. **Mintar USDC para o doador** — mude a conta ativa no topo para uma segunda conta (será "Alice — doadora"). Em **MockUSDC**, função `mint`: `to: [endereço da segunda conta]`, `amount: 30000000000` → **transact**.
15. **Aprovar o Vault para gastar o USDC** — ainda com a conta de Alice, em **MockUSDC**, função `approve`: `spender: [VAULT_ADDR]`, `amount: <um valor grande>` (aprovação ampla simplifica a demo) → **transact**.
16. **Fazer doação e mintar TreeNFT** — em **ReforestVault**, função `donate`: `projectId: 1`, `amount: 7000000000`, `mintNft: true` → **transact**. No log aparecem `Donated` e `TreeMinted` — Alice recebeu um NFT com GPS e espécie gravados on-chain.

## Parte 7 — Declaração de plantio (timestamp on-chain)

17. **Plantador declara o plantio** — mude para a conta do plantador (a usada em `createProject`). Em ReforestVault, função `declarePlanted`: `projectId: 1` → **transact**. O evento `Planted` é emitido com timestamp imutável; a partir daqui os milestones começam a contar.

## Parte 8 — Oracle satelital: milestone M0 aprovado

18. **Oracle reporta 95% de sobrevivência** — volte para a conta admin/oracle. Em ReforestVault, função `reportMilestone`:

    ```
    projectId:      1
    milestone:      0   (0=M0, 1=M6, 2=M12, 3=M36)
    survivalBps:    9500
    dataSourceHash: 0x2d3c1b4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b
    ```

    Resultado: `MilestoneReported (approved=true)` e `PayoutReleased amount=700000000` — 10% do orçamento (700 USDC) liberado automaticamente ao plantador. O `dataSourceHash` é o SHA-256 da cena Sentinel-2 — qualquer auditor pode verificar.

## Parte 9 — Simular um projeto que falhou (reprovação ao vivo)

> **Por que não dá para reprovar o M6 do projeto 1 aqui:** M6 só fica disponível 180 dias após o plantio (`M6_DELAY = 180 days`) e a Remix VM não permite adiantar o relógio. A saída é demonstrar a reprovação usando o **M0 de um segundo projeto** (`M0_DELAY = 0`). Reaproveitamos as mesmas contas. (O ciclo temporal completo M6→M36 + refund é provado no Anvil, pela suíte Foundry.)

19. **Criar um segundo projeto (conta admin)** — selecione a conta admin. Em ReforestVault, `createProject`:

    ```
    planter:      [a MESMA segunda conta do projeto 1]
    geoHash:      0x2222222222222222222222222222222222222222222222222222222222222222
    species:      Aroeira
    gpsCoords:    "-20.1,-44.10"
    plannedTrees: 800
    budgetTotal:  8000000000
    ```

    **transact** → recebe `projectId = 2` automaticamente.

20. **Declarar o plantio do projeto 2** — troque para a conta do plantador. `declarePlanted`: `projectId: 2` → **transact**. Como o M0 tem delay zero, fica disponível imediatamente.
21. **Oracle reporta estiagem — 50% de sobrevivência** — volte para a conta admin/oracle. `reportMilestone`:

    ```
    projectId:      2
    milestone:      0
    survivalBps:    5000
    dataSourceHash: 0x1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b
    ```

    Resultado: `MilestoneReported (approved=false)` — nenhum `PayoutReleased`. 50% está abaixo do threshold de 75% → milestone reprovado. O sistema registra a falha com honestidade. As duas trilhas (aprovado e reprovado) ao vivo, no mesmo Remix.

## Parte 10 — Verificar o NFT do doador

22. **Consultar metadados do TreeNFT** — em **TreeNFT**, função `metadata`: `tokenId: 1`. Resultado: `projectId`, `species: Ipe-amarelo`, `gpsCoords: -19.9,-43.95`, `plantedAt`, `originalDonor`. Esses dados são imutáveis na blockchain — nenhuma organização pode alterá-los.

---

## Parte 11 — Publicar na testnet pública (Base Sepolia)

> A demo das Partes 1–10 roda na Remix VM (local), ótima para ensaiar. Mas o desafio valoriza um **contrato em testnet pública com endereço verificável** — auditável de fora. É o **mesmo** fluxo: só muda o *Environment* e cada transação passa pela MetaMask gastando gás de teste.

23. **Instalar a MetaMask e adicionar a Base Sepolia** — use uma carteira só de teste; adicione a rede com os dados do pré-requisito.
24. **Pegar ETH de teste no faucet** — `faucet.quicknode.com/base/sepolia`. 0,02 ETH cobre vários deploys + a demo inteira.
25. **Trocar o Environment para a MetaMask** — em *Deploy & Run Transactions*, troque `Remix VM (Cancun)` por **Injected Provider — MetaMask**. Autorize e confirme que está na rede Base Sepolia.
26. **Deployar os 3 contratos (confirmando na MetaMask)** — mesma ordem das Partes 3–4:

    ```
    1) Deploy MockUSDC                              → confirmar na MetaMask
    2) Deploy TreeNFT(admin)                        → confirmar
    3) Deploy ReforestVault(admin, USDC_ADDR, NFT_ADDR) → confirmar
    4) ReforestVault.setOracle(admin) e TreeNFT.setMinter(VAULT_ADDR) → confirmar
    ```

    Anote os 3 endereços — agora são públicos e auditáveis na Base Sepolia.

27. **Rodar o fluxo de impacto na testnet** — repita as Partes 5 a 9 (`createProject` → `mint`/`approve` → `donate`+NFT → `declarePlanted` → `reportMilestone` M0 aprovado → 2º projeto com M0 reprovado), confirmando cada transação na MetaMask.

    > Numa testnet real o relógio também não pula 180 dias — então M6/M12/M36 continuam indisponíveis. Use o mesmo truque: a reprovação é demonstrada com o M0 de um segundo projeto (delay zero).

28. **(Opcional) Verificar o código no explorer** — use o plugin *Contract Verification* do Remix com uma API key gratuita de `basescan.org/myapikey`, ou publique no **Sourcify**. Funciona sem isso, mas o código verificado fortalece a auditabilidade.

## Parte 12 — Verificar no Basescan

Se publicou na Base Sepolia, acesse `https://sepolia.basescan.org/address/[VAULT_ADDR]#events` e mostre os eventos emitidos em tempo real.

| O que mostrar | Onde encontrar no Basescan |
|---------------|----------------------------|
| Código verificado do contrato | Aba *Contract* → *Code* |
| Eventos on-chain | Aba *Contract* → *Events* |
| TreeNFT mintado para Alice | TreeNFT → aba *Token Transfers* |
| `dataSourceHash` do oracle | Evento `MilestoneReported` → campo `dataSourceHash` |

### Prova de auditabilidade (PowerShell)

```powershell
$texto  = "S2A_MSIL2A_20260401T130251_N0500_R110_T23KPQ_20260401T163512"
$stream = [IO.MemoryStream]::new([Text.Encoding]::ASCII.GetBytes($texto))
Get-FileHash -InputStream $stream -Algorithm SHA256 | Select-Object -ExpandProperty Hash
```

O hash gerado deve ser idêntico ao `dataSourceHash` gravado on-chain (compare ignorando maiúsculas/minúsculas).

---

## Resumo dos critérios demonstrados

| Critério | Como foi demonstrado |
|----------|----------------------|
| **Auditável** | SHA-256 da cena Sentinel-2 gravado no evento — reproduzível por qualquer um |
| **Verificável** | Metadados do NFT consultáveis on-chain; hash conferível via sha256 |
| **Transparente** | Todos os eventos públicos; código verificado no Basescan |
| **Confiável** | Apenas oracle autorizado reporta; `setOracle` impede outros |
| **Mensurável** | `survivalBps` em basis points; threshold 75% (7500); payout proporcional |
| **Rastreável** | TreeNFT com GPS, espécie e doador original gravados no bloco |
</content>
