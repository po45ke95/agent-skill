"""
Create a cross-platform mail file (.eml on macOS/Linux, .msg on Windows with Outlook).

Usage:
  python create_msg.py --to "alice@example.com" --subject "Hello" --body "Hi" --output "mail.eml"
  python create_msg.py --template sonarqube_credential --template-vars '{"requester":"Alice","project":"MyProject"}' --to "alice@example.com" --output "mail.eml"
  python create_msg.py --format msg --to "alice@example.com" --subject "Hello" --body "Hi" --output "C:\\temp\\mail.msg"

Note: .msg requires Windows with Outlook and pywin32 (pip install pywin32).
      .eml works on all platforms using only the Python standard library.
"""

import argparse
import json
import os
import sys

# ---------------------------------------------------------------------------
# Templates — each entry defines subject, body_plain, and body_html.
# Use {var_name} placeholders; supply values via template_vars dict.
# ---------------------------------------------------------------------------
TEMPLATES: dict[str, dict] = {
    "sonarqube_credential": {
        "subject": "SonarQube Project: {project} - Credential",
        "cc": "Peter.CH.Chang@acer.com, Jonas.Chung@acer.com",
        "attachments": ["xxx.txt"],
        "body_plain": "Dear {requester},\n\n    SonarQube Project: {project}\n    Credential is attached.\n",
        "body_html": (
            "<p>Dear {requester},</p>"
            "<p>&emsp;&emsp;SonarQube Project: <b>{project}</b><br>"
            "&emsp;&emsp;Credential is attached.</p>"
        ),
    },
}


def create_mail(
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
    attachments: list[str] | None = None,
    fmt: str = "auto",
) -> str:
    """Create a mail file (.eml or .msg) and return the saved path.

    template: name of a built-in template (see TEMPLATES). When provided,
              subject and body are filled from the template unless explicitly
              overridden by the caller.
    template_vars: dict of placeholder values, e.g. {"requester": "Alice", "project": "MyProject"}
    """
    if not sender:
        raise ValueError("sender is required")
    attachments = attachments or []
    template_vars = template_vars or {}

    # Standard HTML and plain-text signature appended to every message
    signature_html = (
        "<p>With kind regards,</p>"
        "<p><b>Peter CH Chang</b><br>"
        "Common Tech &amp; Services | Digital Marketing &amp; Common Services BU<br>"
        "Global IT | Acer Inc.<br>"
        "Tel: +886-2-2696-3131 #7145<br>"
        "<a href=\"mailto:Peter.CH.Chang@acer.com\">Peter.CH.Chang@acer.com</a></p>"
    )
    signature_plain = (
        "\nWith kind regards,\n\n"
        "Peter CH Chang\n"
        "Common Tech & Services | Digital Marketing & Common Services BU\n"
        "Global IT | Acer Inc.\n"
        "Tel: +886-2-2696-3131 #7145\n"
        "Peter.CH.Chang@acer.com\n"
    )

    # Apply template — fill subject, cc, and body if not explicitly provided
    if template:
        tmpl = TEMPLATES.get(template)
        if tmpl is None:
            raise ValueError(f"Unknown template '{template}'. Available: {', '.join(TEMPLATES)}")
        if not subject:
            subject = tmpl["subject"].format(**template_vars)
        if not cc and tmpl.get("cc"):
            cc = tmpl["cc"]
        if not attachments and tmpl.get("attachments"):
            attachments = list(tmpl["attachments"])
        if not body:
            body = (tmpl["body_html"] if html else tmpl["body_plain"]).format(**template_vars)

    out_fmt = fmt
    if out_fmt == "auto":
        out_fmt = "msg" if os.name == "nt" else "eml"

    out_path = os.path.abspath(output)
    out_dir = os.path.dirname(out_path)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    if out_fmt == "msg":
        if os.name != "nt":
            raise RuntimeError(".msg output requires Windows with Outlook. Use --format eml or run on Windows.")
        try:
            import win32com.client
        except Exception:
            raise RuntimeError("pywin32 is required for .msg output. Install with: pip install pywin32")

        olMSG = 3
        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)
        mail.To = to
        mail.CC = cc
        mail.BCC = bcc
        mail.Subject = subject
        if sender:
            mail.SentOnBehalfOfName = sender
        # Always append signature
        if html:
            full_html = (body or "") + signature_html
            mail.HTMLBody = full_html
        else:
            full_plain = (body or "") + signature_plain
            mail.Body = full_plain
        for p in attachments:
            p_abs = os.path.abspath(p)
            if os.path.exists(p_abs):
                mail.Attachments.Add(p_abs)
        mail.SaveAs(out_path, olMSG)

    else:  # eml
        import mimetypes
        from email.message import EmailMessage
        from email.policy import SMTP

        msg = EmailMessage()
        if to:
            msg["To"] = to
        if cc:
            msg["Cc"] = cc
        if bcc:
            msg["X-Bcc"] = bcc
        msg["Subject"] = subject
        msg["From"] = sender or ""

        # Append signature: produce HTML alternative and plain text fallback
        if html:
            full_html = (body or "") + signature_html
            # provide a minimal plain-text body as fallback
            msg.set_content((body or "") + signature_plain, subtype="plain")
            msg.add_alternative(full_html, subtype="html")
        else:
            msg.set_content((body or "") + signature_plain)

        for p in attachments:
            p_abs = os.path.abspath(p)
            if not os.path.exists(p_abs):
                continue
            ctype, _ = mimetypes.guess_type(p_abs)
            if ctype is None:
                ctype = "application/octet-stream"
            maintype, subtype = ctype.split("/", 1)
            with open(p_abs, "rb") as f:
                data = f.read()
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=os.path.basename(p_abs))

        with open(out_path, "wb") as f:
            f.write(msg.as_bytes(policy=SMTP))

    return out_path


