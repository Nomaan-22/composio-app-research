import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from dotenv import load_dotenv
from composio import Composio
from google import genai
from google.genai import types as genai_types

from src.models import AppResearch
from src.validator import validate_evidence


load_dotenv()

COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not COMPOSIO_API_KEY:
    raise ValueError("COMPOSIO_API_KEY is not set")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set")


composio = Composio(
    api_key=COMPOSIO_API_KEY
)

# http_options timeout is a client-level safety net (ms). This alone does
# NOT reliably prevent every hang (some SDK paths, including automatic
# function-calling retries, can still stall past it), which is why every
# call site below is *also* wrapped in call_with_timeout(). Belt and
# suspenders: one catches SDK-internal hangs, the other catches everything
# else (network stalls, Composio calls, anything we haven't seen yet).
gemini = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=genai_types.HttpOptions(timeout=60_000),
)

# A single-worker executor used purely as a timeout wrapper for calls that
# don't natively support one (Composio's session.execute, and as a backstop
# around Gemini). This turns "hangs forever" into "raises TimeoutError after
# N seconds", which the retry logic in research_app()/orchestrate.py already
# knows how to handle.
_timeout_executor = ThreadPoolExecutor(max_workers=4)


def call_with_timeout(fn, *args, timeout: float, **kwargs):
    future = _timeout_executor.submit(fn, *args, **kwargs)
    try:
        return future.result(timeout=timeout)
    except FutureTimeoutError:
        raise TimeoutError(
            f"{getattr(fn, '__name__', fn)} timed out after {timeout}s"
        )


# =========================================================
# Search
# =========================================================

def web_search(session, query: str, timeout: float = 45.0):

    response = call_with_timeout(
        session.execute,
        tool_slug="COMPOSIO_SEARCH_WEB",
        arguments={
            "query": query
        },
        timeout=timeout,
    )

    return response.data.get(
        "citations",
        []
    )


# =========================================================
# Fetch
# =========================================================

def fetch_pages(
    session,
    citations,
    max_pages=3,
    timeout: float = 60.0,
):

    urls = []

    for citation in citations:

        url = citation.get("url")

        if url and url not in urls:
            urls.append(url)

        if len(urls) >= max_pages:
            break

    if not urls:
        return [], set()

    response = call_with_timeout(
        session.execute,
        tool_slug="COMPOSIO_SEARCH_FETCH_URL_CONTENT",
        arguments={
            "urls": urls,
            "text": True,
            # Raised from 10,000: content-heavy docs pages (Stripe, Slack)
            # were getting truncated before the relevant passage, so Gemini
            # would (correctly, from its training data) produce an excerpt
            # that was real but not inside the truncated window we actually
            # gave it — the validator then rejected a *true* quote. This is
            # a tradeoff (larger prompts, slower/costlier Gemini calls) but
            # it removes a whole class of false-positive validation failures.
            "max_characters": 25000,
        },
        timeout=timeout,
    )

    pages = response.data.get(
        "results",
        []
    )

    return pages, set(urls)


# =========================================================
# Targeted research
# =========================================================

def targeted_research(
    session,
    app_name: str,
    query: str,
    max_pages=3,
):

    print(f"\nResearching:")
    print(query)

    citations = web_search(
        session,
        query,
    )

    print(
        f"Search results: {len(citations)}"
    )

    pages, urls = fetch_pages(
        session,
        citations,
        max_pages,
    )

    print(
        f"Pages fetched: {len(pages)}"
    )

    return pages, urls


# =========================================================
# Evidence context
# =========================================================

def build_evidence_context(
    research_sections
):

    context = ""

    for section_name, pages in research_sections.items():

        context += (
            f"\n\n========== "
            f"{section_name.upper()} "
            f"==========\n"
        )

        for page in pages:

            context += f"""
SOURCE TITLE:
{page.get("title", "Unknown")}

SOURCE URL:
{page.get("url", "Unknown")}

SOURCE CONTENT:
{page.get("text", "")}

----------------------------------------
"""

    return context


# =========================================================
# Gemini analysis
# =========================================================

