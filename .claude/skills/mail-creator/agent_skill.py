"""
Minimal Python Agent Skill template

Usage (CLI):
  python agent_skill.py run-task --task hello --args '{"name":"Peter"}'

Provides a simple task registry and runner suitable as an agent skill starting point.
"""

import argparse
import json
import logging
from typing import Any, Callable, Dict

logging.basicConfig(level=logging.INFO)

_TASK_REGISTRY: Dict[str, Callable[..., Any]] = {}


def task(name: str | None = None):
    """Decorator to register a function as a task.

    Usage:
        @task("my_task")
        def my_task(a, b=1):
            return a + b
    """
    def decorator(fn: Callable[..., Any]):
        key = name or fn.__name__
        _TASK_REGISTRY[key] = fn
        return fn

    return decorator


def run_task(name: str, params: dict) -> Any:
    """Run a registered task by name with params dict.

    Raises SystemExit on unknown task.
    """
    fn = _TASK_REGISTRY.get(name)
    if not fn:
        available = ', '.join(sorted(_TASK_REGISTRY.keys())) or '<none>'
        raise SystemExit(f"Task '{name}' not found. Available: {available}")

    # Call the task with keyword args; allow the task to raise for errors.
    return fn(**params)


import os
import tempfile

from create_msg import create_mail as _create_mail
from sonarqube_api import create_project, create_project_token


@task("create_mail")
def create_mail_task(
    output: str,
    to: str = "",
    cc: str = "",
    bcc: str = "",
    subject: str = "",
    body: str = "",
    sender: str = "",
    template: str | None = None,
    template_vars: dict | None = None,
    html: bool = False,
    attachments: list | None = None,
    fmt: str = "auto",
) -> dict:
    """Create a mail file (.eml or .msg).

    Parameters
    ----------
    output      : output file path, e.g. "mail.eml"
    to          : comma-separated To recipients
    cc          : comma-separated CC recipients
    bcc         : comma-separated BCC recipients
    subject     : email subject (auto-filled when template is used)
    body        : plain-text or HTML body (auto-filled when template is used)
    sender      : sender email address (required, raises ValueError if empty)
    template    : built-in template name. Available: sonarqube_credential
    template_vars: placeholder values for the template, e.g. {"requester": "Alice", "project": "MyProject"}
    html        : treat body as HTML (default false)
    attachments : list of file paths to attach
    fmt         : output format — auto | eml | msg (auto uses eml on macOS/Linux)
    """
    path = _create_mail(
        output=output, to=to, cc=cc, bcc=bcc,
        subject=subject, body=body, sender=sender,
        template=template, template_vars=template_vars or {},
        html=html, attachments=attachments or [], fmt=fmt,
    )
    return {"saved_to": path}


@task("provision_sonarqube")
def provision_sonarqube_task(
    sonarqube_url: str,
    admin_token: str,
    project_key: str,
    project_name: str,
    # email params
    output: str,
    to: str = "",
    sender: str = "",
    cc: str = "",
    bcc: str = "",
    requester: str = "",
    html: bool = True,
    fmt: str = "auto",
    visibility: str = "private",
    token_name: str = "",
) -> dict:
    """Create a SonarQube project + non-expiring token, then send a credential email.

    Parameters
    ----------
    sonarqube_url : SonarQube server URL, e.g. "https://sonarqube.example.com"
    admin_token   : SonarQube admin authentication token
    project_key   : Unique project key in SonarQube
    project_name  : Display name of the project
    output        : Output mail file path, e.g. "mail.eml"
    to            : Recipient email address
    sender        : Sender email address
    cc            : CC recipients (comma-separated)
    bcc           : BCC recipients (comma-separated)
    requester     : Recipient's name used in the email greeting
    html          : Send HTML email (default true)
    fmt           : Mail format — auto | eml | msg
    visibility    : SonarQube project visibility — private | public (default private)
    token_name    : Name for the generated token (default: "{project_key}-ci-token")
    """
    if not token_name:
        token_name = f"{project_key}-ci-token"

    # 1. Create the SonarQube project
    logging.info("Creating SonarQube project: %s (%s)", project_name, project_key)
    create_project(
        url=sonarqube_url,
        admin_token=admin_token,
        project_key=project_key,
        project_name=project_name,
        visibility=visibility,
    )

    # 2. Generate a non-expiring project analysis token
    logging.info("Generating token '%s' for project '%s'", token_name, project_key)
    token_value = create_project_token(
        url=sonarqube_url,
        admin_token=admin_token,
        project_key=project_key,
        token_name=token_name,
    )

    # 3. Write credentials to a temp file (same format as xxx.txt)
    cred_path = os.path.join(tempfile.gettempdir(), f"{project_key}_credentials.txt")
    with open(cred_path, "w", encoding="utf-8") as f:
        f.write(f"Key: {project_key}\n")
        f.write(f"Token: {token_value}\n")
    logging.info("Credentials written to %s", cred_path)

    # 4. Send credential email using the sonarqube_credential template
    mail_path = _create_mail(
        output=output,
        to=to,
        cc=cc,
        bcc=bcc,
        sender=sender,
        template="sonarqube_credential",
        template_vars={"requester": requester, "project": project_name},
        attachments=[cred_path],
        html=html,
        fmt=fmt,
    )

    return {
        "project_key": project_key,
        "token_name": token_name,
        "credentials_file": cred_path,
        "mail_saved_to": mail_path,
    }


# Example task
@task("hello")
def hello(name: str = "world") -> dict:
    logging.info("Saying hello to %s", name)
    return {"message": f"Hello {name}!"}


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
        # Print JSON result to stdout for easy machine consumption
        print(json.dumps({"status": "ok", "result": result}, ensure_ascii=False))
    else:
        parser.print_help()


if __name__ == "__main__":
    _cli_run_task()
