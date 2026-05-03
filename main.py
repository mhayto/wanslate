"""
WhatsApp EN <-> AR Translation Bot
Uses Meta WhatsApp Cloud API + Anthropic Claude for translation.
"""

import os
import re
import httpx
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="WhatsApp EN<>AR Translator")

# ── Config (set via environment variables) ────────────────────────────────────
WHATSAPP_TOKEN      = os.environ["WHATSAPP_TOKEN"]       # Meta permanent access token
WHATSAPP_PHONE_ID   = os.environ["WHATSAPP_PHONE_ID"]    # WhatsApp Business phone number ID
VERIFY_TOKEN        = os.environ["VERIFY_TOKEN"]         # Any secret string you choose
ANTHROPIC_API_KEY   = os.environ["ANTHROPIC_API_KEY"]

anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)

WHATSAPP_API_URL = (
    f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_ID}/messages"
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def is_arabic(text: str) -> bool:
    """Returns True if the message contains Arabic characters."""
    return bool(re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', text))


def translate(text: str, to_arabic: bool) -> str:
    """Translate text EN→AR or AR→EN using Claude."""
    direction = (
        "Translate the following English text into Arabic."
        if to_arabic else
        "Translate the following Arabic text into English."
    )
    prompt = (
        f"{direction}\n"
        "Return ONLY the translation — no explanation, no quotes, no preamble.\n\n"
        f"{text}"
    )
    response = anthropic.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


async def send_whatsapp_message(to: str, body: str) -> None:
    """Send a text message via the WhatsApp Cloud API."""
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(WHATSAPP_API_URL, json=payload, headers=headers)
    if resp.status_code != 200:
        logger.error("WhatsApp send failed: %s %s", resp.status_code, resp.text)
    else:
        logger.info("Message sent to %s", to)


# ── Webhook endpoints ─────────────────────────────────────────────────────────

@app.get("/webhook")
async def verify_webhook(request: Request):
    """Meta calls this once to verify the webhook URL."""
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == VERIFY_TOKEN
    ):
        return PlainTextResponse(params.get("hub.challenge", ""))
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def receive_message(request: Request):
    """Handles incoming WhatsApp messages."""
    data = await request.json()
    logger.info("Incoming payload: %s", data)

    try:
        entry    = data["entry"][0]
        change   = entry["changes"][0]["value"]

        # Ignore status updates (delivered, read receipts, etc.)
        if "messages" not in change:
            return {"status": "ignored"}

        message  = change["messages"][0]
        sender   = message["from"]          # e.g. "249912345678"
        msg_type = message.get("type")

        # Only handle text messages for now
        if msg_type != "text":
            await send_whatsapp_message(
                sender,
                "Sorry, I can only translate text messages. / آسف، أستطيع ترجمة الرسائل النصية فقط."
            )
            return {"status": "non-text ignored"}

        incoming_text = message["text"]["body"].strip()
        if not incoming_text:
            return {"status": "empty message"}

        # Detect language and translate
        arabic_input = is_arabic(incoming_text)
        translation  = translate(incoming_text, to_arabic=not arabic_input)

        direction_label = "🇬🇧→🇸🇩" if not arabic_input else "🇸🇩→🇬🇧"
        reply = f"{direction_label}\n{translation}"

        await send_whatsapp_message(sender, reply)

    except (KeyError, IndexError) as e:
        logger.warning("Unexpected payload shape: %s", e)

    return {"status": "ok"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