def analyze_with_gemini(
    app_name: str,
    website: str,
    category: str,
    evidence_context: str,
    previous_problems=None,
):

    previous_problems = previous_problems or []

    repair_context = ""

    if previous_problems:

        repair_context = f"""
IMPORTANT:

A previous analysis failed deterministic
evidence validation.

The validation problems were:

{chr(10).join(
    "- " + problem
    for problem in previous_problems
)}

You MUST specifically fix these problems
using the newly supplied evidence.
"""

    prompt = f"""
You are a technical product research analyst.

We are evaluating whether "{app_name}" can be
built as an AI-agent toolkit.

APPLICATION
-----------
Name: {app_name}
Website: {website}
Category: {category}


STRICT EVIDENCE RULES
---------------------

Use ONLY the supplied source material.

Do NOT use your internal knowledge to fill gaps.

Do NOT invent facts.

Do NOT invent URLs.

Do NOT cite a page that is not present
in the supplied source material.

If the evidence does not establish a fact,
return "unknown" where the schema allows it.

Every important factual claim must have
supporting Evidence.

QUOTE VERIFICATION REQUIREMENT
------------------------------

For quote_or_excerpt:

- Copy a short, verbatim excerpt from the supplied SOURCE CONTENT.
- Do not paraphrase the source.
- Do not invent or reconstruct quotations.
- The excerpt must be directly present in the supplied source content.
- Keep excerpts concise, preferably one or two sentences.

AUTHENTICATION EVIDENCE REQUIREMENT
-----------------------------------

Every authentication method listed in auth_methods
must be explicitly supported by at least one supplied
source.

For example, if you list:

- OAuth 2.0
- PKCE
- JWT

the supplied sources must contain evidence specifically
supporting each of those methods.

Do NOT list a method merely because it is commonly
associated with OAuth.

If a method is not directly supported by the supplied
sources, do not include it.


AUTHENTICATION
--------------

Identify authentication mechanisms explicitly
documented by the sources.

Do not infer an authentication method merely
because it is common for similar applications.

AUTH METHOD CLASSIFICATION
--------------------------

For auth_methods, focus on mechanisms a developer would
actually use to authorize API/tool access.

Do NOT automatically list every identity or security
technology mentioned in the documentation.

For example:

- OAuth 2.0 → include if used for API authorization
- API key → include if used for API access
- Basic authentication → include if used for API access
- Bearer token → include if directly documented as an API
  credential mechanism
- OAuth PKCE → treat as an OAuth flow/security extension,
  not necessarily a separate top-level auth method
- OpenID Connect → include only if the source establishes
  that it is directly relevant to API/tool authentication
- SAML → generally treat as SSO/federation rather than an
  API authentication method unless the evidence explicitly
  establishes API authentication through SAML

Prefer a smaller set of well-supported API authentication
methods over a long list of related identity technologies.

SELF-SERVE
----------

Classify access carefully:

"free"
    A developer can obtain a usable developer
    environment/credentials through a free
    self-serve path supported by the evidence.

"trial_or_paid"
    Access requires a trial or paid plan.

"gated"
    Admin approval, partnership, contact-sales,
    enterprise approval, or another explicit
    gate is required.

"unknown"
    Evidence is insufficient.

IMPORTANT:

A free developer environment does NOT automatically
mean unrestricted production access.

Use credential_requirements to explain this distinction.


API SURFACE
-----------

REST and GraphQL must each be supported independently.

Do not infer GraphQL from the existence of REST.

Do not infer REST from the existence of GraphQL.


MCP
---

Set mcp_available to "yes" only when the supplied
sources explicitly establish MCP support/server availability.

Do not infer MCP from generic AI-agent support.


API BREADTH
-----------

Use:

broad
moderate
narrow
unknown

Base this on the documented API surface.


BUILDABILITY
------------

ready:
The available API/tooling and access path appear
sufficient for an agent toolkit.

conditional:
Possible, but meaningful setup, paid access,
admin approval, or similar constraints exist.

blocked:
There is a fundamental blocker.

unknown:
Insufficient evidence.


CREDENTIAL REQUIREMENTS
-----------------------

Provide a concise explanation of how a developer
would actually obtain credentials/access.

This should distinguish:

- API availability
- credential availability
- free vs paid access
- admin approval
- partnership/contact-sales requirements


{repair_context}


SOURCE MATERIAL
---------------

{evidence_context}
"""

    response = call_with_timeout(
        gemini.models.generate_content,
        model="gemini-3.6-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": AppResearch,
            # This is the fix for the AFC warning in the logs. We pass no
            # tools, so there is nothing for automatic function-calling to
            # do — but leaving AFC on its default means the SDK can still
            # enter an internal multi-turn retry/function-calling loop on
            # certain responses, which is the most likely explanation for
            # the run silently stalling on the 3rd Stripe repair attempt
            # (right after "Pages fetched: 4", with no further output).
            # Disabling it makes generate_content a plain single-turn call.
            "automatic_function_calling": {"disable": True},
        },
        timeout=90.0,
    )

    result = AppResearch.model_validate_json(
        response.text
    )

    result.evidence = dedupe_evidence(result.evidence)

    return result


def dedupe_evidence(evidence_items):
    """
    Gemini occasionally emits near-duplicate evidence items (same URL,
    same claim) across the initial pass and repair passes, especially once
    build_evidence_context() has accumulated several research sections.
    Duplicates don't change correctness, but they do inflate the validator's
    problem list (the same broken excerpt gets reported twice, as happened
    with Stripe's docs.stripe.com/api/authentication) which makes repair
    queries noisier than they need to be.
    """
    seen = set()
    deduped = []
    for item in evidence_items:
        key = (item.url.rstrip("/"), item.claim.strip().lower())
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


# =========================================================
# Research one app
# =========================================================

