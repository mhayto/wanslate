# WhatsApp EN ↔ AR Translation Bot — Setup Guide

## How it works
Any message sent to the bot's WhatsApp number is automatically translated:
- **English in → Arabic out** 🇬🇧→🇸🇩
- **Arabic in → English out** 🇸🇩→🇬🇧

Language detection is done locally (Arabic Unicode range check). Translation is handled by Claude.

---

## Step 1 — Meta / WhatsApp Business setup

1. Go to [developers.facebook.com](https://developers.facebook.com) and create an account if needed.
2. Create a new **App** → choose type **Business**.
3. In your app dashboard, add the **WhatsApp** product.
4. Under *WhatsApp → Getting Started*, Meta gives you a free **test phone number** and a temporary access token (valid 24h). Use this to test.
5. For production, you'll need to:
   - Create a **Meta Business Manager** account at business.facebook.com
   - Add a real dedicated phone number (must NOT be registered on any WhatsApp account)
   - Generate a **permanent access token** via a System User in Business Manager
6. Note down:
   - **Phone Number ID** (shown on the WhatsApp Getting Started page)
   - **Access Token**

---

## Step 2 — Configure environment

```bash
cp .env.example .env
# Edit .env with your values
```

Set `VERIFY_TOKEN` to any string you like — you'll enter the same string in the Meta dashboard.

---

## Step 3 — Run the bot

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

For production, run behind a reverse proxy (nginx) with HTTPS. Meta **requires** an HTTPS webhook URL.

If you don't have a domain, [ngrok](https://ngrok.com) is the fastest way to get a public HTTPS URL for testing:
```bash
ngrok http 8000
# Copy the https://xxxx.ngrok.io URL
```

---

## Step 4 — Register the webhook with Meta

1. In your Meta App dashboard → **WhatsApp → Configuration**
2. Set **Webhook URL** to: `https://your-domain.com/webhook`
3. Set **Verify Token** to the same value as your `VERIFY_TOKEN` env var
4. Click **Verify and Save** — Meta will call `GET /webhook` to confirm
5. Under **Webhook Fields**, subscribe to **messages**

---

## Step 5 — Test it

Send a message to your WhatsApp Business number from any phone. You should receive the translation back within a few seconds.

Test messages:
- English: `Hello, how are you?` → should reply in Arabic
- Arabic: `مرحبا كيف حالك` → should reply in English

---

## Deployment notes for Sudan / low-bandwidth context

- The bot itself uses very little data — just the WhatsApp API calls and a small Claude API request.
- Claude's translation is high quality for Sudanese Arabic (Modern Standard + some dialect awareness).
- If latency is a concern, you can swap Claude for the Google Translate API (free tier) — but quality will be lower for dialectal Arabic.
- Run this on the same server as your OSINT dashboard if possible.

---

## Files

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app — webhook verification + message handling + translation |
| `requirements.txt` | Python dependencies |
| `.env.example` | Environment variable template |
