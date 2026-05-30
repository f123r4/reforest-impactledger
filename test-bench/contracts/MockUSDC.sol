// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @title MockUSDC
 * @notice ERC-20 simples para uso em Anvil/testes locais. NÃO usar em produção.
 *
 * @dev Por que existe: em Base Sepolia há USDC.e real (faucet via Circle), mas para
 *      Anvil local precisamos de um token controlável. Mantemos a interface idêntica
 *      ao USDC: 6 decimais, símbolo USDC. O ReforestVault referencia `IERC20`, então
 *      a substituição pelo token real é transparente.
 *
 *      `mint` é público porque a demo precisa popular saldos sob demanda — proteger
 *      atrapalharia o pitch. Em produção a função simplesmente não existe.
 */
contract MockUSDC is ERC20 {
    constructor() ERC20("Mock USDC", "USDC") {}

    /// @dev USDC real tem 6 decimais, não 18. Manter isso aqui faz os cálculos de
    ///      orçamento e payout do Vault baterem igual com o mock e com o token real.
    function decimals() public pure override returns (uint8) {
        return 6;
    }

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}
