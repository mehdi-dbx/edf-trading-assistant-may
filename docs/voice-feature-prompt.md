# PROMPT: Implement Voice Input via Microphone

Use this prompt in another Cursor session to reproduce the voice input feature in a similar chat codebase (Next.js/Vite frontend + Express server, chat with sendMessage).

**Reference implementation in this project:** See file paths and line numbers below.

---

## REFERENCE: Existing Implementation (This Project)

| What | File | Lines |
|------|------|-------|
| Multimodal input (voice logic + UI) | `app/client/src/components/multimodal-input.tsx` | 115-121, 167-240, 392-510 |
| Transcribe API | `app/server/src/index.ts` | 21, 25, 197-232 |
| Voice CSS | `app/client/src/index.css` | 272-289, 373-376 |
| App env (OPENAI) | `app.yaml` | 29-31 |
| Secret resource | `databricks.yml` | 35-39 |
| Secret setup | `deploy/setup_openai_secret.sh` | full file |
| Deploy call | `deploy/deploy.sh` | 28-30 |

---

## BACKEND

### 1. Dependencies
- Add `multer` and `@types/multer` if not present. Use `multer.memoryStorage()` for in-memory uploads.
- **Ref:** [app/server/src/index.ts](app/server/src/index.ts) L21, L25

### 2. Transcription Endpoint
Add `POST /api/audio/transcribe` in your Express server (e.g. `server/src/index.ts`).
- **Ref:** [app/server/src/index.ts](app/server/src/index.ts) L197-232

- **Middleware:** `upload.single('file')` where `upload = multer({ storage: multer.memoryStorage() })`
- **Validation:** Return 400 if `req.file` is missing
- **API key:** Read `process.env.OPENAI_API_KEY`; return 503 if not set
- **Forward to OpenAI:** POST to `https://api.openai.com/v1/audio/transcriptions` with:
  - `Authorization: Bearer ${apiKey}`
  - FormData: `file` (Blob from `file.buffer`, type `file.mimetype || 'audio/webm'`), `model: 'whisper-1'`
- **Response:** `res.json({ text })` on success; on error return `res.status(status).json({ error })`
- **Error handling:** Catch and return 502 with `{ error: 'Transcription failed' }`

---

## FRONTEND

### 1. State and Refs (in your multimodal/chat input component)
- **Ref:** [app/client/src/components/multimodal-input.tsx](app/client/src/components/multimodal-input.tsx) L115-121
```ts
type VoiceState = 'idle' | 'listening' | 'processing';
const [voiceState, setVoiceState] = useState<VoiceState>('idle');
const mediaRecorderRef = useRef<MediaRecorder | null>(null);
const streamRef = useRef<MediaStream | null>(null);
const chunksRef = useRef<Blob[]>([]);
const mimeTypeRef = useRef<string>('audio/webm');
```

### 2. Functions
- **Ref:** [multimodal-input.tsx](app/client/src/components/multimodal-input.tsx) L167-240
- **transcribe(blob):** FormData with `file` + blob as `recording.webm`, POST to `/api/audio/transcribe`, parse `{ text }`, throw on !res.ok
- **startRecording:** `getUserMedia({ audio: true })` → store stream, clear chunks, `MediaRecorder` with `audio/webm` or `audio/mp4` fallback, `ondataavailable` push to chunks, `start()`, `setVoiceState('listening')`. On error: `toast.error('Microphone access denied')`
- **stopRecording:** Stop MediaRecorder, stop stream tracks, clear refs. In `onstop`: build Blob from chunks, `setVoiceState('processing')`, call transcribe, then `submitForm(text)` if text.trim(), else `setVoiceState('idle')`. On transcribe error: toast, set idle
- **abortRecording:** Set `onstop` to only `setVoiceState('idle')`, stop recorder and tracks, clear refs

### 3. Button Layout (input row)
- **Ref:** [multimodal-input.tsx](app/client/src/components/multimodal-input.tsx) L392-510
Order: `[Textarea] [Waveform when listening] | [Paperclip] [Mic] [Cancel or Send]`

### 4. Mic Button – Three States

