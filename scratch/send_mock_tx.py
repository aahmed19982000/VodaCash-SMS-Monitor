import asyncio
import json
import websockets
import sys
from datetime import datetime

async def send_mock():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        # Create a mock transaction
        tx_payload = {
            "transaction_id": "mock_tx_999",
            "type": "SENT",
            "amount": 7.00,
            "balance_after": 120.00,
            "counterpart": "+201012345678",
            "raw_sms": "تم تحويل 7 جنيه إلى 01012345678 بنجاح. رقم العملية 999.",
            "parsed_at": datetime.now().isoformat(),
            "sms_timestamp": datetime.now().isoformat(),
            "confidence": 1.0,
            "wallet_id": "vodafone_cash"
        }
        
        msg = {
            "type": "NEW_TRANSACTION",
            "payload": tx_payload,
            "sent_at": datetime.now().isoformat()
        }
        
        await websocket.send(json.dumps(msg))
        print("Mock transaction sent successfully!")

if __name__ == "__main__":
    asyncio.run(send_mock())
