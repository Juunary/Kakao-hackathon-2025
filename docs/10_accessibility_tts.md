# 10. Accessibility Guidelines (Voice + Haptics + Buttons)

## Design goal
Optimize for listening and tactile interaction rather than visual scanning.

## Output style rules (TTS-first)
- One idea per sentence.
- Always include currency units (e.g., “won”).
- Use consistent phrasing for totals and confirmations.
- Avoid dense formatting (tables, long bullet lists).
- When reading lists: read one item at a time and offer navigation controls.

## Haptic feedback rules (examples)
- SUCCESS_SHORT: successful read/acknowledgment (balance found, command accepted)
- WARNING_PULSE: transfer draft created and awaiting confirmation
- ERROR_LONG: invalid request, insufficient funds, or tool failure
- ITEM_TICK: each transaction item read
- END_OF_LIST_DOUBLE: when user hits the end of a list

## Button guidance rules
### Volume buttons
Use Volume buttons as accessibility controls (client maps hardware buttons to events):
- Volume Up → NEXT
- Volume Down → PREV
For lists, always remind:
- “Press Volume Up for next, Volume Down for previous.”

### Active Button
Use Active Button for:
- Push-to-talk (client-side)
- REPEAT last message
- CONFIRM / CANCEL for sensitive actions (transfer)

## Volume level guidance
If `device_context.volume_level` is low (client-defined threshold), include a prompt:
- “Your volume seems low. Please press Volume Up.”

## Safety phrasing for transfers
- Never say “transfer completed” until confirmation is received.
- Before confirmation:
  - “I can prepare a transfer of 50,000 won. Hold the Active Button to confirm.”
- After confirmation:
  - “Confirmed. Your transfer of 50,000 won is completed.”