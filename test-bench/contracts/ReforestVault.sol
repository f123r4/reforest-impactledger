// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

import {TreeNFT} from "./TreeNFT.sol";

/**
 * @title ReforestVault
 * @notice Cofre de doações com liberação travada por milestones de sobrevivência.
 *
 * Doadores depositam USDC. O oracle satelital reporta survival rate a cada
 * milestone (M0/M6/M12/M36). Se >= 75%, libera a fatia do plantador.
 * Se reprovar, o valor fica disponível para refund proporcional aos doadores.
 */
contract ReforestVault is Ownable {
    // Endereço autorizado a reportar milestones (oracle satelital).
    address public geoOracle;

    // Delays a partir do plantio
    uint256 public constant M0_DELAY  = 0;
    uint256 public constant M6_DELAY  = 180 days;
    uint256 public constant M12_DELAY = 365 days;
    uint256 public constant M36_DELAY = 3 * 365 days;

    // % liberado por milestone em basis points (soma = 10000)
    uint256 public constant M0_BPS  = 1_000;
    uint256 public constant M6_BPS  = 3_000;
    uint256 public constant M12_BPS = 3_000;
    uint256 public constant M36_BPS = 3_000;
    uint256 public constant BPS_DIVISOR = 10_000;

    uint256 public constant SURVIVAL_THRESHOLD_BPS = 7_500; // 75%

    enum Milestone { M0, M6, M12, M36 }
    enum MilestoneStatus { PENDING, APPROVED, REJECTED }

    struct Project {
        address planter;
        bytes32 geoHash;
        string species;
        string gpsCoords;
        uint256 plannedTrees;
        uint256 budgetTotal;
        uint256 budgetRaised;
        uint256 budgetReleased;
        uint256 plantedAt;
        bool exists;
    }

    mapping(uint256 => Project) public projects;
    mapping(uint256 => mapping(uint256 => MilestoneStatus)) public milestoneStatus;
    mapping(uint256 => mapping(address => uint256)) public donatedBy;

    uint256 public nextProjectId = 1;

    IERC20 public immutable paymentToken;
    TreeNFT public immutable treeNft;

    // ============================ Events ============================

    event ProjectCreated(
        uint256 indexed projectId,
        address indexed planter,
        uint256 plannedTrees,
        uint256 budgetTotal
    );
    event Donated(
        uint256 indexed projectId,
        address indexed donor,
        uint256 amount,
        bool nftMinted,
        uint256 nftTokenId
    );
    event Planted(uint256 indexed projectId, uint256 plantedAt);
    event MilestoneReported(
        uint256 indexed projectId,
        Milestone milestone,
        uint256 survivalBps,
        bool approved,
        address indexed reporter,
        bytes32 dataSourceHash
    );
    event PayoutReleased(uint256 indexed projectId, Milestone milestone, uint256 amount);
    event Refunded(uint256 indexed projectId, address indexed donor, uint256 amount);

    modifier onlyOracle() {
        require(msg.sender == geoOracle, "Apenas o oracle autorizado");
        _;
    }

    constructor(address admin, IERC20 paymentToken_, TreeNFT treeNft_)
        Ownable(admin)
    {
        paymentToken = paymentToken_;
        treeNft = treeNft_;
    }

    // ============================ Admin ============================

    function setOracle(address oracle_) external onlyOwner {
        require(oracle_ != address(0), "Endereco do oracle invalido");
        geoOracle = oracle_;
    }

    // ============================ Project lifecycle ============================

    function createProject(
        address planter,
        bytes32 geoHash,
        string calldata species,
        string calldata gpsCoords,
        uint256 plannedTrees,
        uint256 budgetTotal
    ) external onlyOwner returns (uint256 projectId) {
        require(planter != address(0), "Endereco do plantador invalido");
        require(plannedTrees > 0 && budgetTotal > 0, "Arvores e orcamento devem ser positivos");
        require(geoHash != bytes32(0), "Hash do poligono geografico invalido");

        projectId = nextProjectId++;
        projects[projectId] = Project({
            planter: planter,
            geoHash: geoHash,
            species: species,
            gpsCoords: gpsCoords,
            plannedTrees: plannedTrees,
            budgetTotal: budgetTotal,
            budgetRaised: 0,
            budgetReleased: 0,
            plantedAt: 0,
            exists: true
        });
        emit ProjectCreated(projectId, planter, plannedTrees, budgetTotal);
    }

    /**
     * @notice Doador deposita USDC. Opcionalmente minta TreeNFT como certificado.
     */
    function donate(uint256 projectId, uint256 amount, bool mintNft) external {
        Project storage p = projects[projectId];
        require(p.exists, "Projeto nao encontrado");
        require(amount > 0, "Valor da doacao deve ser maior que zero");
        require(p.budgetRaised + amount <= p.budgetTotal, "Doacao excede o limite do projeto");

        paymentToken.transferFrom(msg.sender, address(this), amount);
        p.budgetRaised += amount;
        donatedBy[projectId][msg.sender] += amount;

        uint256 nftTokenId = 0;
        if (mintNft) {
            nftTokenId = treeNft.mintTree(msg.sender, projectId, p.species, p.gpsCoords);
        }
        emit Donated(projectId, msg.sender, amount, mintNft, nftTokenId);
    }

    /**
     * @notice Plantador declara que executou o plantio. Marca timestamp para os milestones.
     */
    function declarePlanted(uint256 projectId) external {
        Project storage p = projects[projectId];
        require(p.exists, "Projeto nao encontrado");
        require(msg.sender == p.planter, "Somente o plantador pode registrar o plantio");
        require(p.plantedAt == 0, "Plantio ja foi registrado");
        p.plantedAt = block.timestamp;
        emit Planted(projectId, block.timestamp);
    }

    // ============================ Oracle milestones ============================

    /**
     * @notice Oracle reporta survival rate de um milestone. Se >= threshold → aprovado e payout.
     * @param survivalBps Survival rate em basis points (ex: 8000 = 80%).
     * @param dataSourceHash SHA-256 do identificador da cena satelital (Sentinel-2),
     *        permitindo que qualquer auditor verifique o NDVI reportado.
     */
    function reportMilestone(
        uint256 projectId,
        Milestone milestone,
        uint256 survivalBps,
        bytes32 dataSourceHash
    ) external onlyOracle {
        Project storage p = projects[projectId];
        require(p.exists, "Projeto nao encontrado");
        require(p.plantedAt > 0, "Plantio ainda nao foi declarado");
        require(survivalBps <= BPS_DIVISOR, "Taxa de sobrevivencia invalida");

        uint256 mi = uint256(milestone);
        require(milestoneStatus[projectId][mi] == MilestoneStatus.PENDING, "Este milestone ja foi reportado");

        uint256 minTimestamp = p.plantedAt + _milestoneDelay(milestone);
        require(block.timestamp >= minTimestamp, "Milestone ainda nao disponivel");

        bool approved = survivalBps >= SURVIVAL_THRESHOLD_BPS;
        milestoneStatus[projectId][mi] = approved ? MilestoneStatus.APPROVED : MilestoneStatus.REJECTED;

        emit MilestoneReported(projectId, milestone, survivalBps, approved, msg.sender, dataSourceHash);

        if (approved) {
            uint256 bps = _milestoneBps(milestone);
            uint256 payout = (p.budgetRaised * bps) / BPS_DIVISOR;
            p.budgetReleased += payout;
            paymentToken.transfer(p.planter, payout);
            emit PayoutReleased(projectId, milestone, payout);
        }
    }

    // ============================ Refunds ============================

    /**
     * @notice Doador resgata pro-rata da parte não liberada, após M36 ser decidido.
     */
    function refund(uint256 projectId) external {
        Project storage p = projects[projectId];
        require(p.exists, "Projeto nao encontrado");
        require(
            milestoneStatus[projectId][uint256(Milestone.M36)] != MilestoneStatus.PENDING,
            "Aguarde a resolucao do milestone M36"
        );

        uint256 userDonation = donatedBy[projectId][msg.sender];
        require(userDonation > 0, "Sem doacao registrada neste projeto");

        uint256 totalUndistributed = p.budgetRaised - p.budgetReleased;
        uint256 share = (userDonation * totalUndistributed) / p.budgetRaised;
        donatedBy[projectId][msg.sender] = 0;

        if (share > 0) {
            paymentToken.transfer(msg.sender, share);
            emit Refunded(projectId, msg.sender, share);
        }
    }

    // ============================ Views ============================

    function isMilestoneReady(uint256 projectId, Milestone milestone) external view returns (bool) {
        Project memory p = projects[projectId];
        if (!p.exists || p.plantedAt == 0) return false;
        return block.timestamp >= p.plantedAt + _milestoneDelay(milestone);
    }

    // ============================ Internal ============================

    function _milestoneDelay(Milestone m) internal pure returns (uint256) {
        if (m == Milestone.M0)  return M0_DELAY;
        if (m == Milestone.M6)  return M6_DELAY;
        if (m == Milestone.M12) return M12_DELAY;
        return M36_DELAY;
    }

    function _milestoneBps(Milestone m) internal pure returns (uint256) {
        if (m == Milestone.M0)  return M0_BPS;
        if (m == Milestone.M6)  return M6_BPS;
        if (m == Milestone.M12) return M12_BPS;
        return M36_BPS;
    }
}
