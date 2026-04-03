"""
K8s Troubleshooting Agent Skill

Queries a self-hosted wiki.js for Kubernetes documentation and provides
troubleshooting guidance based on the retrieved content.

Usage (CLI):
  python agent_skill.py run-task --task search_docs --args '{"query":"pod CrashLoopBackOff"}'
  python agent_skill.py run-task --task get_page --args '{"path":"/kubernetes/troubleshooting/crashloop"}'
  python agent_skill.py run-task --task list_pages --args '{}'

Environment variables:
  WIKIJS_URL              wiki.js base URL, e.g. https://wiki.example.com
  WIKIJS_API_KEY          wiki.js API key (generated in Administration > API Access)
  WIKIJS_K8S_PATH_PREFIX  path prefix to filter K8s docs, default: /kubernetes
"""

import argparse
import json
import logging
from typing import Any, Callable, Dict

logging.basicConfig(level=logging.INFO)

_TASK_REGISTRY: Dict[str, Callable[..., Any]] = {}


def task(name: str | None = None):
    """Decorator to register a function as a task."""
    def decorator(fn: Callable[..., Any]):
        key = name or fn.__name__
        _TASK_REGISTRY[key] = fn
        return fn
    return decorator


def run_task(name: str, params: dict) -> Any:
    """Run a registered task by name with params dict."""
    fn = _TASK_REGISTRY.get(name)
    if not fn:
        available = ', '.join(sorted(_TASK_REGISTRY.keys())) or '<none>'
        raise SystemExit(f"Task '{name}' not found. Available: {available}")
    return fn(**params)


import wikijs_client as wiki


@task("search_docs")
def search_docs_task(
    query: str,
    path_prefix: str | None = None,
    limit: int = 10,
) -> dict:
    """Search wiki.js for K8s documentation by keyword.

    Parameters
    ----------
    query       : search keyword, e.g. "pod CrashLoopBackOff"
    path_prefix : override the default K8s path prefix filter (optional)
    limit       : max number of results to return (default 10)
    """
    logging.info("Searching wiki.js for: %s", query)
    results = wiki.search_pages(query=query, path_prefix=path_prefix, limit=limit)
    return {
        "query": query,
        "count": len(results),
        "results": results,
    }


@task("get_page")
def get_page_task(
    path: str | None = None,
    page_id: int | None = None,
    locale: str = "en",
) -> dict:
    """Fetch full content of a wiki.js page by path or ID.

    Parameters
    ----------
    path    : page path, e.g. "/kubernetes/troubleshooting/oom-killed"
    page_id : numeric page ID (alternative to path)
    locale  : page locale, default "en"
    """
    if path:
        logging.info("Fetching wiki page by path: %s", path)
        page = wiki.get_page_by_path(path=path, locale=locale)
    elif page_id is not None:
        logging.info("Fetching wiki page by id: %s", page_id)
        page = wiki.get_page_by_id(page_id=page_id)
    else:
        raise ValueError("Either 'path' or 'page_id' must be provided")
    return page


@task("list_pages")
def list_pages_task(locale: str = "en") -> dict:
    """List all wiki.js pages under the configured K8s path prefix.

    Parameters
    ----------
    locale : page locale, default "en"
    """
    logging.info("Listing K8s pages from wiki.js (prefix: %s)", wiki.WIKIJS_K8S_PATH_PREFIX)
    pages = wiki.list_k8s_pages(locale=locale)
    return {
        "path_prefix": wiki.WIKIJS_K8S_PATH_PREFIX,
        "count": len(pages),
        "pages": pages,
    }


@task("troubleshoot")
def troubleshoot_task(
    issue: str,
    path_prefix: str | None = None,
    max_docs: int = 3,
    locale: str = "en",
) -> dict:
    """Search wiki.js for docs related to a K8s issue, then return the relevant content.

    This task is intended to be called by Claude as a first step in K8s troubleshooting.
    Claude should then analyse the returned content and provide a diagnosis.

    Parameters
    ----------
    issue      : description of the K8s problem, e.g. "pod stuck in Pending state"
    path_prefix: override path filter (optional)
    max_docs   : max number of wiki pages to retrieve full content for (default 3)
    locale     : page locale, default "en"
    """
    logging.info("Troubleshooting K8s issue: %s", issue)

    # 1. Full-text search; if empty, try individual keywords as fallback
    results = wiki.search_pages(query=issue, path_prefix=path_prefix, limit=max_docs * 2)

    if not results:
        keywords = [w for w in issue.replace("-", " ").split() if len(w) > 3]
        seen_ids: set[str] = set()
        for kw in keywords:
            for hit in wiki.search_pages(query=kw, path_prefix=path_prefix, limit=5):
                if hit["id"] not in seen_ids:
                    seen_ids.add(hit["id"])
                    results.append(hit)
            if len(results) >= max_docs * 2:
                break

    # 2. Title-based fallback: match keywords against known page titles
    if not results:
        keywords = [w.lower() for w in issue.replace("-", " ").split() if len(w) > 3]
        all_pages = wiki.list_k8s_pages(locale=locale)
        for page in all_pages:
            title = page.get("title", "").lower()
            if any(kw in title for kw in keywords):
                results.append(page)
            if len(results) >= max_docs * 2:
                break

    # 3. Last-resort fallback: return pages with "troubleshoot" in title
    if not results:
        logging.info("No keyword match found; falling back to troubleshooting pages")
        all_pages = wiki.list_k8s_pages(locale=locale)
        results = [p for p in all_pages if "troubleshoot" in p.get("title", "").lower()]

    if not results:
        return {
            "issue": issue,
            "wiki_docs": [],
            "note": "No matching documentation found. Try list_pages to browse available runbooks.",
        }

    # 3. Fetch full content for the top results
    docs = []
    for hit in results[:max_docs]:
        try:
            page = wiki.get_page_by_id(page_id=int(hit["id"]))
            docs.append({
                "title": page.get("title"),
                "path": page.get("path"),
                "updated_at": page.get("updatedAt"),
                "content": page.get("content", ""),
            })
        except Exception as e:
            logging.warning("Could not fetch page %s: %s", hit.get("path"), e)

    return {
        "issue": issue,
        "docs_retrieved": len(docs),
        "wiki_docs": docs,
    }


@task("kubectl")
def kubectl_task(command: str, context: str | None = None) -> dict:
    """Run a read-only kubectl command against the current kubeconfig context.

    Parameters
    ----------
    command : kubectl subcommand and args, e.g. "get pods -n default"
    context : kubeconfig context name to use (optional, uses current context if omitted)
    """
    import subprocess
    import shlex

    base = ["kubectl"]
    if context:
        base += ["--context", context]
    args = base + shlex.split(command)

    logging.info("Running: %s", " ".join(args))
    result = subprocess.run(args, capture_output=True, text=True)
    return {
        "command": " ".join(args),
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


@task("hello")
def hello(name: str = "world") -> dict:
    return {"message": f"Hello {name}! K8s troubleshoot skill is ready."}


def _cli_run_task(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="agent_skill")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("run-task", help="Run a registered task")
    p.add_argument("--task", required=True, help="Name of the task to run")
    p.add_argument("--args", default="{}", help="JSON object of keyword arguments")

    opts = parser.parse_args(argv)
    if opts.cmd == "run-task":
        try:
            params = json.loads(opts.args)
            if not isinstance(params, dict):
                raise ValueError("--args must be a JSON object")
        except Exception as e:
            raise SystemExit(f"Invalid --args value: {e}")

        result = run_task(opts.task, params)
        print(json.dumps({"status": "ok", "result": result}, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    _cli_run_task()
