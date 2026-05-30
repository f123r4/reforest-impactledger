// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Script} from "forge-std/Script.sol";
import {console2 as console} from "forge-std/console2.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

import {MockUSDC} from "../contracts/MockUSDC.sol";
import {TreeNFT} from "../contracts/TreeNFT.sol";
import {ReforestVault} from "../contracts/ReforestVault.sol";

/**
 * @title Deploy
 * @notice Deploya os 3 contratos do ReForest+ num único broadcast e escreve os
 *         endereços em deploy/addresses.json (sob a chave do chainId).
 *
 * Ordem: TreeNFT primeiro (o Vault precisa do endereço dele no constructor),
 * depois o Vault, e por fim configuramos o minter e o oracle.
 */
contract Deploy is Script {
    function run() external {
        uint256 deployerKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address deployer = vm.addr(deployerKey);

        console.log("=== Deploy ReForest+ ===");
        console.log("chainId:", block.chainid);
        console.log("deployer:", deployer);

        vm.startBroadcast(deployerKey);

        MockUSDC usdc = new MockUSDC();
        console.log("MockUSDC:", address(usdc));

        TreeNFT treeNft = new TreeNFT(deployer);
        console.log("TreeNFT:", address(treeNft));

        ReforestVault vault = new ReforestVault(deployer, IERC20(address(usdc)), treeNft);
        console.log("ReforestVault:", address(vault));

        // Vault pode mintar NFTs quando doador opta pelo certificado.
        treeNft.setMinter(address(vault));

        // Deployer assume o papel de oracle na demo local.
        vault.setOracle(deployer);

        vm.stopBroadcast();

        _writeAddresses(address(usdc), address(treeNft), address(vault));
    }

    function _writeAddresses(address usdc, address treeNft, address vault) private {
        string memory path = "./deploy/addresses.json";
        string memory chainKey = vm.toString(block.chainid);

        vm.serializeAddress(chainKey, "MockUSDC", usdc);
        vm.serializeAddress(chainKey, "TreeNFT", treeNft);
        string memory inner = vm.serializeAddress(chainKey, "ReforestVault", vault);

        vm.writeJson(inner, path, string.concat(".", chainKey));
    }
}
