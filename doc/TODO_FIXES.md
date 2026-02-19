# Temporary TODO Fixes

## 1. 400 BAD_REQUEST — Assistant message with `tool_calls` missing tool result

**Error:**
```text
An assistant message with 'tool_calls' must be followed by tool messages responding to each 'tool_call_id'. The following tool_call_ids did not have response messages: call_fUgPKDgf69w7rxO4NXphBnuz
```

**Cause:** The `messages` array sent to the model API has an assistant message with `tool_calls` but no following message with `role: "tool"` (and `tool_call_id` matching that id). The API requires every `tool_call_id` to have a matching tool result message.

**Where to look:**
- **Client:** `e2e-chatbot-app-next/client/src/components/chat.tsx` — `prepareSendMessagesRequest` sends `previousMessages: messages`. If the client `messages` state has an assistant with tool_calls but no following tool message (e.g. after stream error/disconnect), the API will reject.
- **Stream / resume:** If the stream was interrupted before all tool results were emitted, the client may have assistant + tool_calls but missing tool result(s). On continue/retry, that incomplete state is sent.
- **Conversion:** `convertToModelMessages(uiMessages)` (server) — ensure it doesn’t drop or mis-map tool result messages when converting to API format.
- **DB history:** If loading from DB, ensure tool result messages are stored and loaded for assistant messages that have tool_calls.

**Fix:** Ensure every assistant message with `tool_calls` is immediately followed by one tool message per `tool_call_id`. Add a guard before calling the API to validate this, or fix the place where a tool result is lost (stream handling, resume, or conversion).

---

## 2. JSON parse error — "Expecting property name enclosed in double quotes: line 1 column 680"

**Error:**
```text
Expecting property name enclosed in double quotes: line 1 column 680 (char 679)
```

**Cause:** Python `json.loads()` is parsing a string and hits invalid JSON around character 679. Common causes: trailing comma before `}`/`]`, single quotes instead of double, truncated/streamed JSON, or unescaped character inside a string.

**Where it happens (Python tools):**
- `tools/email_report/email_tool.py` ~line 72: `data = json.loads(data)` when tool input is a string.
- `tools/pdf_report/pdf_tool.py` ~line 32: `payload = json.loads(report_payload)` — model-generated `report_payload`.
- `tools/pdf_report/download_reports_tool.py` ~line 34: `json.loads(input)`.

**Fix:**
1. Check the traceback to see which tool/file fails.
2. Log the raw string before `json.loads` (e.g. `len(s)` and slice around 679) to see the bad character.
3. Harden parsing: try stripping trailing commas before `}`/`]`, or catch `json.JSONDecodeError` and return a clear error.
4. Reduce malformed output from the model (prompt: "valid JSON only, no trailing commas"; or shorten payloads so the model is less likely to truncate).
