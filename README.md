# Composio 100-App Research Orchestrator

Agentic research pipeline built for the **Composio AI Product Ops Intern take-home assignment**.

The system researches 100 apps and produces structured, evidence-backed findings covering:

- Authentication methods
- Self-serve vs gated access
- REST / GraphQL API availability
- API breadth
- MCP availability
- Buildability for an AI-agent toolkit
- Main blockers
- Supporting evidence and documentation URLs

## Case Study

**Live case study:**  
https://nomaan-22.github.io/composio-app-research/

The case study presents the findings, patterns across the 100 apps, research workflow, validation process, human verification, and individual app results.

## How It Works

For each app, the research agent:

1. Searches official developer documentation for authentication.
2. Researches the REST / GraphQL API surface.
3. Determines whether API access is self-serve or gated.
4. Checks for existing MCP support.
5. Synthesizes the findings into a structured JSON result.
6. Validates the claims against the fetched evidence.
7. Runs targeted repair research when validation fails.
8. Saves the final result as an individual JSON checkpoint.

This makes the workflow repeatable and allows completed apps to be skipped automatically.

## Validation & Repair

The first research result is **not automatically treated as correct**.

Validation checks include:

- Missing evidence
- Unsupported authentication methods
- Unsupported REST / GraphQL claims
- Unsupported self-serve classifications
- Evidence excerpts that cannot be found in fetched source content

When a validation check fails, the agent performs targeted repair research and validates the result again. Repair attempts are bounded to avoid endless loops.

The case study also includes an independent human verification sample and reports misses honestly.

## Running the Agent

### 1. Clone

```bash
git clone https://github.com/Nomaan-22/composio-app-research.git
cd composio-app-research
```

### 2. Create the virtual environment

Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure API credentials

Configure the API credentials required by the research pipeline as environment variables.

**Do not commit API keys or secrets to the repository.**

### 5. Research an app

```powershell
python -m src.orchestrate --app Salesforce
```

Multiple apps can be researched in one run:

```powershell
python -m src.orchestrate `
  --app Salesforce `
  --app HubSpot `
  --app Slack
```

Or run a small batch:

```powershell
python -m src.orchestrate --limit 5
```

Existing checkpoints are skipped automatically.

## Results

Individual research results are stored in:

[`src/results/`](./src/results/)

Each app has its own JSON file, for example:

```text
src/results/salesforce.json
src/results/hubspot.json
src/results/slack.json
```

These files contain the structured research result, evidence, validation status, and research metadata.

## Repository Structure

```text
composio-app-research/
│
├── index.html              # Interactive case study
├── README.md               # Project documentation
│
└── src/
    ├── orchestrate.py      # Research orchestrator
    ├── app_list.py         # 100 assignment apps
    └── results/            # Structured research outputs
        ├── salesforce.json
        ├── hubspot.json
        └── ...
```

## Human vs Agent

The agent handled the repetitive research work:

- documentation discovery
- source fetching
- structured synthesis
- evidence collection
- validation
- targeted repair research

Human involvement was used for independent verification and quality control, especially where automated research could not confidently establish a claim.

The system is intentionally transparent about uncertainty rather than assuming every first-pass answer is correct.

## Deliverables

**Live case study:**  
https://nomaan-22.github.io/composio-app-research/

**Source repository:**  
https://github.com/Nomaan-22/composio-app-research

**100 structured research results:**  
[`src/results/`](./src/results/)
