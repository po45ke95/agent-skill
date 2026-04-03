# k8s-troubleshoot Agent Skill

A Claude Code agent skill for Kubernetes troubleshooting. It combines two capabilities:

1. **Wiki.js lookup** — searches your self-hosted wiki for runbooks and returns relevant docs as context for Claude to diagnose issues.
2. **kubectl execution** — runs kubectl commands directly against your local or remote cluster.

## Architecture

```
User reports K8s issue
        │
        ▼
 [troubleshoot task]        ←─ queries wiki.js for matching runbooks
        │
        ▼
 Claude analyses docs
        │
        ▼
 [kubectl task]             ←─ runs verification / remediation commands
```

For operational requests (create, delete, describe, logs), Claude skips the wiki
lookup and calls `kubectl` directly to save tokens.

## Setup

### Environment Variables

| Variable | Description | Example |
|---|---|---|
| `WIKIJS_URL` | wiki.js base URL | `https://wiki.example.com` |
| `WIKIJS_API_KEY` | API key from wiki.js Admin > API Access | `eyJhbGci...` |
| `WIKIJS_K8S_PATH_PREFIX` | Path prefix to filter K8s pages | `/kubernetes` (default) |

### Requirements

- Python 3.11+
- `kubectl` installed and kubeconfig configured (e.g. Rancher Desktop, minikube)

## Quick Start

```bash
# Smoke test
python agent_skill.py run-task --task hello --args '{"name":"Peter"}'

# Troubleshoot a K8s issue (queries wiki first)
python agent_skill.py run-task --task troubleshoot --args '{"issue":"pod stuck in Pending state"}'

# Run kubectl directly
python agent_skill.py run-task --task kubectl --args '{"command":"get pods -A"}'
```

## Available Tasks

| Task | Description | Queries wiki? |
|---|---|---|
| `troubleshoot` | Diagnose a K8s issue using wiki runbooks | ✅ |
| `search_docs` | Search wiki.js by keyword | ✅ |
| `get_page` | Fetch a specific wiki page by path or ID | ✅ |
| `list_pages` | List all K8s pages in wiki.js | ✅ |
| `kubectl` | Run a kubectl command against the cluster | ❌ |
| `hello` | Smoke test | ❌ |
