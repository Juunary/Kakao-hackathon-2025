# 07. API Contract (Voice + Control Events)

## Common notes
- Request/response are JSON.
- Client is responsible for STT/TTS and mapping haptics to OS APIs.
- Backend responses include:
  - `tts_text`
  - `haptics.pattern`
  - `audio_cue.id` (optional)
  - `next_expected_controls` (optional)

## 1) Health Check
### GET /healthz
Response 200:
```json
{ "ok": true }
```

## 2) Agent Turn (single endpoint for voice text + control events)

`POST /api/v1/agent/turn`

**Request (voice):**

```json
  "session_id": "s_001",
  "user_id": "u_123",
  "input": {
    "type": "voice",
    "text": "Read my last 5 transactions."
  },
  "device_context": {
    "volume_level": 0.35,
    "haptics_enabled": true
  }
}
```

**Request (control event from buttons):**

```json
{
  "session_id": "s_001",
  "user_id": "u_123",
  "input": {
    "type": "control",
    "event": "NEXT"
  },
  "device_context": {
    "volume_level": 0.35,
    "haptics_enabled": true
  }
}
```

**Response:**

```json
{
  "request_id": "req_opaque",
  "tts_text": "Transaction 2 of 5. Debit, 12,000 won, Coffee Shop.",
  "haptics": { "pattern": "ITEM_TICK" },
  "audio_cue": { "id": "NONE" },
  "meta": {
    "mode": "reading_transactions",
    "tools_used": [],
    "approval_required": false
  },
  "next_expected_controls": ["NEXT", "PREV", "REPEAT", "CANCEL"]
}
```

## 3) Transfer confirmation (optional explicit endpoint)

If you prefer separating confirmation from the agent endpoint, add:

`POST /api/v1/actions/confirm`

**Request:**

```json
{
  "session_id": "s_001",
  "user_id": "u_123",
  "action_token": "act_opaque_token",
  "control_event": "CONFIRM"
}
```

**Response:**

```json
{
  "request_id": "req_opaque",
  "tts_text": "Confirmed. Your transfer of 50,000 won has been completed.",
  "haptics": { "pattern": "SUCCESS_SHORT" },
  "meta": { "approval_required": false }
}
```

> **Security note:** The server must reject confirmation if the action token is invalid/expired
> or does not belong to the session/user.


