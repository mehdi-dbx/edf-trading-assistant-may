# Cursor Plan: LangGraph PDF Report Generation Tool

## Objective
Build a LangGraph-compatible tool that takes structured agent output, renders it into
a branded HTML report using a Jinja2 template, and exports a PDF to a Databricks
Unity Catalog Volume path.

---

## Stack
- **Jinja2** — HTML templating
- **WeasyPrint** — HTML/CSS → PDF rendering (supports full CSS, embedded images)
- **Pydantic v2** — input validation for agent output
- **LangChain `@tool`** — exposes function to LangGraph agent
- **Databricks Unity Catalog Volume** — output destination (`/Volumes/...`)

---

## Project Structure to Create
```
report_tool/
├── __init__.py
├── pdf_tool.py              # @tool entry point for LangGraph
├── renderer.py              # Jinja2 + WeasyPrint logic
├── models.py                # Pydantic models for report_data
├── utils.py                 # Logo loading, path helpers
└── templates/
    └── report.html.j2       # Main HTML template
```

---

## Step-by-Step Instructions

### 1. `models.py` — Define report schema
- Create a Pydantic v2 `ReportInput` model with fields:
  - `customer_id: str`
  - `customer_name: str`
  - `logo_path: str` (absolute path on volume)
  - `data: ReportData` (nested model)
- Create `ReportData` with at minimum:
  - `summary: str`
  - `sections: list[ReportSection]`
  - `metrics: dict[str, Any]`
- Create `ReportSection` with `title: str` and `content: str`

### 2. `utils.py` — Helpers
- `load_logo_b64(path: str) -> str`
  - Read binary, base64-encode, return as data URI string (`data:image/png;base64,...`)
  - Handle png, jpg, svg
  - Raise clear error if file not found
- `get_output_path(customer_id: str, volume_base: str) -> Path`
  - Returns `/Volumes/.../reports/<customer_id>/report.pdf`
  - Creates parent dirs if they don't exist

### 3. `templates/report.html.j2` — HTML Template
- Professional layout with:
  - Header: embedded logo (via base64 data URI) + customer name + generation date
  - Summary section
  - Dynamic sections loop (`{% for section in data.sections %}`)
  - Metrics table (key/value pairs from `data.metrics`)
  - Footer with page numbers using CSS `@page` rules
- All styles inline in `<style>` block — no external CSS files
- Use `@page { margin: 2cm; }` for print margins
- Make it clean and professional — white background, subtle borders, readable font

### 4. `renderer.py` — Core rendering logic
- `render_html(report_input: ReportInput) -> str`
  - Load Jinja2 env from `templates/` directory
  - Pass `logo_b64`, `customer_name`, `data`, `generated_at` to template
  - Return rendered HTML string
- `render_pdf(html: str, output_path: Path) -> None`
  - Call `HTML(string=html).write_pdf(str(output_path))`
  - Wrap in try/except, raise descriptive errors

### 5. `pdf_tool.py` — LangGraph @tool
- Decorate with `@tool`
- Accept a single `input: dict` argument (agent passes JSON)
- Validate with `ReportInput(**input)` — let Pydantic raise on bad data
- Call `render_html` → `render_pdf` → return output path string
- Docstring must clearly describe what the tool does and what `input` dict shape it expects
  (LangGraph uses the docstring to decide when to call this tool)

---

## Configuration
- Use a `config.py` or env vars for:
  - `VOLUME_BASE_PATH` — e.g. `/Volumes/main/reporting/outputs`
  - `TEMPLATES_DIR` — absolute path to templates folder

---

## Databricks-Specific Notes
- **Production runs on Databricks:** WeasyPrint works on Databricks compute without extra apt-get. No DYLD or local-only code is needed there.
- **Local testing only:** For macOS with Homebrew Pango/Cairo, use `DYLD_LIBRARY_PATH=/opt/homebrew/lib` or the code marked "TEMPORARY LOCAL TESTING ONLY - REMOVE FOR DATABRICKS" in `agent_server/start_server.py`; remove that block before/for Databricks deployment.
- Unity Catalog Volume paths are mounted as local filesystem paths on compute
- Logos should be stored at: `/Volumes/.../logos/<customer_id>/logo.png`
- Output goes to: `/Volumes/.../reports/<customer_id>/report.pdf`

---

## Do NOT
- Do not use external CSS files or external image URLs in the template (WeasyPrint embedding issues)
- Do not use `file://` URLs for images — always base64-encode
- Do not block the event loop — WeasyPrint is sync, keep it that way
- Do not hardcode volume paths — use config/env vars

---

## Definition of Done
- [ ] All modules created with type hints throughout
- [ ] Pydantic model validates agent output before rendering
- [ ] Template renders correctly with logo, sections, and metrics table
- [ ] PDF is written to the correct Unity Catalog volume path
- [ ] `pdf_tool.py` registers cleanly as a LangGraph tool with a descriptive docstring
- [ ] Basic error handling with descriptive messages at each stage