**Idle:** Regular Button, `onClick={startRecording}`, disabled when `status !== 'ready'` OR `uploadQueue.length > 0` OR `voiceState === 'processing'`, aria-label "Record voice message", icon `<Mic />`

**Listening:** Native `<button>` (not Button) with class `voice-mic-listening`, `onClick={stopRecording}`, aria-label "Stop recording", icon `<Mic />`. Exact classes: `voice-mic-listening flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-full border-none text-muted-foreground shadow-[0_0_4px_8px_rgba(254,226,226,0.5)] transition-colors hover:text-accent-foreground focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-0 disabled:pointer-events-none disabled:opacity-50 dark:shadow-[0_0_4px_10px_rgba(127,29,29,0.4)] [&_svg]:size-4`, plus `style={{ WebkitAppearance: 'none', appearance: 'none' }}` (L438-448)

**Processing:** Same Button as idle but shows `<Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />` instead of Mic, disabled, aria-label "Transcribing..." (L451-476)

### 5. Waveform (only when listening)
Render when `voiceState === 'listening'`. Container: `flex min-w-8 items-center justify-center gap-1 h-8 shrink-0 overflow-visible`, `aria-hidden`. Seven bars: `[0,1,2,3,4,5,6].map(i => <div key={i} className="min-w-[2px] w-0.5 rounded-full bg-muted-foreground/60" style={{ animation: 'voice-bar 1.2s ease-in-out infinite', animationDelay: `${i * 0.1}s` }} />)`

Position: Inside the same flex row as the textarea, between textarea and Paperclip button. (L409-426)

### 6. Cancel Button
Show when `voiceState === 'listening'` OR `status === 'submitted'` OR `status === 'streaming'`. Button variant ghost, size icon, `className="size-7 shrink-0 text-muted-foreground hover:text-foreground hover:bg-muted/80"`, aria-label "Cancel", `data-testid="cancel-button"`, icon `<X className="size-3.5" />`. On click: if listening → `abortRecording()`, else → `stop()` and `setMessages(m => m)`.

When Cancel is hidden, show the normal Send button instead. (L477-510)

### 7. CSS (add to index.css or global styles)
- **Ref:** [app/client/src/index.css](app/client/src/index.css) L272-289, L373-376

```css
/* Mic button tint when listening */
button.voice-mic-listening {
  background: rgba(254, 226, 226, 0.5) !important;
  -webkit-appearance: none !important;
  appearance: none !important;
}
button.voice-mic-listening:hover {
  background: rgba(254, 226, 226, 0.65) !important;
}
.dark button.voice-mic-listening {
  background: rgba(127, 29, 29, 0.3) !important;
}
.dark button.voice-mic-listening:hover {
  background: rgba(127, 29, 29, 0.45) !important;
}

@keyframes voice-bar {
  0%, 100% { height: 8px; }
  50% { height: 20px; }
}
```

---

## DEPLOYMENT (if using Databricks Apps)

- **app.yaml:** Add env `OPENAI_API_KEY` with `valueFrom: openai_api_key` — [app.yaml](app.yaml) L29-31
- **databricks.yml:** Add resource `openai_api_key` (secret scope + key), grant READ to app — [databricks.yml](databricks.yml) L35-39
- **setup script:** Create scope, put secret from `OPENAI_API_KEY` in `.env.local`; run before deploy — [deploy/setup_openai_secret.sh](deploy/setup_openai_secret.sh)
- **deploy.sh:** Call setup script if `OPENAI_API_KEY` is set — [deploy/deploy.sh](deploy/deploy.sh) L28-30

---

## ENV

- **Local:** `OPENAI_API_KEY` in `.env.local` for the Node server
- **Deployed:** Databricks secret, referenced via `valueFrom`

---

## FILES TO TOUCH (map to your project structure)

| Area | This project | Your project |
|------|--------------|--------------|
| Backend | `app/server/src/index.ts` | `server/src/index.ts` (or equivalent) |
| Frontend | `app/client/src/components/multimodal-input.tsx` | Your chat input component |
| CSS | `app/client/src/index.css` | Your global CSS |
| Deploy | `app.yaml`, `databricks.yml`, `deploy/setup_openai_secret.sh`, `deploy/deploy.sh` | Same if using Databricks Apps |
