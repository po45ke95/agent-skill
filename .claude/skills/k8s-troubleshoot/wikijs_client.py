"""
Wiki.js GraphQL API client for K8s documentation queries.

Authentication: API Key via Authorization: Bearer header

Configuration is loaded from a .env file located in the same directory as this
module. Environment variables take precedence over .env values.
"""

import os
from pathlib import Path
from typing import Any

import urllib.request
import urllib.error
import json


def _load_dotenv(path: Path) -> None:
    """Load key=value pairs from a .env file into os.environ (if not already set)."""
    if not path.is_file():
        return
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


_load_dotenv(Path(__file__).parent / ".env")

WIKIJS_URL = os.environ.get("WIKIJS_URL", "").rstrip("/")
WIKIJS_API_KEY = os.environ.get("WIKIJS_API_KEY", "")
WIKIJS_K8S_PATH_PREFIX = os.environ.get("WIKIJS_K8S_PATH_PREFIX", "docs/k8s")


def _graphql(query: str, variables: dict | None = None) -> dict:
    """Send a GraphQL request to wiki.js and return the parsed JSON response."""
    if not WIKIJS_URL:
        raise ValueError("WIKIJS_URL environment variable is not set")
    if not WIKIJS_API_KEY:
        raise ValueError("WIKIJS_API_KEY environment variable is not set")

    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        f"{WIKIJS_URL}/graphql",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {WIKIJS_API_KEY}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"wiki.js API HTTP {e.code}: {body}") from e

    if "errors" in data:
        msgs = [e.get("message", str(e)) for e in data["errors"]]
        raise RuntimeError(f"wiki.js GraphQL errors: {'; '.join(msgs)}")

    return data.get("data", {})


def search_pages(query: str, path_prefix: str | None = None, limit: int = 10) -> list[dict]:
    """Search wiki.js pages by keyword, optionally filtered by path prefix.

    Returns a list of page summaries: {id, title, description, path}.
    """
    prefix = path_prefix if path_prefix is not None else WIKIJS_K8S_PATH_PREFIX

    gql = """
    query SearchPages($query: String!) {
      pages {
        search(query: $query) {
          results {
            id
            title
            description
            path
            locale
          }
        }
      }
    }
    """
    data = _graphql(gql, {"query": query})
    results: list[dict] = data.get("pages", {}).get("search", {}).get("results", [])

    # Filter by path prefix (client-side) if prefix is specified
    if prefix:
        results = [r for r in results if r.get("path", "").startswith(prefix.lstrip("/"))]

    return results[:limit]


def get_page_by_path(path: str, locale: str = "en") -> dict[str, Any]:
    """Fetch full page content by path.

    Returns {id, title, description, content, path, updatedAt}.
    """
    gql = """
    query GetPage($path: String!, $locale: String!) {
      pages {
        singleByPath(path: $path, locale: $locale) {
          id
          title
          description
          content
          path
          updatedAt
        }
      }
    }
    """
    data = _graphql(gql, {"path": path, "locale": locale})
    page = data.get("pages", {}).get("singleByPath")
    if not page:
        raise ValueError(f"Page not found: {path}")
    return page


def get_page_by_id(page_id: int) -> dict[str, Any]:
    """Fetch full page content by numeric ID."""
    gql = """
    query GetPageById($id: Int!) {
      pages {
        single(id: $id) {
          id
          title
          description
          content
          path
          updatedAt
        }
      }
    }
    """
    data = _graphql(gql, {"id": page_id})
    page = data.get("pages", {}).get("single")
    if not page:
        raise ValueError(f"Page not found: id={page_id}")
    return page


def list_k8s_pages(locale: str = "en") -> list[dict]:
    """List all pages under the configured K8s path prefix.

    Returns a list of {id, title, path, description}.
    """
    gql = """
    query ListPages($locale: String!) {
      pages {
        list(locale: $locale) {
          id
          title
          path
          description
        }
      }
    }
    """
    data = _graphql(gql, {"locale": locale})
    pages: list[dict] = data.get("pages", {}).get("list", [])

    prefix = WIKIJS_K8S_PATH_PREFIX.lstrip("/")
    if prefix:
        pages = [p for p in pages if p.get("path", "").startswith(prefix)]

    return sorted(pages, key=lambda p: p.get("path", ""))
