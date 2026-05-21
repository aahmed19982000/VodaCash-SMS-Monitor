# desktop/server.py
# ── WebSocket Server لاستقبال البيانات من الموبايل ────────────────────────

import asyncio
import json
import logging
from datetime import datetime
from typing import Set, Callable, Optional

import websockets
from websockets.server import WebSocketServerProtocol

from shared.config import WEBSOCKET_HOST, WEBSOCKET_PORT, CONNECTION_TIMEOUT
from shared.models import Transaction, TransactionType, UnclassifiedSMS
from shared.protocol import (
    parse_message,
    make_heartbeat_ack,
    make_sync_request,
    MessageType,
)

logger = logging.getLogger("VodaCash.Server")


class DesktopServer:
    """
    WebSocket Server يعمل على سطح المكتب لاستقبال بيانات الموبايل.

    المسؤوليات:
    ─────────────────────────────────────────────────────
    1. الاستماع لاتصالات الموبايل عبر WebSocket
    2. استقبال العمليات الجديدة وتحديثات الرصيد
    3. الرد على Heartbeat للحفاظ على الاتصال
    4. إرسال طلبات المزامنة (Sync Request)
    5. إدارة عدة اتصالات متزامنة (عدة موبايلات)
    6. تمرير البيانات لـ Callbacks للمعالجة (UI / DB)
    """

    def __init__(self, host: str = None, port: int = None):
        self._host = host or WEBSOCKET_HOST
        self._port = port or WEBSOCKET_PORT
        self._clients: Set[WebSocketServerProtocol] = set()
        self._running = False
        self._server = None

        # Callbacks
        self._on_transaction: Optional[Callable] = None
        self._on_balance_update: Optional[Callable] = None
        self._on_unclassified: Optional[Callable] = None
        self._on_client_connected: Optional[Callable] = None
        self._on_client_disconnected: Optional[Callable] = None

        # إحصائيات
        self._received_count = 0
        self._start_time: Optional[datetime] = None

    # ═════════════════════════════════════════════════════════════════════
    # تسجيل Callbacks
    # ═════════════════════════════════════════════════════════════════════

    def on_transaction(self, callback: Callable):
        """عند استقبال عملية مصنفة جديدة."""
        self._on_transaction = callback

    def on_balance_update(self, callback: Callable):
        """عند تحديث الرصيد."""
        self._on_balance_update = callback

    def on_unclassified(self, callback: Callable):
        """عند استقبال رسالة غير مصنفة."""
        self._on_unclassified = callback

    def on_client_connected(self, callback: Callable):
        """عند اتصال موبايل جديد."""
        self._on_client_connected = callback

    def on_client_disconnected(self, callback: Callable):
        """عند انقطاع اتصال موبايل."""
        self._on_client_disconnected = callback

    # ═════════════════════════════════════════════════════════════════════
    # التشغيل والإيقاف
    # ═════════════════════════════════════════════════════════════════════

    async def start(self):
        """بدء السيرفر."""
        self._running = True
        self._start_time = datetime.now()

        self._server = await websockets.serve(
            self._handle_client,
            self._host,
            self._port,
            ping_interval=None,  # نتحكم بالـ heartbeat يدوياً
            ping_timeout=None,
        )

        logger.info(f"🟢 Server listening on ws://{self._host}:{self._port}")
        await self._server.wait_closed()

    async def stop(self):
        """إيقاف السيرفر."""
        self._running = False

        # إغلاق كل الاتصالات
        for client in list(self._clients):
            await client.close(1001, "Server shutting down")

        if self._server:
            self._server.close()
            await self._server.wait_closed()

        logger.info("🛑 Server stopped")

    def run(self):
        """تشغيل السيرفر (blocking)."""
        asyncio.run(self.start())

    # ═════════════════════════════════════════════════════════════════════
    # إدارة الاتصالات
    # ═════════════════════════════════════════════════════════════════════

    async def _handle_client(self, websocket: WebSocketServerProtocol):
        """معالجة اتصال موبايل واحد."""
        client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self._clients.add(websocket)
        logger.info(f"📱 Client connected: {client_info} (total: {len(self._clients)})")

        if self._on_client_connected:
            self._on_client_connected(client_info)

        try:
            async for raw_message in websocket:
                await self._process_message(raw_message, websocket, client_info)
        except websockets.ConnectionClosed as e:
            logger.info(f"🔌 Client disconnected: {client_info} ({e.code})")
        except Exception as e:
            logger.error(f"❌ Error with {client_info}: {e}")
        finally:
            self._clients.discard(websocket)
            if self._on_client_disconnected:
                self._on_client_disconnected(client_info)
            logger.info(f"📱 Clients remaining: {len(self._clients)}")

    async def _process_message(self, raw: str, ws: WebSocketServerProtocol, client: str):
        """معالجة رسالة واردة."""
        msg = parse_message(raw)
        msg_type = msg.get("type")
        payload = msg.get("payload", {})

        if msg_type is None:
            logger.warning(f"⚠️ Invalid message from {client}")
            return

        self._received_count += 1

        # ── Heartbeat → رد فوري ──────────────────────────────────────
        if msg_type == MessageType.HEARTBEAT:
            await ws.send(make_heartbeat_ack())

        # ── عملية جديدة ──────────────────────────────────────────────
        elif msg_type == MessageType.NEW_TRANSACTION:
            tx = Transaction.from_dict(payload)
            logger.info(
                f"💰 {tx.type.value}: {tx.amount} EGP "
                f"| {tx.counterpart} | conf: {tx.confidence:.0%}"
            )
            if self._on_transaction:
                self._on_transaction(tx)

        # ── تحديث رصيد ───────────────────────────────────────────────
        elif msg_type == MessageType.BALANCE_UPDATE:
            balance = payload.get("balance", 0)
            wallet_id = payload.get("wallet_id", "")
            logger.info(f"💳 Balance update: {balance} EGP (wallet: {wallet_id})")
            if self._on_balance_update:
                self._on_balance_update(balance, wallet_id)

        # ── رسالة غير مصنفة ──────────────────────────────────────────
        elif msg_type == MessageType.UNCLASSIFIED_SMS:
            logger.info(f"📬 Unclassified SMS (conf: {payload.get('confidence', 0):.0%})")
            if self._on_unclassified:
                self._on_unclassified(payload)

        # ── رسالة SMS خام جديدة من الأندرويد ──────────────────────────
        elif msg_type == MessageType.NEW_SMS:
            from mobile.parser.engine import SMSEngine
            from shared.config import CONFIDENCE_THRESHOLD
            
            body = payload.get("body", "")
            sender = payload.get("sender", "")
            timestamp = payload.get("timestamp")
            
            logger.info(f"📨 Received raw SMS from Android: {sender} | {body[:30]}...")
            
            tx = SMSEngine.parse(body, sender=sender)
            if timestamp:
                tx.sms_timestamp = datetime.fromtimestamp(timestamp / 1000.0)
            
            if tx.confidence >= CONFIDENCE_THRESHOLD:
                logger.info(
                    f"💰 Parse Success - {tx.type.value}: {tx.amount} EGP "
                    f"| {tx.counterpart} | conf: {tx.confidence:.0%}"
                )
                if self._on_transaction:
                    self._on_transaction(tx)
            else:
                logger.warning(f"📬 Raw SMS is unclassified (conf: {tx.confidence:.0%})")
                if self._on_unclassified:
                    self._on_unclassified({
                        "id": tx.transaction_id,
                        "raw_sms": body,
                        "sender": sender,
                        "received_at": datetime.now().isoformat(),
                        "confidence": tx.confidence,
                        "reviewed": False
                    })

        # ── إشعار انقطاع ─────────────────────────────────────────────
        elif msg_type == MessageType.DISCONNECT:
            reason = payload.get("reason", "")
            logger.info(f"👋 Client disconnecting: {reason}")

    # ═════════════════════════════════════════════════════════════════════
    # إرسال للموبايل (Desktop → Mobile)
    # ═════════════════════════════════════════════════════════════════════

    async def request_sync(self, last_sync: datetime = None):
        """إرسال طلب مزامنة لكل الموبايلات المتصلة."""
        if not last_sync:
            last_sync = datetime.now()
        msg = make_sync_request(last_sync)
        await self._broadcast(msg)

    async def _broadcast(self, message: str):
        """إرسال رسالة لكل الموبايلات المتصلة."""
        if not self._clients:
            return
        await asyncio.gather(
            *[client.send(message) for client in self._clients],
            return_exceptions=True
        )

    # ═════════════════════════════════════════════════════════════════════
    # الحالة والإحصائيات
    # ═════════════════════════════════════════════════════════════════════

    @property
    def connected_clients(self) -> int:
        return len(self._clients)

    @property
    def stats(self) -> dict:
        uptime = (datetime.now() - self._start_time).total_seconds() if self._start_time else 0
        return {
            "host": self._host,
            "port": self._port,
            "clients": self.connected_clients,
            "received": self._received_count,
            "uptime_seconds": int(uptime),
        }
