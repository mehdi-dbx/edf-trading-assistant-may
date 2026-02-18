# Agent request/response payload structure

## Request (POST /invocations)

```json
{
  "input": [
    { "role": "user", "content": "<message>" }
  ]
}
```

- **`input`** (array): Chat messages in OpenAI-style format. Each item has:
  - **`role`**: `"user"` | `"assistant"` | `"system"`
  - **`content`**: string (or array for multimodal)

Multi-turn: append `{"role": "assistant", "content": "..."}` and `{"role": "user", "content": "..."}` as needed.

---

## Response (200, non-streaming)

Top-level shape:

```json
{
  "object": "response",
  "output": [ ... ]
}
```

- **`object`**: `"response"` (fixed).
- **`output`** (array): List of **output items**. Each item is one message or artifact.

### Output item (message)

```json
{
  "type": "message",
  "id": "lc_run--<uuid>",
  "content": [
    {
      "type": "output_text",
      "text": "<assistant reply text>"
    }
  ],
  "role": "assistant"
}
```

- **`type`**: `"message"` for assistant messages.
- **`id`**: Run/message id (e.g. LangChain run id).
- **`content`**: Array of content blocks. For plain text: one block with `"type": "output_text"` and **`text`**.
- **`role`**: `"assistant"`.

### Other output item types

- **`response.output_item.done`** (streaming): event type used when building the non-streaming `output`; the **item** in that event is one of the objects above.
- Tool calls / tool results may appear as additional items in `output` (e.g. `type` and shape depend on MLflow/langchain response types).

---

## Example (successful run)

**Request:**

```json
{
  "input": [
    { "role": "user", "content": "What MCP tools do you have access to? List them." }
  ]
}
```

**Response:**

```json
{
  "object": "response",
  "output": [
    {
      "type": "message",
      "id": "lc_run--019c707b-6b10-77a2-8d50-cb4758729c4a",
      "content": [
        {
          "text": "I have access to these MCP tools (by namespace)...",
          "type": "output_text"
        }
      ],
      "role": "assistant"
    }
  ]
}
```

To get the assistant’s reply text: take the first (or only) item in `output` with `type === "message"`, then the first element of `content` with `type === "output_text"`, and use its `text` field.

---

## Error response (e.g. 500)

Body may be JSON:

```json
{ "detail": "<error message>" }
```

Example: `{"detail":"unhandled errors in a TaskGroup (1 sub-exception)"}` — indicates an exception in the agent (e.g. tool or Genie call). Check server logs for the underlying error.
