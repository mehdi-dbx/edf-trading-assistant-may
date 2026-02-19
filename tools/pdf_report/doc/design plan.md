# Cursor Plan: Incremental Build — PDF Report Tool

## Rule: One step at a time. Test before moving on. Do not proceed if previous step fails.

---

## Step 1 — Pydantic models only
Create `models.py` with `ReportSection`, `ReportData`, and `ReportInput`.
No logic, no files, just the schema.
**Test:** Instantiate a `ReportInput` object with dummy data in a `__main__` block and print it. It should validate and print cleanly.

---

## Step 2 — Logo utility only
Create `utils.py` with just `load_logo_b64(path: str) -> str`.
**Test:** Point it at any PNG on disk, print the first 80 chars of the returned string.
Should start with `data:image/png;base64,`.

---

## Step 3 — HTML template only (no Python)
Create `templates/report.html.j2` with hardcoded dummy values (no Jinja variables yet).
**Test:** Open it in a browser. It should look like a clean professional report layout
with a placeholder where the logo and sections will go.

---

## Step 4 — Jinja2 rendering only
Create `renderer.py` with `render_html(report_input: ReportInput) -> str`.
Wire up the template variables. No PDF yet.
**Test:** Call it with a dummy `ReportInput`, write the output to `test_output.html`,
open in browser. Logo should appear, sections should render correctly.

---

## Step 5 — WeasyPrint PDF export only
Add `render_pdf(html: str, output_path: Path) -> None` to `renderer.py`.
Write to a local path (not Databricks yet).
**Test:** Call it with the HTML string from Step 4, open the resulting PDF.
Check layout, logo, margins.

---

## Step 6 — Volume path helper
Add `get_output_path(customer_id: str, volume_base: str) -> Path` to `utils.py`.
**Test:** Call it with a dummy customer_id, assert the returned path matches expected
pattern and that dirs are created.

---

## Step 7 — Wire it all together in `pdf_tool.py`
Create the `@tool` function that calls models → utils → renderer → pdf export.
Still local paths, no Databricks.
**Test:** Call the function directly (not via agent) with a dict payload. Assert PDF exists at expected path.

---

## Step 8 — Databricks integration
Swap local output path for Unity Catalog volume path via env var `VOLUME_BASE_PATH`.
**Test:** Run on Databricks compute, confirm PDF appears in the volume via `%fs ls`.

---

## Step 9 — Plug into LangGraph agent
Register the tool with your agent and run an end-to-end test with a real agent invocation.
**Test:** Agent should call the tool, return the PDF path as output.