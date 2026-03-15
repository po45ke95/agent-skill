---
name: mail-creator
description: Create email files (.eml on macOS/Linux, .msg on Windows) from built-in templates or custom content. Use when the user wants to compose, draft, generate, or save an email file, or mentions SonarQube credential notifications.
---

# Mail Creator

This skill creates ready-to-open email files using `agent_skill.py` as a CLI runner and `create_msg.py` for the actual mail construction.

## Quick Start

Run tasks via:

```bash
python agent_skill.py run-task --task <task_name> --args '<JSON>'
```

## Available Tasks

### `create_mail` — Create an email file

**Minimum required parameters:**
- `output` (string): Output file path, e.g. `"mail.eml"`
- `sender` (string): Sender email address

**Optional parameters:**
- `to` (string): Comma-separated To recipients
- `cc` (string): Comma-separated CC recipients
- `bcc` (string): Comma-separated BCC recipients
- `subject` (string): Email subject
- `body` (string): Plain-text or HTML body
- `html` (bool): Set `true` to treat body as HTML (default `false`)
- `attachments` (list): File paths to attach, e.g. `["file.txt"]`
- `fmt` (string): `"auto"` | `"eml"` | `"msg"` (default `"auto"` — uses eml on macOS/Linux, msg on Windows)
- `template` (string): Built-in template name (see Templates section)
- `template_vars` (object): Placeholder values for the template

### `hello` — Smoke test

```bash
python agent_skill.py run-task --task hello --args '{"name":"Peter"}'
```

## Templates

### `sonarqube_credential`

Sends a SonarQube project credential notification with an attachment.

**Required `template_vars`:**
- `requester` — recipient's name shown in the greeting
- `project` — SonarQube project name

**Auto-filled fields:** subject, CC (`Peter.CH.Chang@acer.com`, `Jonas.Chung@acer.com`), attachment (`xxx.txt`), and body.

**Example:**

```bash
python agent_skill.py run-task --task create_mail --args '{
  "output": "mail.eml",
  "to": "alice@example.com",
  "sender": "Peter.CH.Chang@acer.com",
  "template": "sonarqube_credential",
  "template_vars": {"requester": "Alice", "project": "MyProject"},
  "html": true
}'
```

## Custom Email Example

```bash
python agent_skill.py run-task --task create_mail --args '{
  "output": "custom.eml",
  "to": "bob@example.com",
  "subject": "Meeting Tomorrow",
  "body": "Hi Bob, see you at 10am.",
  "sender": "peter@example.com"
}'
```

## Output

On success the command prints:

```json
{"status": "ok", "result": {"saved_to": "/absolute/path/to/mail.eml"}}
```

Open the saved `.eml` file with any mail client (Mail.app, Outlook, Thunderbird).

## Notes

- A personal signature (Peter CH Chang / Acer Inc.) is automatically appended to every message.
- `.msg` output requires Windows with Outlook and `pywin32` installed.
- If `attachments` reference files that do not exist, they are silently skipped.
