from src.models import AppResearch, Evidence
from src.validator import validate_evidence


# --------------------------------------------------
# Test Salesforce research result
# --------------------------------------------------

result = AppResearch(
    app="Salesforce",
    website="https://www.salesforce.com/",
    category="CRM and Sales",
    description=(
        "Salesforce is a CRM platform providing "
        "APIs and tools for managing customer data."
    ),

    # --------------------------------------------------
    # Authentication
    # --------------------------------------------------

    auth_methods=[
        "OAuth 2.0",
        "OpenID Connect",
        "PKCE",
        "JWT",
    ],

    credential_requirements=(
        "Developers can obtain a free Developer Edition "
        "and configure an External Client App or Connected "
        "App to obtain OAuth credentials."
    ),

    # --------------------------------------------------
    # Access
    # --------------------------------------------------

    self_serve="free",

    # --------------------------------------------------
    # API surface
    # --------------------------------------------------

    rest_api="yes",
    graphql_api="yes",
    api_breadth="broad",

    # --------------------------------------------------
    # MCP
    # --------------------------------------------------

    mcp_available="yes",

    # --------------------------------------------------
    # Buildability
    # --------------------------------------------------

    buildability="ready",
    main_blocker=None,

    # --------------------------------------------------
    # Evidence
    # --------------------------------------------------

    evidence=[
        # OAuth
        Evidence(
            claim=(
                "Salesforce supports OAuth 2.0 "
                "authentication for API integrations."
            ),
            url=(
                "https://developer.salesforce.com/docs/"
                "atlas.en-us.api_rest.meta/api_rest/"
                "intro_oauth_and_connected_apps.htm"
            ),
            source_type="official_docs",
            quote_or_excerpt=(
                "For an external client app or connected "
                "app to request access, it must be integrated "
                "with your org's REST API using the OAuth 2.0 "
                "protocol."
            ),
        ),

        # OpenID Connect
        Evidence(
            claim=(
                "Salesforce supports OpenID Connect "
                "as an authentication service."
            ),
            url=(
                "https://help.salesforce.com/"
                "s/articleView?id=sf.remoteaccess_authenticate.htm"
                "&language=en_US&type=5"
            ),
            source_type="official_help",
            quote_or_excerpt=(
                "Instead, use OpenID Connect as an "
                "authentication service in addition "
                "to OAuth authorization."
            ),
        ),

        # PKCE
        Evidence(
            claim=(
                "Salesforce supports the Proof Key for "
                "Code Exchange (PKCE) extension."
            ),
            url=(
                "https://help.salesforce.com/"
                "s/articleView?id=sf.remoteaccess_authenticate.htm"
                "&language=en_US&type=5"
            ),
            source_type="official_help",
            quote_or_excerpt=(
                "To improve the security of your OAuth "
                "and authentication provider implementations, "
                "use the OAuth 2.0 Proof Key for Code Exchange "
                "(PKCE) extension."
            ),
        ),

        # JWT
        Evidence(
            claim=(
                "Salesforce supports JSON Web Token "
                "(JWT)-based access tokens."
            ),
            url=(
                "https://help.salesforce.com/"
                "s/articleView?id=sf.remoteaccess_authenticate.htm"
                "&language=en_US&type=5"
            ),
            source_type="official_help",
            quote_or_excerpt=(
                "Salesforce supports two types of access "
                "tokens: opaque tokens and JSON Web Token "
                "(JWT)-based access tokens."
            ),
        ),

        # REST
        Evidence(
            claim=(
                "Salesforce provides a REST API with "
                "broad platform and object coverage."
            ),
            url=(
                "https://developer.salesforce.com/docs/"
                "atlas.en-us.api_rest.meta/api_rest/"
                "resources_list.htm"
            ),
            source_type="official_docs",
            quote_or_excerpt=(
                "The following table lists supported "
                "REST resources in the API and provides "
                "a brief description for each."
            ),
        ),

        # GraphQL
        Evidence(
            claim=(
                "Salesforce provides a GraphQL API."
            ),
            url=(
                "https://developer.salesforce.com/docs/"
                "platform/graphql/references/graphql"
            ),
            source_type="official_docs",
            quote_or_excerpt=(
                "GraphQL API provides a single endpoint "
                "that returns exactly what you request for."
            ),
        ),

        # MCP
        Evidence(
            claim=(
                "Salesforce provides hosted MCP servers."
            ),
            url=(
                "https://developer.salesforce.com/docs/"
                "platform/hosted-mcp-servers/overview"
            ),
            source_type="official_docs",
            quote_or_excerpt=(
                "Give AI agents a secure, governed way "
                "to interact with Salesforce data and "
                "automation using the Model Context Protocol."
            ),
        ),

        # Free Developer Edition
        Evidence(
            claim=(
                "Developers can sign up for a free ongoing "
                "Developer Edition environment."
            ),
            url=(
                "https://developer.salesforce.com/free-trials"
            ),
            source_type="official_docs",
            quote_or_excerpt=(
                "Start building on Salesforce for free "
                "with access to development environments "
                "for a range of platforms within the "
                "Salesforce ecosystem."
            ),
        ),
    ],

    confidence="high",
)


