# mobile/scratch/simulate_client.py
import asyncio
import json
import time
import sys
import os

# Add main directory to path to enable imports if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    import websockets
except ImportError:
    print("Error: 'websockets' library is not installed in the python environment.")
    print("Please run: pip install websockets")
    sys.exit(1)

# List of mock Vodafone Cash messages to send for testing
MOCK_SMS = [
    # 1. User's exact Sent Cash (Arabic)
    {
        "sender": "VodafoneCash",
        "body": "كسبت 10 جنيه كاش باك تستخدمها دقائق لفودافون اوميجابيتس ب 20 قرش الوحدة! ادخل علي تطبيق انا فودافون http://vf.eg/vfcash او اطلب\n *365*90#\n قبل آخر اليوم للاستمتاع بالهدية.\nتم تحويل 5 جنيه لرقم 01222820473 مصاريف الخدمة 1 جنيه رصيد حسابك فى فودافون كاش الحالي 71.31.\nتاريخ العملية: 11:32 26-05-21\nرقم العملية: 020173477469\n مع كل معاملة بفودافون كاش هتزود فرصتك انك تكسب جنيه دهب لست الحبايب ,حول، اشحن،جدد باقتك، وادفع فواتيرك علشان تزود فرصتك من خلال http://vf.eg/vfcash",
        "timestamp": int(time.time() * 1000)
    },
    # 2. User's exact Own Top-up (Arabic)
    {
        "sender": "VodafoneCash",
        "body": "تم شحن رصيد موبايلك ب 175 بنجاح وخصم 250 من محفظتك شاملة الضريبة; رصيد حسابك في فودافون كاش الحالي 77.31. تابع كل مصروفاتك من تاريخ المعاملات على أبلكيشن أنا فودافون http://vf.eg/vfcash",
        "timestamp": int(time.time() * 1000)
    },
    # 3. User's exact Received Cash (English Long)
    {
        "sender": "VodafoneCash",
        "body": "May 20, 2026 9:52:11 PM: Received EGP200 from 00201099437596 to Mobile Account Number 5786. Ref: 020161931051 Available Balance: 327.31",
        "timestamp": int(time.time() * 1000)
    },
    # 4. User's exact Own Top-up 20 EGP (Arabic)
    {
        "sender": "VodafoneCash",
        "body": "تم شحن رصيد موبايلك ب 14 بنجاح وخصم 20 من محفظتك شاملة الضريبة; رصيد حسابك في فودافون كاش الحالي 127.31. تابع كل مصروفاتك من تاريخ المعاملات على أبلكيشن أنا فودافون http://vf.eg/vfcash",
        "timestamp": int(time.time() * 1000)
    },
    # 5. User's exact Sent Cash (English)
    {
        "sender": "VodafoneCash",
        "body": "EGP 103 were successfully transferred to 01068586061 the transfer fee is EGP 1, your current Vodafone Cash balance is EGP 147.31\nTransaction date: 26-05-15 18:56\nTransaction ID: 020015669334\nWith every transaction you get more chances to win a Gold Coin for Mother's Day. Transfer, recharge & pay your bills through http://vf.eg/vfcash and increase your chances!",
        "timestamp": int(time.time() * 1000)
    }
]


async def send_mock_transactions():
    uri = "ws://localhost:8765"
    print(f"Connecting to {uri} to send simulation messages...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected successfully!")
            
            for index, sms in enumerate(MOCK_SMS, start=1):
                payload = {
                    "type": "NEW_SMS",
                    "payload": sms
                }
                
                print(f"\n[{index}/{len(MOCK_SMS)}] Sending mock SMS from '{sms['sender']}':")
                print(sms['body'])
                
                await websocket.send(json.dumps(payload))
                print("-> Sent! Check Flet desktop app UI.")
                
                # Sleep briefly between messages so the user can see them appear sequentially
                await asyncio.sleep(2.5)
                
            print("\nAll mock messages sent successfully!")
    except Exception as e:
        print(f"Error connecting to WebSocket server: {e}")
        print("Make sure the Desktop app is running and listening on port 8765.")

if __name__ == "__main__":
    asyncio.run(send_mock_transactions())
