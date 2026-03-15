"""
SonarQube API helpers.

Requires:
    pip install requests

Requires SonarQube 9.5+ for PROJECT_ANALYSIS_TOKEN support.
"""

import requests


def _auth(admin_token: str) -> tuple[str, str]:
    """SonarQube uses HTTP Basic Auth with the token as the username."""
    return (admin_token, "")


def create_project(
    url: str,
    admin_token: str,
    project_key: str,
    project_name: str,
    visibility: str = "private",
) -> dict:
    """Create a SonarQube project.

    Returns the parsed JSON response from the API.
    Raises RuntimeError on HTTP or API errors.
    """
    endpoint = f"{url.rstrip('/')}/api/projects/create"
    resp = requests.post(
        endpoint,
        auth=_auth(admin_token),
        data={
            "project": project_key,
            "name": project_name,
            "visibility": visibility,
        },
        timeout=30,
    )
    if resp.status_code == 400:
        # SonarQube returns 400 with a JSON body describing the error
        body = _safe_json(resp)
        errors = "; ".join(e.get("msg", "") for e in body.get("errors", []))
        raise RuntimeError(f"SonarQube create_project failed: {errors or resp.text}")
    resp.raise_for_status()
    return resp.json()


def create_project_token(
    url: str,
    admin_token: str,
    project_key: str,
    token_name: str,
) -> str:
    """Create a non-expiring PROJECT_ANALYSIS_TOKEN for *project_key*.

    Returns the raw token string (only available at creation time).
    Raises RuntimeError on failure.
    """
    endpoint = f"{url.rstrip('/')}/api/user_tokens/generate"
    payload = {
        "name": token_name,
        "type": "PROJECT_ANALYSIS_TOKEN",
        "projectKey": project_key,
        # Omitting 'expirationDate' creates a token that never expires.
    }
    resp = requests.post(
        endpoint,
        auth=_auth(admin_token),
        data=payload,
        timeout=30,
    )
    if resp.status_code == 400:
        body = _safe_json(resp)
        errors = "; ".join(e.get("msg", "") for e in body.get("errors", []))
        if "PROJECT_ANALYSIS_TOKEN" in errors:
            raise RuntimeError(
                "SonarQube does not support PROJECT_ANALYSIS_TOKEN (requires 9.5+). "
                "Please upgrade your SonarQube instance."
            )
        raise RuntimeError(f"SonarQube create_project_token failed: {errors or resp.text}")
    resp.raise_for_status()
    return resp.json()["token"]


def _safe_json(resp: requests.Response) -> dict:
    try:
        return resp.json()
    except Exception:
        return {}
