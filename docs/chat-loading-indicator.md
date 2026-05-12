# Chat Loading Indicator

This document describes the loading indicator shown when the assistant is preparing a response. It enables an AI or developer to reproduce this behavior in a similar chat codebase.

## Overview

The loading indicator consists of:
1. **Three bouncing dots** – CSS-only animation
2. **Rotating status phrases** – "Thinking…", "Analysing…", "Almost there…" cycling every 7 seconds each
3. **Shimmering text** – Gradient sweep + brightness pulse on the status text

---

## 1. Three Bouncing Dots

### Behavior
- Three small circular dots that bounce in sequence
- Each dot scales from 0.6 to 1 and back, with opacity 0.5 → 1 → 0.5
- Staggered animation delays create a wave effect

### Code Location
**CSS:** `app/client/src/index.css` (around lines 291–303)

```css
@keyframes chat-dot-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

.chat-loading-dot {
  animation: chat-dot-bounce 1.4s ease-in-out infinite both;
}

.chat-loading-dot:nth-child(1) { animation-delay: 0s; }
.chat-loading-dot:nth-child(2) { animation-delay: 0.16s; }
.chat-loading-dot:nth-child(3) { animation-delay: 0.32s; }
```

**Component:** `app/client/src/components/chat-loading-indicator.tsx` (lines 95–99)

```tsx
<div className="flex gap-1" aria-hidden>
  {[0, 1, 2].map((i) => (
    <span key={i} className="chat-loading-dot size-1.5 rounded-full bg-current" />
  ))}
</div>
```

- Use `size-1.5` (or equivalent) for dot size
- Use `rounded-full bg-current` so dots inherit the parent text color
- `aria-hidden` hides the decorative dots from screen readers

---

## 2. Rotating Status Phrases

### Behavior
- Three phrases cycle: "Thinking…" → "Analysing…" → "Almost there…"
- Each phrase is visible for **7 seconds**
- Total cycle: 21 seconds
- Phrases are stacked with `position: absolute`; opacity keyframes control which one is visible

### Code Location
**Phrases constant:** `app/client/src/components/chat-loading-indicator.tsx` (line 3)

```tsx
const STATUS_PHRASES = ['Thinking…', 'Analysing…', 'Almost there…'];
```

**CSS keyframes:** `app/client/src/index.css` (lines 332–346)

```css
@keyframes chat-status-cycle-1 {
  0%, 33.33% { opacity: 1; }
  33.34%, 100% { opacity: 0; }
}

@keyframes chat-status-cycle-2 {
  0%, 33.33% { opacity: 0; }
  33.34%, 66.66% { opacity: 1; }
  66.67%, 100% { opacity: 0; }
}

@keyframes chat-status-cycle-3 {
  0%, 66.66% { opacity: 0; }
  66.67%, 100% { opacity: 1; }
}

.chat-status-phrase-1 { animation: chat-status-cycle-1 21s ease-in-out infinite; }
.chat-status-phrase-2 { animation: chat-status-cycle-2 21s ease-in-out infinite; }
.chat-status-phrase-3 { animation: chat-status-cycle-3 21s ease-in-out infinite; }
```

**Component markup:** `app/client/src/components/chat-loading-indicator.tsx` (lines 100–117)

```tsx
<div className="relative h-5 min-w-[120px] overflow-hidden">
  <span className="chat-loading-status chat-status-phrase-1 absolute inset-0 flex items-center">
    {STATUS_PHRASES[0]}
  </span>
  <span className="chat-loading-status chat-status-phrase-2 absolute inset-0 flex items-center">
    {STATUS_PHRASES[1]}
  </span>
  <span className="chat-loading-status chat-status-phrase-3 absolute inset-0 flex items-center">
    {STATUS_PHRASES[2]}
  </span>
</div>
```

- Parent needs `relative`, fixed height (e.g. `h-5`), `min-w-[120px]`, and `overflow-hidden`
- Each phrase needs `absolute inset-0` so they stack and only one is visible at a time

---