def research_app(
    app_name: str,
    website: str,
    category: str,
    max_repair_attempts=2,
):

    session = composio.create(
        user_id="research-agent"
    )

    all_pages = {}
    all_fetched_urls = set()

    # -----------------------------------------------------
    # Initial targeted research
    # -----------------------------------------------------

    queries = {
        "authentication": (
            f"{app_name} official developer documentation "
            f"API authentication OAuth API key token credentials"
        ),

        "api_surface": (
            f"{app_name} official developer documentation "
            f"REST API GraphQL API endpoints API reference"
        ),

        "self_serve": (
            f"{app_name} official developer documentation "
            f"developer signup free trial API access credentials "
            f"pricing plan API availability self serve"
        ),

        "mcp": (
            f"{app_name} official MCP Model Context Protocol "
            f"MCP server developer documentation"
        ),
    }

    for section, query in queries.items():

        pages, urls = targeted_research(
            session,
            app_name,
            query,
        )

        all_pages[section] = pages
        all_fetched_urls.update(urls)

        # Respect Composio search throttling.
        time.sleep(0.7)

    # -----------------------------------------------------
    # Initial Gemini analysis
    # -----------------------------------------------------

    evidence_context = build_evidence_context(
        all_pages
    )

    result = analyze_with_gemini(
        app_name=app_name,
        website=website,
        category=category,
        evidence_context=evidence_context,
    )

    # -----------------------------------------------------
    # Verification / repair loop
    # -----------------------------------------------------

    # Cumulative history of every problem string ever seen for this app.
    # Previously only the *latest* round's problems were fed back to
    # Gemini, so a repair could silently reintroduce something an earlier
    # round had already fixed (this is what happened on Stripe: round 1
    # fixed excerpt issues, round 2's regenerated evidence then failed a
    # *different* check). Feeding the full history in doesn't guarantee
    # convergence, but it stops Gemini from re-breaking things it already
    # got right once.
    problem_history: set[str] = set()
    previous_round_problems: list[str] = []

    for attempt in range(
        max_repair_attempts + 1
    ):

        # Build URL -> raw fetched page text for source-grounded
        # evidence verification. This is rebuilt on every attempt
        # so repaired pages are included automatically.
        all_fetched_content = {}

        for pages in all_pages.values():
            for page in pages:
                url = page.get("url")
                text = page.get("text", "")

                if url and text:
                    all_fetched_content[url] = text

        problems = validate_evidence(
            result=result,
            fetched_urls=all_fetched_urls,
            fetched_content=all_fetched_content,
        )

        print(
            f"\nValidation attempt "
            f"{attempt + 1}:"
        )

        if not problems:

            print(
                "✓ Validation PASSED"
            )

            return result, attempt, True

        print(
            "✗ Validation FAILED"
        )

        for problem in problems:
            print(
                f"  - {problem}"
            )

        # Stagnation guard: if this round's problems are identical to (or a
        # subset of) last round's — i.e. the repair search + re-analysis
        # made zero net progress — stop burning time/API budget on further
        # rounds that are unlikely to converge, rather than always walking
        # all the way to max_repair_attempts. The app still gets a result;
        # it's just flagged as not fully validated via the return value.
        if (
            attempt > 0
            and previous_round_problems
            and set(problems) <= set(previous_round_problems)
        ):
            print(
                "\nNo progress vs. previous round — stopping repair "
                "loop early (stagnation guard)."
            )
            return result, attempt, False

        previous_round_problems = problems
        problem_history.update(problems)

        # No more repair attempts
        if attempt >= max_repair_attempts:
            print(
                "\nMaximum repair attempts reached."
            )

            return result, attempt, False

        # -------------------------------------------------
        # Repair search
        # -------------------------------------------------

        repair_query = (
            f"{app_name} official documentation "
            f"verify these research issues: "
            + "; ".join(problems)
        )

        print(
            "\nRunning repair research:"
        )

        print(repair_query)

        pages, urls = targeted_research(
            session,
            app_name,
            repair_query,
            max_pages=4,
        )

        all_pages[
            f"repair_{attempt + 1}"
        ] = pages

        all_fetched_urls.update(
            urls
        )

        time.sleep(0.7)

        # -------------------------------------------------
        # Re-run Gemini
        # -------------------------------------------------

        evidence_context = build_evidence_context(
            all_pages
        )

        result = analyze_with_gemini(
            app_name=app_name,
            website=website,
            category=category,
            evidence_context=evidence_context,
            # Full history, not just this round — see comment above.
            previous_problems=sorted(problem_history),
        )

    return result, max_repair_attempts, False


# =========================================================
# Test
# =========================================================

if __name__ == "__main__":

    result, attempts, validated = research_app(
        app_name="Salesforce",
        website="https://www.salesforce.com/",
        category="CRM and Sales",
        max_repair_attempts=2,
    )

    print(
        "\n\n========== FINAL RESULT ==========\n"
    )

    print(
        result.model_dump_json(
            indent=2
        )
    )

    print(
        f"\nRepair attempts used: {attempts}"
    )

    print(
        f"Fully validated: {validated}"
    )