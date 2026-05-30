// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title TreeNFT — ReForest+
 * @notice Certificado de impacto ambiental: cada NFT representa uma árvore plantada via ReforestVault.
 * Apenas o endereço minter (definido pelo owner) pode emitir certificados,
 * garantindo que todo NFT tenha uma doação real por trás.
 */
contract TreeNFT is ERC721, Ownable {
    // Único endereço autorizado a mintar (será o ReforestVault).
    address public minter;

    struct TreeMetadata {
        uint256 projectId;
        string species;
        string gpsCoords;
        uint256 plantedAt;
        address originalDonor;
    }

    mapping(uint256 => TreeMetadata) public metadata;

    uint256 public nextTokenId = 1;

    event TreeMinted(
        uint256 indexed tokenId,
        uint256 indexed projectId,
        address indexed donor,
        string species
    );

    modifier onlyMinter() {
        require(msg.sender == minter, "Apenas o minter autorizado");
        _;
    }

    constructor(address initialAdmin)
        ERC721("TreeNFT ReForest+", "TREE")
        Ownable(initialAdmin)
    {}

    function setMinter(address minter_) external onlyOwner {
        require(minter_ != address(0), "Endereco do minter invalido");
        minter = minter_;
    }

    function mintTree(
        address donor,
        uint256 projectId,
        string calldata species,
        string calldata gpsCoords
    ) external onlyMinter returns (uint256 tokenId) {
        tokenId = nextTokenId++;
        metadata[tokenId] = TreeMetadata({
            projectId: projectId,
            species: species,
            gpsCoords: gpsCoords,
            plantedAt: block.timestamp,
            originalDonor: donor
        });
        _safeMint(donor, tokenId);
        emit TreeMinted(tokenId, projectId, donor, species);
    }
}