## 3. Shimmering Text

### Behavior
Two effects run together on the status text:
1. **Gradient sweep** – A highlight (brighter color) moves across the text every 2 seconds
2. **Brightness pulse** – The text brightness animates from 1 to 1.35 and back every 1.5 seconds

### Code Location
**Shimmer keyframes:** `app/client/src/index.css` (lines 305–330)

```css
@keyframes chat-status-shimmer {
  0% { background-position: 200% 50%; }
  100% { background-position: -200% 50%; }
}

@keyframes chat-status-glow {
  0%, 100% { filter: brightness(1); }
  50% { filter: brightness(1.35); }
}

.chat-loading-status {
  color: var(--muted-foreground);
  background: linear-gradient(
    90deg,
    var(--muted-foreground) 0%,
    var(--muted-foreground) 25%,
    var(--foreground) 50%,
    var(--muted-foreground) 75%,
    var(--muted-foreground) 100%
  );
  background-size: 200% 100%;
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
```

**Important:** The phrase cycle animations must include the shimmer and glow, otherwise they override them. Combine all three:

```css
.chat-status-phrase-1 {
  animation:
    chat-status-shimmer 2s ease-in-out infinite,
    chat-status-glow 1.5s ease-in-out infinite,
    chat-status-cycle-1 21s ease-in-out infinite;
}
.chat-status-phrase-2 {
  animation:
    chat-status-shimmer 2s ease-in-out infinite,
    chat-status-glow 1.5s ease-in-out infinite,
    chat-status-cycle-2 21s ease-in-out infinite;
}
.chat-status-phrase-3 {
  animation:
    chat-status-shimmer 2s ease-in-out infinite,
    chat-status-glow 1.5s ease-in-out infinite,
    chat-status-cycle-3 21s ease-in-out infinite;
}
```

### Theme Variables
The gradient uses `--muted-foreground` and `--foreground`. Ensure these exist in your theme (e.g. in `:root` and `.dark`).

---

## 4. When to Show the Indicator

### Condition 1: Streaming, last message is assistant, no text yet
**Location:** `app/client/src/components/message.tsx` (lines 595–605)

Show when:
- `message.role === 'assistant'`
- `isLoading === true` (e.g. `status === 'streaming'`)
- Message has no text parts: `!message.parts.some(p => p.type === 'text' && p.text?.trim())`

```tsx
{message.role === 'assistant' &&
  isLoading &&
  !message.parts.some(
    (p) => p.type === 'text' && (p as { text?: string }).text?.trim()
  ) && (
  <div className="mt-1">
    <ChatLoadingIndicator />
  </div>
)}
```

### Condition 2: Submitted, waiting for first response
**Location:** `app/client/src/components/messages.tsx` (lines 125–130)

Show when:
- `status === 'submitted'`
- `messages.length > 0`
- Last message is from user: `messages[messages.length - 1].role === 'user'`

```tsx
{status === 'submitted' &&
  messages.length > 0 &&
  messages[messages.length - 1].role === 'user' && (
  <AwaitingResponseMessage />
)}
```

`AwaitingResponseMessage` renders the same `ChatLoadingIndicator` component.

---

## 5. Component Structure Summary

```
ChatLoadingIndicator
├── Dots container (flex gap-1)
│   └── 3 × span.chat-loading-dot (size-1.5, rounded-full, bg-current)
└── Status container (relative, h-5, min-w-[120px], overflow-hidden)
    └── 3 × span.chat-loading-status.chat-status-phrase-N (absolute inset-0)
        └── STATUS_PHRASES[N]
```

---

## 6. File Reference

| What | File Path |
|------|-----------|
| CSS (dots, shimmer, glow, cycle) | `app/client/src/index.css` |
| ChatLoadingIndicator component | `app/client/src/components/chat-loading-indicator.tsx` |
| Show in message (streaming) | `app/client/src/components/message.tsx` |
| AwaitingResponseMessage | `app/client/src/components/message.tsx` |
| Show when submitted | `app/client/src/components/messages.tsx` |
