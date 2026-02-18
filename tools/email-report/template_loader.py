"""Load and parse the email template file."""

from pathlib import Path


def _template_dir() -> Path:
    return Path(__file__).resolve().parent


def load_template() -> tuple[str, str, str]:
    """Load email.template and return (subject_template, body_template, attachment_filename_template)."""
    path = _template_dir() / "email.template"
    if not path.exists():
        raise FileNotFoundError(f"Email template not found: {path}")
    raw = path.read_text(encoding="utf-8")

    subject = ""
    body = ""
    attachment_filename = ""

    section = None
    buf: list[str] = []
    for line in raw.splitlines():
        if line.strip() == "---SUBJECT---":
            section = "subject"
            buf = []
            continue
        if line.strip() == "---BODY---":
            if section == "subject" and buf:
                subject = "\n".join(buf).strip()
            section = "body"
            buf = []
            continue
        if line.strip() == "---ATTACHMENT_FILENAME---":
            if section == "body" and buf:
                body = "\n".join(buf).strip()
            section = "attachment"
            buf = []
            continue
        if section == "subject":
            buf.append(line)
        elif section == "body":
            buf.append(line)
        elif section == "attachment":
            buf.append(line)

    if section == "body" and buf:
        body = "\n".join(buf).strip()
    if section == "attachment" and buf:
        attachment_filename = "\n".join(buf).strip().split("\n")[0].strip()

    return subject, body, attachment_filename
