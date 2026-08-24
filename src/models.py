from typing import List, Literal

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    claim: str
    url: str
    source_type: Literal[
        "official_docs",
        "official_pricing",
        "official_help",
        "official_blog",
        "official_github",
        "third_party",
    ]
    quote_or_excerpt: str | None = None


class AppResearch(BaseModel):
    app: str
    website: str

    category: str
    description: str

    # -------------------------
    # Authentication
    # -------------------------

    auth_methods: List[str]

    credential_requirements: str

    # -------------------------
    # Access / gating
    # -------------------------

    self_serve: Literal[
        "free",
        "trial_or_paid",
        "gated",
        "unknown",
    ]

    # -------------------------
    # API surface
    # -------------------------

    rest_api: Literal[
        "yes",
        "no",
        "unknown",
    ]

    graphql_api: Literal[
        "yes",
        "no",
        "unknown",
    ]

    api_breadth: Literal[
        "broad",
        "moderate",
        "narrow",
        "unknown",
    ]

    # -------------------------
    # MCP
    # -------------------------

    mcp_available: Literal[
        "yes",
        "no",
        "unknown",
    ]

    # -------------------------
    # Agent buildability
    # -------------------------

    buildability: Literal[
        "ready",
        "conditional",
        "blocked",
        "unknown",
    ]

    main_blocker: str | None = None

    # -------------------------
    # Evidence
    # -------------------------

    evidence: List[Evidence]

    # -------------------------
    # Confidence
    # -------------------------

    confidence: Literal[
        "high",
        "medium",
        "low",
    ]