# 00. Overview

## Problem
Low-vision users often struggle with screen-first mobile banking UIs. This project provides a backend
for a mobile client that enables banking tasks using **voice + multisensory controls**:

- Voice for intent and content
- Haptics/vibration for immediate feedback
- Volume buttons for hands-free navigation and quick commands
- An Active Button for push-to-talk and explicit confirmation of sensitive actions

## What the backend provides
- A safe “Voice-to-Action” agent that interprets user intents and calls permission-controlled tools
- Structured responses that the client can render via:
  - TTS text
  - vibration patterns
  - optional audio cues
  - guidance for Active Button / Volume Button usage

## What the backend does NOT provide (by default)
- Speech-to-Text (STT)
- Text-to-Speech (TTS)
- OS-level vibration/audio playback

Instead, the backend returns **TTS-ready text and feedback directives** for the client.

## Core user journeys
1) Balance inquiry (voice)
- User: “What’s my balance?”
- Backend: Calls balance tool → returns TTS + success vibration

2) Recent transactions (voice + volume buttons)
- User: “Read my last 5 transactions.”
- Backend: Calls transactions tool → reads first item, then user presses Volume Up/Down to move through items

3) Transfer (voice + active button confirmation + haptics)
- User: “Send 50,000 won to Mom.”
- Backend: Creates a transfer draft, returns summary + warning vibration + “Hold the Active Button to confirm.”
- Client sends a confirm control event when Active Button is held/pressed as required.
- Backend executes finalization only after confirmation.

## Success criteria (high-level)
- Correct tool usage (no hallucinated arguments)
- No unauthorized DB access (LLM never runs SQL)
- Clear, TTS-friendly responses + consistent haptic/button guidance
- Safe handling of sensitive actions via explicit confirmation events