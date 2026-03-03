# 11. Interaction Protocol (Voice, Vibration, Volume, Active Button)

This document defines the contract between the mobile client and the backend for
multisensory interaction.

## Input types

### 1) Voice input
Client sends a transcript (STT output):
```json
{ "type": "voice", "text": "Read my last 5 transactions." }
```

### 2) Control input (buttons)

Client converts hardware/on-screen interactions into a small set of events:

```json
{ "type": "control", "event": "NEXT" }
```

Allowed event values:

- `NEXT` (Volume Up)
- `PREV` (Volume Down)
- `REPEAT` (Active Button short press)
- `CONFIRM` (Active Button long press / hold)
- `CANCEL` (Active Button double press)

## Output directives

Backend returns:

- `tts_text`: what should be spoken
- `haptics.pattern`: what vibration pattern to play
- `audio_cue.id` (optional): short beep types
- `next_expected_controls`: a list of controls that make sense next (for UX guidance)

**Example:**

```json
{
  "tts_text": "Transaction 1 of 5. Credit, 100,000 won, Salary.",
  "haptics": { "pattern": "ITEM_TICK" },
  "next_expected_controls": ["NEXT", "PREV", "REPEAT", "CANCEL"]
}
```

## Pending actions (transfer drafts)

When a transfer is requested:

- Backend creates a pending action and returns:
  - `approval_required: true`
  - `action_token` (opaque)
- Backend must only finalize after a `CONFIRM` event referencing that token.

## Device context (optional)

Client may send:

- volume level (0.0–1.0)
- haptics enabled
- locale/timezone

Backend uses this to adjust prompts (e.g., advise increasing volume).