---
name: k8s-troubleshoot
description: K8s troubleshooting assistant that queries a self-hosted wiki.js API for documentation. Use when the user reports a Kubernetes issue, error, or pod failure and wants diagnosis or remediation steps based on internal runbooks.
---

# K8s Troubleshoot

This skill queries a self-hosted **wiki.js** instance for Kubernetes documentation and uses the retrieved content as context for troubleshooting.

## Environment Setup

Set these environment variables before running:

| Variable | Description | Example |
|---|---|---|
| `WIKIJS_URL` | wiki.js base URL | `https://wiki.example.com` |
| `WIKIJS_API_KEY` | API key from wiki.js Admin > API Access | `eyJhbGci...` |
| `WIKIJS_K8S_PATH_PREFIX` | Path prefix to filter K8s pages | `/kubernetes` (default) |

## Quick Start

```bash
python agent_skill.py run-task --task <task_name> --args '<JSON>'
```

## Available Tasks

### `troubleshoot` — Main entry point for K8s issue diagnosis

Searches wiki.js for relevant docs and returns full page content for Claude to analyse.

**Parameters:**
- `issue` (string, required): description of the K8s problem
- `path_prefix` (string, optional): override the default K8s path filter
- `max_docs` (int, optional): max pages to retrieve, default `3`
- `locale` (string, optional): page locale, default `"en"`

**Example:**
```bash
python agent_skill.py run-task --task troubleshoot --args '{
  "issue": "pod stuck in Pending state, no nodes available"
}'
```

---

### `search_docs` — Search wiki.js for K8s documentation

**Parameters:**
- `query` (string, required): search keyword
- `path_prefix` (string, optional): path prefix filter
- `limit` (int, optional): max results, default `10`

**Example:**
```bash
python agent_skill.py run-task --task search_docs --args '{"query":"OOMKilled"}'
```

---

### `get_page` — Fetch full page content

**Parameters:**
- `path` (string): page path, e.g. `"/kubernetes/troubleshooting/oom-killed"`
- `page_id` (int): numeric page ID (alternative to path)
- `locale` (string, optional): default `"en"`

**Example:**
```bash
python agent_skill.py run-task --task get_page --args '{"path":"/kubernetes/troubleshooting/crashloop"}'
```

---

### `list_pages` — List all K8s pages in wiki.js

**Parameters:**
- `locale` (string, optional): default `"en"`

**Example:**
```bash
python agent_skill.py run-task --task list_pages --args '{}'
```

---

### `kubectl` — Execute kubectl commands against the cluster

Runs a kubectl command directly without querying wiki.js. Use for operational
tasks (create, delete, get, describe, logs) that don't require documentation lookup.

**Parameters:**
- `command` (string, required): kubectl subcommand and args, e.g. `"get pods -n default"`
- `context` (string, optional): kubeconfig context name (uses current context if omitted)

**Example:**
```bash
python agent_skill.py run-task --task kubectl --args '{"command":"get pods -A"}'
python agent_skill.py run-task --task kubectl --args '{"command":"describe pod nginx"}'
```

---

### `hello` — Smoke test

```bash
python agent_skill.py run-task --task hello --args '{"name":"Peter"}'
```

## Output Format

On success:
```json
{
  "status": "ok",
  "result": { ... }
}
```

## Workflow for Claude

When a user reports a K8s issue:

1. Call `troubleshoot` with the issue description → retrieves relevant wiki docs
2. Analyse the returned `wiki_docs[].content` (Markdown) against the reported symptoms
3. Provide a structured diagnosis:
   - **Root cause** (based on wiki runbook)
   - **Verification steps** (`kubectl` commands)
   - **Remediation steps**
   - **Reference** (wiki page path)

If `troubleshoot` returns no docs, fall back to `search_docs` with broader keywords, or call `list_pages` to browse available runbooks.

## Task Selection Strategy

Claude selects tasks based on the nature of the request to minimise token usage:

| Request type | Task to use | Queries wiki? |
|---|---|---|
| User reports a problem / error | `troubleshoot` | ✅ Yes |
| Manual doc lookup | `search_docs` / `get_page` / `list_pages` | ✅ Yes |
| Operational command (get/create/delete/logs) | `kubectl` | ❌ No |

Avoid calling `troubleshoot` for routine operations — it incurs extra API calls and
injects wiki content into the context unnecessarily.

## Notes

- Wiki.js GraphQL endpoint: `{WIKIJS_URL}/graphql`
- The skill uses the standard wiki.js 2.x/3.x GraphQL schema — no extra plugins needed
- Page content is returned as raw Markdown
- Path prefix matching is done client-side after the wiki full-text search
