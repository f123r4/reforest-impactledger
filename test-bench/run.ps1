#!/usr/bin/env pwsh
# ReForest+ - runner do dia-a-dia no Windows (PowerShell nativo, sem WSL).
#
#   Uso:   .\run.ps1 <tarefa>        ex:  .\run.ps1 demo
#   Ajuda: .\run.ps1 help
#
# Assume forge / anvil / cast e python no PATH. Veja o README para a instalacao.

param([Parameter(Position = 0)][string]$Task = "help")

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# Conta #0 do Anvil: chave publica e conhecida, sem valor real. Usada na demo local.
$AnvilKey0 = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
$AnvilRpc = "http://127.0.0.1:8545"

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

# Le o .env e injeta as variaveis no ambiente do processo (forge precisa delas
# para resolver ${BASE_SEPOLIA_RPC_URL} etc.). A demo Python le o .env sozinha.
function Import-DotEnv {
    if (-not (Test-Path ".env")) { return }
    Get-Content ".env" | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $name, $value = $line.Split("=", 2)
            Set-Item -Path "Env:$($name.Trim())" -Value $value.Trim()
        }
    }
}

function Test-Anvil {
    try {
        $body = '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
        Invoke-RestMethod -Uri $AnvilRpc -Method Post -Body $body `
            -ContentType "application/json" -TimeoutSec 2 | Out-Null
        return $true
    } catch { return $false }
}

function Get-VenvPython {
    $py = ".\.venv\Scripts\python.exe"
    if (-not (Test-Path $py)) {
        throw "venv nao encontrada. Rode '.\run.ps1 install' primeiro."
    }
    return $py
}

# Baixa as libs Solidity (forge-std + OpenZeppelin) se ainda nao existirem.
function Install-SolidityDeps {
    if (-not (Test-Path "lib\forge-std")) {
        if (-not (Test-Path ".git")) { git init -q }
        forge install foundry-rs/forge-std
    }
    if (-not (Test-Path "lib\openzeppelin-contracts")) {
        forge install OpenZeppelin/openzeppelin-contracts
    }
}

# ----------------------------------------------------------------------------
# Tarefas
# ----------------------------------------------------------------------------

switch ($Task) {

    "help" {
        Write-Host "ReForest+ - tarefas disponiveis (.\run.ps1 <tarefa>):"
        Write-Host "  setup           Cria o .env com a chave de teste do Anvil"
        Write-Host "  deps            Baixa as libs Solidity (forge-std + OpenZeppelin)"
        Write-Host "  install         Cria a .venv e instala as dependencias Python"
        Write-Host "  build           Compila os contratos"
        Write-Host "  test            Roda os 15 testes do ReForest+"
        Write-Host "  anvil           Sobe o Anvil local em background"
        Write-Host "  deploy          Deploya os 3 contratos no Anvil local"
        Write-Host "  demo            Roda a demo ponta-a-ponta (M0->M36 + refund)"
        Write-Host "  dashboard       Painel de impacto dos projetos on-chain"
        Write-Host "  deploy-testnet  Deploy + verificacao na Base Sepolia"
        Write-Host "  demo-testnet    Roda a demo na Base Sepolia com carteiras reais"
    }

    "setup" {
        if (Test-Path ".env") {
            Write-Host ".env ja existe, pulando."
        } else {
            Copy-Item ".env.example" ".env"
            (Get-Content ".env") -replace 'DEPLOYER_PRIVATE_KEY=0x0000.*', "DEPLOYER_PRIVATE_KEY=$AnvilKey0" |
                Set-Content ".env"
            Write-Host ".env criado com a chave de teste do Anvil (conta #0 - sem valor real)."
        }
    }

    "deps" { Install-SolidityDeps }

    "install" {
        if (-not (Test-Path ".venv")) { python -m venv .venv }
        & ".\.venv\Scripts\python.exe" -m pip install -U pip
        & ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
    }

    "build" {
        Install-SolidityDeps
        forge build
    }

    "test" {
        Install-SolidityDeps
        forge test -vv
    }

    "anvil" {
        if (Test-Anvil) {
            Write-Host "Anvil ja esta rodando em 127.0.0.1:8545."
        } else {
            Start-Process -FilePath "anvil" `
                -ArgumentList "--chain-id", "31337", "--block-time", "2" `
                -WindowStyle Hidden `
                -RedirectStandardOutput "$env:TEMP\anvil.log" `
                -RedirectStandardError  "$env:TEMP\anvil.err.log"
            Write-Host "Aguardando Anvil iniciar..."
            for ($i = 0; $i -lt 10; $i++) {
                Start-Sleep -Seconds 1
                if (Test-Anvil) { break }
            }
            Write-Host "Anvil pronto em 127.0.0.1:8545 (logs: $env:TEMP\anvil.log)."
        }
    }

    "deploy" {
        $env:DEPLOYER_PRIVATE_KEY = $AnvilKey0
        forge script script/Deploy.s.sol --rpc-url $AnvilRpc --broadcast --private-key $AnvilKey0
    }

    "demo" {
        $py = Get-VenvPython
        $env:DEPLOYER_PRIVATE_KEY = $AnvilKey0
        & $py -m agent.demo
    }

    "dashboard" {
        $py = Get-VenvPython
        $env:DEPLOYER_PRIVATE_KEY = $AnvilKey0
        & $py -m agent.dashboard
    }

    "deploy-testnet" {
        Import-DotEnv
        forge script script/Deploy.s.sol `
            --rpc-url $env:BASE_SEPOLIA_RPC_URL `
            --broadcast `
            --verify `
            --etherscan-api-key $env:BASESCAN_API_KEY `
            --private-key $env:DEPLOYER_PRIVATE_KEY
    }

    "demo-testnet" {
        $py = Get-VenvPython
        & $py -m agent.demo --remote
    }

    default {
        Write-Host "Tarefa desconhecida: '$Task'. Rode '.\run.ps1 help' para ver as opcoes."
        exit 1
    }
}
