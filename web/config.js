/**
 * Advance Insights — Application Configuration
 * Fill in your Fabric workspace ID, agent GUIDs, and Entra ID app registration.
 */
window.APP_CONFIG = {
    // Auth mode: true = proxy handles auth (local server.py or SWA Functions), false = MSAL direct
    // On SWA, relative /api/* URLs route to managed Functions automatically.
    // Locally, server.py proxies /api/* at localhost:5000. Both work with useProxy: true.
    useProxy: true,

    // Fabric workspace GUID (from portal URL)
    workspaceId: "82f53636-206f-4825-821b-bdaa8e089893",

    // MSAL / Entra ID configuration
    msalConfig: {
        auth: {
            clientId: "TODO_CLIENT_ID",           // Entra ID → App registrations → Overview
            authority: "https://login.microsoftonline.com/TODO_TENANT_ID",  // Entra ID → Overview → Tenant ID
            redirectUri: window.location.origin    // Auto-detects localhost or Azure URL
        },
        cache: {
            cacheLocation: "sessionStorage",
            storeAuthStateInCookie: false
        }
    },

    // Fabric API scopes
    fabricScopes: ["https://api.fabric.microsoft.com/.default"],

    // Agent definitions
    // Each maps a chatbot persona to a Fabric Data Agent in the workspace.
    //
    // ┌──────────────┬─────────────────────────────┬──────────────────────────────────────┐
    // │ Chatbot Tab   │ Fabric Data Agent            │ GUID                                 │
    // ├──────────────┼─────────────────────────────┼──────────────────────────────────────┤
    // │ Crew Chief    │ (client-side orchestrator)   │ n/a                                  │
    // │ Pit Crew      │ Customer Service & Support   │ e2cf8db6-2e51-45b6-bb2d-edfeeeb8b38a │
    // │ GearUp        │ Loyalty Program Manager      │ b03579f9-1074-4578-8165-6954a83b31c5 │
    // │ Ignition      │ Marketing & Promotions       │ f0272a61-7e54-408f-bf70-28495982567b │
    // │ PartsPro      │ Merchandising & Categories   │ 1062ac57-5132-4cf1-afbd-71e1e973fbc8 │
    // │ DieHard       │ Store Operations             │ e8fc166b-360e-4b0a-922b-05ca8bba3ff4 │
    // └──────────────┴─────────────────────────────┴──────────────────────────────────────┘
    //
    // API endpoint per agent (OpenAI-compatible):
    //   POST https://msitapi.fabric.microsoft.com/v1/workspaces/82f53636-206f-4825-821b-bdaa8e089893/dataagents/{GUID}/aiassistant/openai
    //   Body: { "messages": [{ "role": "user", "content": "..." }] }
    //   Auth: Bearer token (scope: https://api.fabric.microsoft.com/.default)
    //
    // Portal URLs:
    //   https://msit.powerbi.com/groups/82f53636-206f-4825-821b-bdaa8e089893/aiskills/{GUID}
    agents: {
        "crew-chief": {
            id: null, // Client-side orchestrator — no Fabric agent
            name: "Crew Chief",
            icon: "img/crew-chief.svg",
            accent: "#1E1E1E",
            welcome: "I coordinate the full team. Ask me anything \u2014 I'll get the right people on it.",
            description: "Executive orchestrator",
            shortDesc: "Ask anything",
            sampleQuestions: [
                "How are our top-tier loyalty members responding to the holiday promo?",
                "Which stores have the highest revenue and most loyalty sign-ups?",
                "What's our overall member retention rate vs. last quarter?",
                "Show me a cross-department summary of Q4 performance",
                "Which product categories drive the most reward redemptions?",
                "Compare campaign engagement rates across our top 10 stores"
            ]
        },
        "pit-crew": {
            id: "e2cf8db6-2e51-45b6-bb2d-edfeeeb8b38a",
            name: "Pit Crew",
            icon: "img/pit-crew.svg",
            accent: "#2B6CB0",
            welcome: "Ready to dig into service data. What can I look up?",
            description: "Customer Service & Support",
            shortDesc: "Service & support",
            sampleQuestions: [
                "How many support tickets were opened this month?",
                "What are the top 5 complaint categories?",
                "Show me average resolution time by support channel",
                "Which stores have the most escalated service issues?",
                "What's the customer satisfaction score trend over 6 months?",
                "List unresolved tickets older than 7 days"
            ]
        },
        "gearup": {
            id: "b03579f9-1074-4578-8165-6954a83b31c5",
            name: "GearUp",
            icon: "img/gearup.svg",
            accent: "#FFCC00",
            welcome: "Let's check in on the loyalty program. What do you want to know?",
            description: "Loyalty Program Manager",
            shortDesc: "Loyalty & rewards",
            sampleQuestions: [
                "How many active loyalty members do we have?",
                "What's the breakdown of members by tier?",
                "Show me the top 10 members by lifetime points earned",
                "What's our monthly enrollment trend this year?",
                "How many points were redeemed last quarter?",
                "Which rewards are most popular among Gold tier members?"
            ]
        },
        "ignition": {
            id: "f0272a61-7e54-408f-bf70-28495982567b",
            name: "Ignition",
            icon: "img/ignition.svg",
            accent: "#E86C00",
            welcome: "Campaigns, promotions, engagement \u2014 what are we analyzing?",
            description: "Marketing & Promotions",
            shortDesc: "Campaigns & promos",
            sampleQuestions: [
                "Which campaign had the highest response rate this quarter?",
                "Show me email open rates by campaign type",
                "How many customers redeemed the latest coupon offer?",
                "Compare engagement across our active promotions",
                "What's the ROI on our top 5 campaigns?",
                "Which customer segments respond best to email vs. SMS?"
            ]
        },
        "partspro": {
            id: "1062ac57-5132-4cf1-afbd-71e1e973fbc8",
            name: "PartsPro",
            icon: "img/partspro.svg",
            accent: "#2D8A4E",
            welcome: "Products, categories, inventory trends \u2014 ask away.",
            description: "Merchandising & Categories",
            shortDesc: "Products & merch",
            sampleQuestions: [
                "What are our top 10 selling products this month?",
                "Show me revenue by product category",
                "Which brands have the highest average transaction value?",
                "What products are trending up in sales vs. last quarter?",
                "List categories with declining sales over 3 months",
                "What's the average basket size by product category?"
            ]
        },
        "diehard": {
            id: "e8fc166b-360e-4b0a-922b-05ca8bba3ff4",
            name: "DieHard",
            icon: "img/diehard.svg",
            accent: "#B6121B",
            welcome: "Store performance, operations data \u2014 what do you need?",
            description: "Store Operations",
            shortDesc: "Stores & ops",
            sampleQuestions: [
                "What are our top 5 stores by revenue?",
                "Show me store performance by region",
                "Which stores had the biggest sales increase this quarter?",
                "Compare weekend vs. weekday sales across districts",
                "What's the average transaction value by store?",
                "Which locations have the most loyalty sign-ups per month?"
            ]
        }
    },

    // Agent display order (Crew Chief first)
    agentOrder: ["crew-chief", "pit-crew", "gearup", "ignition", "partspro", "diehard"],

    // Executive agent keyword routing
    executiveRouting: {
        "pit-crew":  ["service", "support", "complaint", "call", "agent", "csr", "ticket", "escalat", "audit"],
        "gearup":    ["loyalty", "reward", "tier", "gear", "points", "member", "enroll", "redeem"],
        "ignition":  ["campaign", "promo", "market", "email", "engag", "coupon", "offer", "response"],
        "partspro":  ["product", "category", "inventory", "merchand", "sku", "brand", "price", "item"],
        "diehard":   ["store", "location", "operat", "perform", "region", "district", "sales", "revenue"]
    }
};
