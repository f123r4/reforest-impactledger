# ReForest+ — ImpactLedger

Projeto da trilha Blockchain do HackWeb Web3 (Desafio 3 — ImpactLedger).

A ideia é simples: hoje, quando alguém doa para um projeto de reflorestamento, não tem como saber se as árvores realmente sobreviveram. ReForest+ resolve isso colocando cada projeto na blockchain e travando o dinheiro em um contrato inteligente. O valor só é liberado quando um oracle satelital (Sentinel-2 / ESA) confirma que as árvores estão vivas. Se o projeto falha, o doador recebe sua parte de volta automaticamente.

A gente fez todo o fluxo principal rodar no navegador, pelo **[Remix IDE](https://remix.ethereum.org)** — não precisa instalar nada.

## O problema

Uma engenheira ambiental e doou para um projeto de reflorestamento no Vale do Ribeira. Seis meses depois ela foi perguntar como estava e recebeu um PDF com fotos sem data e coordenadas que não batem. Ou seja: ela não tem como saber se as árvores existem.

Isso acontece o tempo todo. Os projetos dependem de relatório manual, planilha, auditoria cara e rara. Não existe verificação independente, e quem doou fica no escuro.

## A solução

Cada projeto vira um registro on-chain, e a liberação do dinheiro fica condicionada a evidência satelital que qualquer um pode conferir.

```
Doador → [ReforestVault] → Oracle Sentinel-2 (NDVI) → Milestone aprovado → Plantador recebe
                                                     ↓ reprovado → Doador resgata pro-rata
```

A liberação é feita por milestones de sobrevivência (M0, M6, M12, M36). A cada milestone o oracle grava o SHA-256 do scene ID da imagem Sentinel-2 no evento on-chain. Com isso, qualquer pessoa baixa a mesma cena no portal da ESA, recalcula o NDVI e confere se o número reportado é verdadeiro — sem precisar confiar na nossa palavra.

## Como o desafio é atendido

| Critério | Como resolvemos |
|----------|-----------------|
| Auditável | SHA-256 da cena Sentinel-2 gravado no evento `MilestoneReported`, reproduzível por qualquer um |
| Verificável | Metadados do TreeNFT e eventos consultáveis on-chain; hash conferível localmente |
| Transparente | Todos os eventos são públicos na Base Sepolia, com o código verificado no Basescan |
| Confiável | Papéis separados (admin / oracle / plantador) e 15 testes automatizados |
| Mensurável | `survivalBps` em basis points, threshold de 75% e payout proporcional automático |
| Rastreável | TreeNFT (ERC-721) com GPS, espécie e doador original gravados no bloco |

## Arquitetura e tecnologias

- Solidity 0.8.24 + OpenZeppelin (ERC-20, ERC-721, Ownable)
- Remix IDE para compilar, deployar e operar o fluxo no navegador
- Base Sepolia (testnet pública) + MetaMask para publicar e auditar
- Sentinel-2 / ESA Copernicus como fonte do oracle (NDVI de sobrevivência)
- Bancada de testes em `test-bench/`: Foundry (15 testes) + um agente Python que roda o ciclo completo M0→M36

### Os contratos (`contracts/`)

| Contrato | O que faz |
|----------|-----------|
| `ReforestVault.sol` | Guarda as doações, libera por milestone validado pelo oracle e faz o refund pro-rata |
| `TreeNFT.sol` | Certificado de impacto (ERC-721) com GPS, espécie e doador on-chain |
| `MockUSDC.sol` | ERC-20 com 6 decimais para a demo (dá pra trocar pelo USDC real) |

## Contratos publicados na Base Sepolia

Os três contratos estão deployados e com o código verificado:

| Contrato | Endereço | Links |
|----------|----------|-------|
| ReforestVault | `0xc445823A43c857438bCdA289e8d713DFC183B463` | [código](https://sepolia.basescan.org/address/0xc445823A43c857438bCdA289e8d713DFC183B463#code) · [eventos](https://sepolia.basescan.org/address/0xc445823A43c857438bCdA289e8d713DFC183B463#events) |
| TreeNFT | `0xDd7b07dd2684c4881Df7B1Ba450B69fbc1ddE848` | [código](https://sepolia.basescan.org/address/0xDd7b07dd2684c4881Df7B1Ba450B69fbc1ddE848#code) · [tokens](https://sepolia.basescan.org/address/0xDd7b07dd2684c4881Df7B1Ba450B69fbc1ddE848#tokentxns) |
| MockUSDC | `0x7D3f460251dd9d04481de14B04507697B2bA36d2` | [código](https://sepolia.basescan.org/address/0x7D3f460251dd9d04481de14B04507697B2bA36d2#code) |

## Como rodar (Remix, sem instalar nada)

O passo a passo completo está em [`docs/guia-remix-navegador.md`](docs/guia-remix-navegador.md) (também em [PDF](docs/guia-remix-navegador.pdf)). Em resumo:

1. Abra [remix.ethereum.org](https://remix.ethereum.org) e suba os 3 arquivos de `contracts/`.
2. Compile com Solidity 0.8.24 e EVM Cancun (os imports do OpenZeppelin vêm por CDN, não precisa instalar nada).
3. Faça o deploy em Remix VM (Cancun) para testar local, ou em Injected Provider — MetaMask na Base Sepolia para a versão pública auditável.
4. Configure os papéis: `ReforestVault.setOracle(...)` e `TreeNFT.setMinter(VaultAddr)`.
5. Rode o fluxo: `createProject` → `donate` (com TreeNFT) → `declarePlanted` → `reportMilestone` (M0 aprovado) → um segundo projeto com M0 reprovado (estiagem) → `refund`.

Os milestones M6/M12/M36 dependem de 180 a 1.095 dias reais, então o ciclo temporal inteiro a gente valida na bancada de testes (Foundry), não no navegador.

## Bancada de testes (`test-bench/`)

É o tooling que usamos para validar os contratos antes de subir. Não faz parte do fluxo de entrega, mas é o que prova que a lógica está certa:

- Foundry — 15 testes cobrindo payout, refund pro-rata, controle de acesso e janelas de milestone.
- Agente Python — simula o ciclo completo M0→M36 + refund, que não dá pra fazer no navegador por causa dos prazos reais.

As instruções de execução estão em [`docs/GUIA_AVALIADOR.md`](docs/GUIA_AVALIADOR.md).

## Demonstração auditável

As evidências verificáveis (links do Basescan, conferência do hash satelital e a fórmula do refund) estão em [`docs/DEMONSTRACAO_AUDITAVEL.md`](docs/DEMONSTRACAO_AUDITAVEL.md).

## Organização do repositório

```
contracts/    Os 3 contratos Solidity usados no Remix
docs/         Guia Remix passo a passo, demonstração auditável e guia do avaliador
test-bench/   Bancada de testes: Foundry (15 testes) + agente Python (ciclo M0→M36)
```
</content>
