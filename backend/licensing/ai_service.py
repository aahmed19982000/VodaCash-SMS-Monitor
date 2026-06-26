# backend/licensing/ai_service.py

import os
import json
import logging
import httpx
from django.utils import timezone
from .models import SMSPattern

logger = logging.getLogger(__name__)

class GeminiParserGenerator:
    """
    استخدام ذكاء اصطناعي (Gemini) لتحليل الرسائل الجديدة واكتشاف أنماطها تلقائياً.
    """
    @staticmethod
    def analyze_and_create_pattern(raw_sms: str, sender: str) -> bool:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.warning("⚠️ GEMINI_API_KEY environment variable is not set. Skipping AI auto-analysis.")
            return False

        # Prompts Gemini to parse the SMS structure and return clean regex pattern
        system_instruction = (
            "You are an expert regular expression (regex) developer. "
            "Analyze the structure of the provided SMS and construct a precise Python regex pattern "
            "that matches this SMS and similar future messages of the same transaction type.\n"
            "The regex must be compatible with Python's re.compile(pattern, re.IGNORECASE | re.DOTALL).\n"
            "Classify the SMS type into one of: RECEIVED, SENT, BILL, PURCHASE, TOPUP, BALANCE, ATM_WITHDRAWAL, ATM_DEPOSIT.\n"
            "Ensure capture groups are mapped correctly. The regex must capture:\n"
            "- amount: (\\d+(?:\\.\\d+)?)\n"
            "- counterpart: (\\d{11,14}) or name ([A-Za-z\\u0621-\\u064a\\s\\-\\*]+?)\n"
            "- balance: (\\d+(?:\\.\\d+)?)\n"
            "- trx_id: (\\d{10,15}) or (\\w{10,20})\n"
            "- date: (\\d{2}-\\d{2}-\\d{2}) or similar date formats\n"
            "- time: (\\d{2}:\\d{2}(?::\\d{2})?)\n\n"
            "You must return ONLY a JSON object with the following fields:\n"
            "{\n"
            "  \"type\": \"RECEIVED | SENT | BILL | PURCHASE | TOPUP | BALANCE | ATM_WITHDRAWAL | ATM_DEPOSIT\",\n"
            "  \"regex_pattern\": \"regex string pattern with capture groups\",\n"
            "  \"groups\": {\"amount\": 1, \"counterpart\": 2, ... (map each captured field to its group index (1-based))},\n"
            "  \"confidence\": 0.95\n"
            "}\n"
            "Do not include markdown code block syntax (like ```json) in your response, output raw JSON only."
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": f"SMS Message to analyze:\nSender: {sender}\nBody: {raw_sms}"}
                ]
            }],
            "systemInstruction": {
                "parts": [
                    {"text": system_instruction}
                ]
            },
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }

        try:
            response = httpx.post(url, json=payload, timeout=20.0)
            if response.status_code != 200:
                logger.error(f"Gemini API returned error status {response.status_code}: {response.text}")
                return False
            
            result = response.json()
            text_response = result['candidates'][0]['content']['parts'][0]['text']
            parsed_data = json.loads(text_response.strip())

            tx_type = parsed_data.get("type")
            regex_pat = parsed_data.get("regex_pattern")
            groups = parsed_data.get("groups", {})

            if not tx_type or not regex_pat:
                logger.error("Invalid response from Gemini AI: missing type or regex_pattern")
                return False

            import uuid
            pattern_id = f"auto_{tx_type.lower()}_{uuid.uuid4().hex[:6]}"
            SMSPattern.objects.create(
                pattern_id=pattern_id,
                type=tx_type,
                regex_pattern=regex_pat,
                groups_json=json.dumps(groups),
                is_active=True
            )
            logger.info(f"✨ Successfully auto-generated and saved pattern {pattern_id} for type {tx_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to auto-generate pattern using Gemini: {e}")
            return False
