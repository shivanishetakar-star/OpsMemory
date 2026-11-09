# 🧠 OpsMemory
### AI-Assisted Historical Incident Investigation and Response Support

OpsMemory is a Python-based incident investigation prototype that uses historical incident memories to support technical teams during software service failures.

Instead of investigating every incident without historical context, OpsMemory retrieves relevant past incidents, identifies matching and related patterns, and generates an AI-assisted investigation report with supporting historical evidence.

---

## 1. Problem Statement

Software systems frequently experience incidents such as HTTP errors, service failures, deployment issues, and database connectivity problems.

During incident investigation, engineers often need to search through previous incident records to understand whether similar failures have occurred before.

This process can be time-consuming, particularly when historical incident information is scattered across different records.

OpsMemory addresses this problem by retrieving and analyzing historical incident information to support faster, evidence-informed investigation.

## 2. Project Objectives

- Retrieve relevant historical incident memories.
- Identify exact historical incident matches.
- Distinguish related incidents from exact matches.
- Retrieve historical resolution evidence.
- Generate an AI-assisted incident investigation report.
- Display supporting historical evidence through an Evidence Tracker.
- Clearly distinguish historical facts from assumptions and hypotheses.

## 3. Key Features

### Historical Memory Retrieval
Uses Hindsight to retrieve relevant historical incident information based on the current incident details.

### Evidence Classification
Classifies retrieved memories into:

- Exact Incident Matches
- Related Historical Patterns
- Historical Resolution Evidence

### AI-Assisted Investigation
Uses Hindsight's reflection capability to generate an investigation report using the retrieved evidence and supplied incident details.

### Evidence Tracker
Displays historical memory records associated with memory references cited in the generated investigation report.

### Duplicate Filtering
Removes exact duplicate memory text after normalizing whitespace and letter case.

### Investigation Report
Organizes the generated report into:

1. Current Incident
2. Relevant Historical Evidence
3. Root Cause Analysis
4. Recommended Next Steps

## 4. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core application logic |
| Streamlit | User interface |
| Hindsight | Historical memory retrieval and reflection |
| python-dotenv | Environment variable management |
| Regular Expressions | Text processing and evidence classification |
| JSON | Sample incident dataset |
| Git | Version control |

## 5. System Architecture

The application follows this investigation workflow:

1. User enters service, error and deployment information.
2. Application validates the Hindsight configuration.
3. Hindsight retrieves relevant historical memories.
4. Exact duplicate records are filtered.
5. Retrieved memories are classified into evidence categories.
6. Relevant evidence is passed to Hindsight for reflection.
7. An AI-assisted investigation report is generated.
8. Evidence Tracker displays the corresponding historical memory records.

## 6. Project Structure

```text
OpsMemory/
│
├── backend/
│   ├── app.py
│   ├── incidents.json
│   ├── seed_memory.py
│   ├── test_hindsight.py
│   └── .env
│
├── .gitignore
├── README.md
└── requirements.txt
```

The `.env` file contains local configuration and must never be committed to Git.

## 7. Installation and Setup

### Prerequisites

- Python 3
- pip
- Git
- Hindsight Cloud account and API credentials

### Step 1: Clone the repository

```bash
git clone https://github.com/shivanishetakar-star/OpsMemory.git
cd opsmemory
```

### Step 2: Create a virtual environment

```bash
python3 -m venv backend/.venv
```

### Step 3: Activate the virtual environment

```bash
source backend/.venv/bin/activate
```

### Step 4: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Configure environment variables

Create a `.env` file inside the `backend` directory.

Add your own Hindsight configuration:

```env
HINDSIGHT_API_KEY=your_api_key
HINDSIGHT_BASE_URL=your_base_url
HINDSIGHT_BANK_ID=your_bank_id
```

Replace the placeholder values with your actual configuration.

Never publish API credentials.

### Step 6: Run the application

```bash
cd backend
streamlit run app.py
```

Streamlit will provide a local URL to access the application.

## 8. Sample Incident Dataset

The project includes a sample JSON dataset containing five incident records.

The sample records cover:

- Payment API HTTP 502 errors
- Payment API HTTP 500 errors
- User API HTTP 503 errors
- Order API HTTP 502 errors
- Database connection exhaustion
- Redis connection failures
- Upstream service timeouts

These records provide sample historical incident scenarios for the prototype.

## 9. Testing and Validation

The prototype was manually evaluated using three regression scenarios.

| Test | Input | Expected Behaviour |
|---|---|---|
| Test 1 | Payment API, HTTP 500, v2.5 | Identify matching historical evidence |
| Test 2 | Payment API, HTTP 502, v2.6 | Separate exact matches from related incidents |
| Test 3 | Payment API, HTTP 404, v9.9 | Report no exact historical match and distinguish hypotheses |

The three scenarios produced the intended high-level behaviour during manual testing.

**Testing limitation:** These are manually executed regression scenarios, not an automated unit-test suite. Hindsight retrieval and AI-generated output can vary depending on the available memories and model response.

## 10. Security Considerations

- API credentials are stored in environment variables.
- `.env` files are excluded through `.gitignore`.
- Virtual environments are excluded from version control.
- The application uses historical incident information supplied to the memory system.
- No live production credentials should be included in sample datasets or public repositories.

## 11. Current Limitations

OpsMemory is currently a prototype.

- It does not connect directly to live production monitoring systems.
- It does not automatically detect production incidents.
- It does not execute deployments, rollbacks or service restarts.
- Evidence classification currently uses rule-based text matching.
- Duplicate filtering removes exact normalized duplicates, not semantically equivalent records.
- The Evidence Tracker displays referenced memory records but does not independently verify whether every generated claim is semantically supported by its citation.
- Root cause suggestions must be validated by a human engineer.

OpsMemory is intended to support investigation, not replace engineering judgment.

## 12. Future Enhancements

Potential improvements include:

- Automated unit and integration testing.
- Stronger semantic evidence classification.
- Independent citation-support validation.
- Integration with monitoring and observability platforms.
- Structured incident severity assessment.
- Better historical memory ranking.
- Investigation report export.
- Role-based access control and audit logging.
- Human-reviewed incident resolution workflows.

## 13. Demo Workflow

For a demonstration:

1. Start the Streamlit application.
2. Enter a service name.
3. Enter an HTTP error code.
4. Enter a deployment version.
5. Run the investigation.
6. Review exact historical matches.
7. Compare related historical patterns.
8. Examine historical resolution evidence.
9. Read the AI-assisted investigation report.
10. Open the Evidence Tracker to inspect referenced memories.

## 14. Project Status

**Status:** Working prototype

**Project Name:** OpsMemory

**Category:** AI-Assisted Software Incident Investigation

**Primary Technologies:** Python, Streamlit and Hindsight

---

*OpsMemory aims to make historical incident knowledge more accessible and useful during software troubleshooting and incident investigation.*
## Architecture Documentation

For detailed system architecture, incident investigation workflow, and evidence retrieval sequence, see [Architecture Documentation](docs/architecture.md).