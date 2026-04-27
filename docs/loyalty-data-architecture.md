# AAP Loyalty Data Architecture

```mermaid
flowchart LR
    subgraph DS["🔵 Data Sources"]
        POS["**Point of Sale**\n- Transactions (purchases & returns)\n- Coupon Redemption\n- New member enrollment"]
        ECOMM["**Ecomm (B2C & mobile app)**\n- New member enrollment\n- New DIY account\n- Coupon Redemption"]
        OMS["**Order Management System\n(Sterling)**\n- Transactions (purchases & returns)"]
        CF["**Customer First**\n- Member enrollment\n- Member status modifications\n- Coupon Adjustment\n- CSR (agent)"]
        CT["**CrowdTwist**\n- Points Earned\n- Tier Status\n- Bonus Activities\n- Campaigns"]
        GK["**GK Coupon Management**\n- Coupon issuance\n- Coupon definitions\n- Coupon usage"]
    end

    subgraph LDB["🔵 Loyalty Database"]
        TXN["**Transactions Details**\n*(3 years data)*\n- Purchases\n- Returns"]
        LMD["**Loyalty Member Details**\n- Member Info\n- Opt Ins\n- Member Status\n- Member Tier Info"]
        MPD["**Member Points Details**\n- Total points\n- Redeemable points\n- Tier status\n- Tier rules"]
        CPD["**Coupons Details**\n- Coupon rule\n- Coupon Issuance\n- Coupon Status\n- Coupon Reference"]
        AFD["**Audit and Fraud Details**\n- Agent activity\n- Member enroll history\n- Coupon history"]
        AGD["**Agent Details**\n- CSR agent info"]
        SKU["**SKU Details**\n- Skip SKUs\n- Bonus Activities SKUs"]
    end

    subgraph P2["📋 Phase 2"]
        CAM["**Campaign Metrics**\n- Engagement by channel\n- CTR, Opt-outs,\n  unsubscribe"]
        SUR["**Survey Data**\n- Unstructured responses\n- Consumer sentiment"]
        ONC["**Online Conversion**\n- Funnel metrics\n- Browse and abandon\n  history"]
    end

    %% Point of Sale connections
    POS --> TXN
    POS --> LMD

    %% Ecomm connections
    ECOMM --> LMD
    ECOMM --> CPD

    %% Order Management connections
    OMS --> TXN
    OMS --> MPD

    %% Customer First connections
    CF --> LMD
    CF --> CPD
    CF --> AFD
    CF --> AGD

    %% CrowdTwist connections
    CT --> MPD
    CT --> AFD
    CT --> SKU

    %% GK Coupon Management connections
    GK --> CPD
    GK --> AGD
    GK --> SKU

    %% Styles
    classDef source fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1
    classDef db fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20
    classDef phase2 fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#bf360c

    class POS,ECOMM,OMS,CF,CT,GK source
    class TXN,LMD,MPD,CPD,AFD,AGD,SKU db
    class CAM,SUR,ONC phase2
```

## Reading This Diagram

| Column | Description |
|--------|-------------|
| **Data Sources** | Upstream systems feeding loyalty data |
| **Loyalty Database** | Consolidated loyalty data store (target for Fabric mirroring) |
| **Phase 2** | Future data sources not yet in scope |

> **Viewing:** This renders natively on GitHub. In VS Code, install the
> [Markdown Preview Mermaid Support](https://marketplace.visualstudio.com/items?itemName=bierner.markdown-mermaid) extension,
> then open Markdown Preview (`Ctrl+Shift+V`).
