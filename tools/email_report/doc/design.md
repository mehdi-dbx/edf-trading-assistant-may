# Email Report Tool — Design

## Purpose

Send check-in performance report PDFs to airline contacts by email. Used after PDFs are generated (e.g. by `pdf_report_tool`) when the user asks to send or email reports to contacts.

## Overview

- **Tool**: `send_email_report_tool` (LangGraph `@tool`)
- **Provider**: [Resend](https://resend.com) (transactional email API)
- **Input**: One recipient per call — `to_email`, `contact_name`, `airline_name`, `pdf_path`, `period_label`
- **Output**: Success message or error description (string)

## Architecture

```
Agent → send_email_report_tool(input)
              │
              ├── load_template() → subject, body, attachment_filename (from email.template)
              ├── substitute(placeholders) → personalized subject, body, filename
              ├── Resolve PDF: /Volumes/... only → WorkspaceClient().files.download()
              ├── base64-encode PDF, build Resend params
              └── resend.Emails.send(params)
```

## Input (JSON object)

| Field           | Type | Description |
|-----------------|------|-------------|
| `to_email`      | str  | Recipient email address |
| `contact_name`  | str  | Name for greeting (e.g. "John Smith") |
| `airline_name`  | str  | Airline name for subject and attachment |
| `pdf_path`      | str  | Unity Catalog Volume path to PDF (e.g. as returned by `pdf_report_tool`). Must start with `/Volumes/`. |
| `period_label`  | str  | Report period for subject/body (e.g. "Jan 5-12, 2026") |

One call per recipient; the agent should call the tool once per contact.

## Template

- **File**: `tools/email_report/email.template`
- **Format**: Three sections separated by markers:
  - `---SUBJECT---` … subject line template
  - `---BODY---` … plain-text body template
  - `---ATTACHMENT_FILENAME---` … attachment filename template (single line used)

### Placeholders

| Placeholder      | Replaced with |
|------------------|----------------|
| `[Contact Name]` | `contact_name` (typo `[Contact Namel]` also supported) |
| `[Airline Name]` | `airline_name` |
| `[Period]`       | `period_label` |
| `[Period Long]`  | `period_label` |
| `[Airline]`      | Slug of airline (e.g. "Singapore_Airlines") |
| `[PeriodSlug]`   | Slug of period (e.g. "Jan5-12_2026") |

Body is converted to HTML (paragraphs and line breaks) before sending.

## PDF source

- **Volume path only** (`/Volumes/...`): PDF is read via Databricks `WorkspaceClient().files.download(pdf_path)`. Reports must be written to a Unity Catalog Volume (e.g. by `pdf_report_tool`). Local filesystem paths are not supported; the tool returns an error if `pdf_path` does not start with `/Volumes/`.

## Environment

| Variable        | Required | Default | Description |
|-----------------|----------|---------|-------------|
| `RESEND_API_KEY` | Yes     | —       | Resend API key; must be set to send emails |
| `EMAIL_FROM`    | No       | `Amadeus Airport Insights <onboarding@resend.dev>` | Sender address and display name |

## Limits

- **Attachment size**: Resend limit 40MB; the tool returns an error if the PDF exceeds 40MB.
- **One recipient per call**: The agent must invoke the tool once per contact when sending to multiple recipients.

## Error handling

- Missing `RESEND_API_KEY` → clear error message.
- Missing required input field → `Error: missing required input field <key>.`
- Template file not found → `FileNotFoundError` message.
- `pdf_path` not a Volume path → `Error: pdf_path must be a Unity Catalog Volume path (...). Local paths are not supported.`
- PDF not found on Volume → `Error: PDF file not found at <path>.`
- PDF > 40MB → `Error: PDF is larger than 40MB; Resend cannot send it.`
- Resend API failure → `Resend error: <message>`.

## Dependencies

- `resend` (Resend Python SDK)
- For Volume paths: `databricks.sdk` (WorkspaceClient)
