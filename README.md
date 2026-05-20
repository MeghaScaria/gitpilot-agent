# ⚡ GitPilot — DevOps Intelligence Agent

> Google Cloud Rapid Agent Hackathon · GitLab Track

GitPilot is an AI-powered DevOps agent that connects to your GitLab workspace
and helps software teams work faster by reasoning over real project data —
not just answering questions, but taking multi-step action.

## 🔴 Live Demo
👉 https://gitpilot-34658952945.us-central1.run.app

> Note: First load may take 10-15 seconds due to cold start.

## 🧠 What GitPilot Can Do
- **Prioritize Issues** — Analyzes open issues and ranks by severity and impact
- **Pipeline Triage** — Fetches CI/CD failure logs and diagnoses root causes
- **Standup Summaries** — Generates structured project summaries from live data
- **MR Review** — Lists and summarizes open merge requests
- **Multi-step Reasoning** — Chains multiple tool calls autonomously to fully
  answer questions without asking for project IDs or other manual input

## 🏗️ Architecture
User → FastAPI Backend → Gemini 2.5 Flash (Vertex AI, us-east5)
↓ autonomous tool calls
GitLab Tools (issues, pipelines, MRs, projects)
↓
Structured, actionable response

## 🛠️ Tech Stack
- **AI Model**: Gemini 2.5 Flash via Google Cloud Vertex AI
- **Agent Loop**: Google GenAI SDK (Python) with autonomous tool calling
- **Partner Integration**: GitLab API (issues, CI/CD pipelines, merge requests)
- **Backend**: FastAPI + Python
- **Hosting**: Google Cloud Run
- **Secrets**: Google Cloud Secret Manager

## 🚀 Run Locally

### Prerequisites
- Python 3.11+
- Google Cloud account with Vertex AI API enabled
- GitLab account with Personal Access Token (api, read_repository scopes)

### Setup
```bash
git clone https://github.com/YOUR_USERNAME/gitpilot-agent
cd gitpilot-agent
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

Create `.env`:
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_REGION=us-east5
GITLAB_TOKEN=your-gitlab-personal-access-token
GITLAB_URL=https://gitlab.com

Authenticate:
```bash
gcloud auth application-default login
```

Run:
```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload
```

Open http://localhost:8080

## 📁 Project Structure
gitpilot-agent/
├── agent/
│   ├── core.py          # Gemini agent loop with autonomous tool calling
│   └── prompts.py       # System prompt and agent behavior rules
├── tools/
│   └── gitlab_tools.py  # GitLab API tool wrappers
├── api/
│   └── main.py          # FastAPI backend with session management
├── frontend/
│   └── index.html       # Chat UI
├── Dockerfile
└── requirements.txt

## 📄 License
MIT