# --------------------------------------------------
# URLs that our research agent supposedly fetched
# --------------------------------------------------

fetched_urls = {
    "https://developer.salesforce.com/docs/"
    "atlas.en-us.api_rest.meta/api_rest/"
    "intro_oauth_and_connected_apps.htm",

    "https://help.salesforce.com/"
    "s/articleView?id=sf.remoteaccess_authenticate.htm"
    "&language=en_US&type=5",

    "https://developer.salesforce.com/docs/"
    "atlas.en-us.api_rest.meta/api_rest/"
    "resources_list.htm",

    "https://developer.salesforce.com/docs/"
    "platform/graphql/references/graphql",

    "https://developer.salesforce.com/docs/"
    "platform/hosted-mcp-servers/overview",

    "https://developer.salesforce.com/free-trials",
}


# --------------------------------------------------
# Run validation
# --------------------------------------------------

problems = validate_evidence(
    result=result,
    fetched_urls=fetched_urls,
)


# --------------------------------------------------
# Print result
# --------------------------------------------------

if problems:

    print("Validation FAILED:")

    for problem in problems:
        print(f"- {problem}")

else:

    print("Validation PASSED")

# --------------------------------------------------
# V5 source-text verification tests
# --------------------------------------------------

def test_source_excerpt_must_exist_in_fetched_content():
    source_url = (
        "https://example.com/auth"
    )

    valid_result = AppResearch(
        app="Example",
        website="https://example.com/",
        category="Test",
        description="Example app.",
        auth_methods=["API key"],
        credential_requirements="Create an API key.",
        self_serve="free",
        rest_api="yes",
        graphql_api="unknown",
        api_breadth="narrow",
        mcp_available="unknown",
        buildability="ready",
        main_blocker=None,
        evidence=[
            Evidence(
                claim="Example supports API key authentication.",
                url=source_url,
                source_type="official_docs",
                quote_or_excerpt="The API uses an API key to authenticate requests.",
            ),
            Evidence(
                claim="Example provides a REST API.",
                url=source_url,
                source_type="official_docs",
                quote_or_excerpt="The API is a REST API.",
            ),
        ],
        confidence="high",
    )

    fetched_urls = {source_url}
    fetched_content = {
        source_url: (
            "The API uses an API key to authenticate requests. "
            "The API is a REST API."
        )
    }

    problems = validate_evidence(
        result=valid_result,
        fetched_urls=fetched_urls,
        fetched_content=fetched_content,
    )

    assert not problems, problems


def test_fake_excerpt_is_rejected():
    source_url = (
        "https://example.com/auth"
    )

    invalid_result = AppResearch(
        app="Example",
        website="https://example.com/",
        category="Test",
        description="Example app.",
        auth_methods=["API key"],
        credential_requirements="Create an API key.",
        self_serve="free",
        rest_api="yes",
        graphql_api="unknown",
        api_breadth="narrow",
        mcp_available="unknown",
        buildability="ready",
        main_blocker=None,
        evidence=[
            Evidence(
                claim="Example supports API key authentication.",
                url=source_url,
                source_type="official_docs",
                quote_or_excerpt=(
                    "The API uses an API key and OAuth 2.0 "
                    "to authenticate requests."
                ),
            ),
            Evidence(
                claim="Example provides a REST API.",
                url=source_url,
                source_type="official_docs",
                quote_or_excerpt="The API is a REST API.",
            ),
        ],
        confidence="high",
    )

    fetched_urls = {source_url}
    fetched_content = {
        source_url: (
            "The API uses an API key to authenticate requests. "
            "The API is a REST API."
        )
    }

    problems = validate_evidence(
        result=invalid_result,
        fetched_urls=fetched_urls,
        fetched_content=fetched_content,
    )

    assert any(
        "Evidence excerpt was not found in the fetched source content"
        in problem
        for problem in problems
    )