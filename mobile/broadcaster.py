# mobile/broadcaster.py
# ── WebSocket Client لإرسال البيانات من الموبايل إلى سطح المكتب ───────────

import asyncio
import json
import logging
import threading
import time
from datetime import datetime
from typing import Callable, Optional

import websockets
from websockets.exceptions import ConnectionClosed, InvalidURI, InvalidHandshake

from shared.config import WEBSOCKET_HOST, WEBSOCKET_PORT, HEARTBEAT_INTERVAL, CONNECTION_TIMEOUT
from shared.models import Transaction, UnclassifiedSMS
from shared.protocol import (
    make_new_transaction,
    make_balance_update,
    make_unclassified_sms,
    make_heartbeat,
    make_disconnect,
    parse_message,
    MessageType,
)

logger = logging.getLogger("VodaCash.Broadcaster")


class Broadcaster:
    """
    WebSocket Client يعمل في thread منفصل.

    المسؤوليات:
    ─────────────────────────────────────────────────────
    1. الاتصال بسيرفر سطح المكتب عبر WebSocket
    2. إرسال العمليات المصنفة والرسائل غير المصنفة
    3. إرسال heartbeat دوري للتأكد من سلامة الاتصال
    4. إعادة الاتصال تلقائياً عند الانقطاع
    5. تخزين الرسائل مؤقتاً (queue) عند عدم الاتصال
    """

    def __init__(self, host: str = None, port: int = None,
                 on_connected: Callable = None,
                 on_disconnected: Callable = None,
                 on_message: Callable = None):

        self._host = host or WEBSOCKET_HOST
        self._port = port or WEBSOCKET_PORT
        self._uri = f"ws://{self._host}:{self._port}"

        # Callbacks
        self._on_connected = on_connected
        self._on_disconnected = on_disconnected
        self._on_message = on_message

        # الحالة
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._connected = False
        self._running = False
        self._reconnect_delay = 2  # ثوانٍ — يتضاعف مع كل محاولة فاشلة

        # Thread + Event Loop
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Offline Queue (thread-safe)
        self._queue: list = []
        self._queue_lock = threading.Lock()
        self._max_queue = 500

        # إحصائيات
        self._sent_count = 0
        self._failed_count = 0
        self._last_heartbeat: Optional[datetime] = None

    # ═════════════════════════════════════════════════════════════════════
    # التشغيل والإيقاف
    # ═════════════════════════════════════════════════════════════════════

    def start(self):
        """بدء الاتصال في thread منفصل."""
        if self._running:
            logger.warning("⚠️ Broadcaster already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="WS-Broadcaster")
        self._thread.start()
        logger.info(f"🚀 Broadcaster started → {self._uri}")

    def stop(self):
        """إيقاف الاتصال بشكل نظيف."""
        self._running = False
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._close(), self._loop)
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("🛑 Broadcaster stopped")

    def _run_loop(self):
        """تشغيل event loop في الـ thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connection_loop())

    # ═════════════════════════════════════════════════════════════════════
    # حلقة الاتصال الرئيسية (مع إعادة اتصال تلقائية)
    # ═════════════════════════════════════════════════════════════════════

    async def _connection_loop(self):
        """حلقة لا نهائية: اتصال → استماع → إعادة اتصال."""
        delay = self._reconnect_delay

        while self._running:
            try:
                logger.info(f"🔌 Connecting to {self._uri}...")
                async with websockets.connect(
                    self._uri,
                    ping_interval=HEARTBEAT_INTERVAL,
                    ping_timeout=CONNECTION_TIMEOUT,
                    close_timeout=5,
                ) as ws:
                    self._ws = ws
                    self._connected = True
                    delay = self._reconnect_delay  # إعادة تعيين التأخير

                    logger.info("🟢 Connected to desktop!")
                    if self._on_connected:
                        self._on_connected()

                    # تفريغ الرسائل المعلقة
                    await self._drain_queue()

                    # بدء Heartbeat + الاستماع للرسائل
                    await asyncio.gather(
                        self._listen(),
                        self._heartbeat_loop(),
                    )

            except (ConnectionClosed, ConnectionRefusedError) as e:
                logger.warning(f"🔴 Connection lost: {e}")
            except (InvalidURI, InvalidHandshake) as e:
                logger.error(f"❌ Connection error: {e}")
            except Exception as e:
                logger.error(f"❌ Unexpected error: {e}")
            finally:
                self._connected = False
                self._ws = None
                if self._on_disconnected:
                    self._on_disconnected()

            if not self._running:
                break

            # Exponential backoff (2s → 4s → 8s → ... → 60s max)
            logger.info(f"⏳ Reconnecting in {delay}s...")
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)

    async def _listen(self):
        """الاستماع للرسائل الواردة من سطح المكتب."""
        async for raw in self._ws:
            try:
                msg = parse_message(raw)
                msg_type = msg.get("type")

                if msg_type == MessageType.HEARTBEAT_ACK:
                    self._last_heartbeat = datetime.now()

                elif msg_type == MessageType.SYNC_REQUEST:
                    logger.info("📥 Sync request received from desktop")

                if self._on_message:
                    self._on_message(msg)

            except Exception as e:
                logger.error(f"❌ Error handling message: {e}")

    async def _heartbeat_loop(self):
        """إرسال heartbeat دوري."""
        while self._running and self._connected:
            try:
                await self._ws.send(make_heartbeat())
                self._last_heartbeat = datetime.now()
            except Exception:
                break
            await asyncio.sleep(HEARTBEAT_INTERVAL)

    async def _close(self):
        """إغلاق الاتصال بشكل نظيف."""
        if self._ws and self._connected:
            try:
                await self._ws.send(make_disconnect("Client shutting down"))
                await self._ws.close()
            except Exception:
                pass

    # ═════════════════════════════════════════════════════════════════════
    # إرسال البيانات (Thread-Safe API)
    # ═════════════════════════════════════════════════════════════════════

    def broadcast_transaction(self, tx: Transaction) -> bool:
        """إرسال عملية مصنفة."""
        message = make_new_transaction(tx)
        return self._send_or_queue(message, f"{tx.type.value}: {tx.amount} EGP")

    def broadcast_balance(self, balance: float, wallet_id: str = "wallet_001") -> bool:
        """إرسال تحديث رصيد."""
        message = make_balance_update(balance, wallet_id)
        return self._send_or_queue(message, f"Balance: {balance} EGP")

    def broadcast_unclassified(self, sms: UnclassifiedSMS) -> bool:
        """إرسال رسالة غير مصنفة."""
        message = make_unclassified_sms(sms)
        return self._send_or_queue(message, "Unclassified SMS")

    def _send_or_queue(self, message: str, label: str) -> bool:
        """إرسال فوري إذا متصل، أو تخزين في الـ queue."""
        if self._connected and self._ws and self._loop:
            future = asyncio.run_coroutine_threadsafe(
                self._async_send(message), self._loop
            )
            try:
                future.result(timeout=5)
                self._sent_count += 1
                logger.info(f"📤 Sent: {label}")
                return True
            except Exception as e:
                logger.error(f"❌ Send failed: {e}")
                self._enqueue(message)
                return False
        else:
            self._enqueue(message)
            logger.debug(f"📦 Queued (offline): {label}")
            return False

    async def _async_send(self, message: str):
        """إرسال غير متزامن."""
        await self._ws.send(message)

    # ═════════════════════════════════════════════════════════════════════
    # Offline Queue
    # ═════════════════════════════════════════════════════════════════════

    def _enqueue(self, message: str):
        """إضافة رسالة للـ queue."""
        with self._queue_lock:
            if len(self._queue) >= self._max_queue:
                self._queue.pop(0)  # إزالة الأقدم
            self._queue.append(message)

    async def _drain_queue(self):
        """تفريغ الرسائل المعلقة بعد إعادة الاتصال."""
        with self._queue_lock:
            pending = list(self._queue)
            self._queue.clear()

        if not pending:
            return

        logger.info(f"📤 Draining {len(pending)} queued messages...")
        for msg in pending:
            try:
                await self._ws.send(msg)
                self._sent_count += 1
            except Exception as e:
                logger.error(f"❌ Drain failed: {e}")
                self._enqueue(msg)  # إرجاعها للـ queue
                break

    # ═════════════════════════════════════════════════════════════════════
    # الحالة والإحصائيات
    # ═════════════════════════════════════════════════════════════════════

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def queue_size(self) -> int:
        with self._queue_lock:
            return len(self._queue)

    @property
    def stats(self) -> dict:
        return {
            "connected": self._connected,
            "uri": self._uri,
            "sent_count": self._sent_count,
            "failed_count": self._failed_count,
            "queue_size": self.queue_size,
            "last_heartbeat": self._last_heartbeat.isoformat() if self._last_heartbeat else None,
        }