def main():
    parser = argparse.ArgumentParser(description="Create a cross-platform mail file (.eml or .msg)")
    parser.add_argument("--to", default="", help="Comma-separated 'To' recipients")
    parser.add_argument("--cc", default="", help="Comma-separated 'CC' recipients")
    parser.add_argument("--bcc", default="", help="Comma-separated 'BCC' recipients")
    parser.add_argument("--subject", default="", help="Email subject")
    parser.add_argument("--body", default="", help="Plain text or HTML body")
    parser.add_argument("--html", action="store_true", help="Treat body as HTML")
    parser.add_argument("--attachments", nargs="*", default=[], help="Paths to files to attach")
    parser.add_argument("--output", required=True, help="Output file path (.eml or .msg)")
    parser.add_argument("--format", choices=["auto", "msg", "eml"], default="auto",
                        help="Output format: auto (detect by OS), msg (Windows+Outlook), eml (cross-platform)")
    parser.add_argument("--sender", default="", help="Sender email address")
    parser.add_argument("--template", default=None,
                        help=f"Template name. Available: {', '.join(TEMPLATES)}")
    parser.add_argument("--template-vars", default="{}", dest="template_vars",
                        help='JSON object of template placeholder values, e.g. \'{"requester":"Alice","project":"MyProject"}\'')

    args = parser.parse_args()

    try:
        template_vars = json.loads(args.template_vars)
        if not isinstance(template_vars, dict):
            raise ValueError("--template-vars must be a JSON object")
    except Exception as e:
        print(f"Error parsing --template-vars: {e}")
        sys.exit(1)

    try:
        out_path = create_mail(
            output=args.output,
            to=args.to,
            cc=args.cc,
            bcc=args.bcc,
            subject=args.subject,
            body=args.body,
            sender=args.sender,
            template=args.template,
            template_vars=template_vars,
            html=args.html,
            attachments=args.attachments,
            fmt=args.format,
        )
        print(f"Saved to: {out_path}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
