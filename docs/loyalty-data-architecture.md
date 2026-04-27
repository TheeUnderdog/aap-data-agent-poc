# AAP Loyalty Data Architecture

## Source → Loyalty Database Mapping

Each data source feeds specific entity groups in the loyalty database. Lines are color-coded by source system; connections converge through a central integration layer (likely external SQL links or ETL pipelines).

| Data Source | Data Elements | → Loyalty DB Entity | Rationale |
|---|---|---|---|
| **Point of Sale** | Transactions (purchases & returns) | **Transactions Details** | POS purchase/return records |
| **Point of Sale** | New member enrollment | **Loyalty Member Details** | In-store enrollment |
| **Point of Sale** | Coupon Redemption | **Coupons Details** | Coupon scans at checkout |
| **Order Mgmt (Sterling)** | Transactions (purchases & returns) | **Transactions Details** | Order fulfillment records |
| **Ecomm (B2C/mobile)** | New member enrollment, New DIY account | **Loyalty Member Details** | Online enrollment and DIY accounts |
| **Ecomm (B2C/mobile)** | Coupon Redemption | **Coupons Details** | Online coupon redemptions |
| **Customer First** | Member enrollment, status modifications | **Loyalty Member Details** | CRM manages member lifecycle |
| **Customer First** | Coupon Adjustment | **Coupons Details** | Service agents adjust coupons |
| **Customer First** | CSR (agent) | **Agent Details** | CSR representative records |
| **Customer First** | All agent/member/coupon activity | **Audit and Fraud Details** | CRM audit trail |
| **CrowdTwist** | Points Earned, Tier Status | **Member Points Details** | Loyalty engine — points & tiers |
| **CrowdTwist** | Bonus Activities | **SKU Details** | Bonus activity SKU configs |
| **CrowdTwist** | Points/tier change history | **Audit and Fraud Details** | Activity tracked for fraud detection |
| **GK Coupon Mgmt** | Coupon issuance, definitions, usage | **Coupons Details** | Coupon platform rules & status |
| **GK Coupon Mgmt** | SKU-level coupon rules | **SKU Details** | Product-level coupon rules |

## Architecture Diagram

```mermaid
flowchart LR
    %% ── Data Sources ──
    POS(["🏪 Point of Sale"])
    OMS(["📦 Order Mgmt\n(Sterling)"])
    ECOMM(["🌐 Ecomm\n(B2C / Mobile)"])
    CF(["📞 Customer First"])
    CT(["⭐ CrowdTwist"])
    GK(["🎟️ GK Coupon Mgmt"])

    %% ── Loyalty Database ──
    TXN["Transactions Details\n(3 yr history)"]
    LMD["Loyalty Member\nDetails"]
    MPD["Member Points\nDetails"]
    CPD["Coupons Details"]
    AFD["Audit & Fraud\nDetails"]
    AGD["Agent Details"]
    SKU["SKU Details"]

    %% ── Phase 2 (future) ──
    P2_CAM["Campaign Metrics"]
    P2_SUR["Survey Data"]
    P2_ONC["Online Conversion"]

    %% ── Point of Sale (blue) ──
    POS --> TXN
    POS --> LMD
    POS --> CPD

    %% ── Order Management (orange) ──
    OMS --> TXN

    %% ── Ecomm (green) ──
    ECOMM --> LMD
    ECOMM --> CPD

    %% ── Customer First (red) ──
    CF --> LMD
    CF --> CPD
    CF --> AGD
    CF --> AFD

    %% ── CrowdTwist (purple) ──
    CT --> MPD
    CT --> SKU
    CT --> AFD

    %% ── GK Coupon (teal) ──
    GK --> CPD
    GK --> SKU

    %% ── Link colors per source ──
    linkStyle 0,1,2 stroke:#1565c0,stroke-width:2px
    linkStyle 3 stroke:#e65100,stroke-width:2px
    linkStyle 4,5 stroke:#2e7d32,stroke-width:2px
    linkStyle 6,7,8,9 stroke:#c62828,stroke-width:2px
    linkStyle 10,11,12 stroke:#6a1b9a,stroke-width:2px
    linkStyle 13,14 stroke:#00838f,stroke-width:2px

    %% ── Node styles ──
    classDef src fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1
    classDef db fill:#e8eaf6,stroke:#283593,stroke-width:2px,color:#1a237e
    classDef future fill:#fff3e0,stroke:#e65100,stroke-width:1px,color:#bf360c,stroke-dasharray: 5 5

    class POS,OMS,ECOMM,CF,CT,GK src
    class TXN,LMD,MPD,CPD,AFD,AGD,SKU db
    class P2_CAM,P2_SUR,P2_ONC future
```

**Legend:** 🔵 POS &nbsp; 🟠 OMS &nbsp; 🟢 Ecomm &nbsp; 🔴 Customer First &nbsp; 🟣 CrowdTwist &nbsp; 🔷 GK Coupon

**Phase 2** (dashed) sources are not yet integrated: Campaign Metrics, Survey Data, Online Conversion.

## Reading This Diagram

| Column | Description |
|--------|-------------|
| **Data Sources** | Upstream systems feeding loyalty data |
| **Loyalty Database** | Consolidated loyalty data store (target for Fabric mirroring) |
| **Phase 2** | Future data sources not yet in scope |

> **Viewing:** This renders natively on GitHub. In VS Code, install the
> [Markdown Preview Mermaid Support](https://marketplace.visualstudio.com/items?itemName=bierner.markdown-mermaid) extension,
> then open Markdown Preview (`Ctrl+Shift+V`).
