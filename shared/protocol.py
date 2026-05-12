# shared/protocol.py

import json
from datetime import datetime
from enum import Enum
from shared.models import Transaction, UnclassifiedSMS


# ── أنواع الرسائل بين الموبايل والديسكتوب ────────────────────────────────
class MessageType(Enum):
    NEW_TRANSACTION  = "NEW_TRANSACTION"   # موبايل → ديسكتوب
    BALANCE_UPDATE   = "BALANCE_UPDATE"    # موبايل → ديسكتوب
    UNCLASSIFIED_SMS = "UNCLASSIFIED_SMS"  # موبايل → ديسكتوب
    HEARTBEAT        = "HEARTBEAT"         # في الاتجاهين
    HEARTBEAT_ACK    = "HEARTBEAT_ACK"     # رد على الـ heartbeat
    SYNC_REQUEST     = "SYNC_REQUEST"      # ديسكتوب → موبايل
    SYNC_RESPONSE    = "SYNC_RESPONSE"     # موبايل → ديسكتوب
    DISCONNECT       = "DISCONNECT"        # في الاتجاهين


# ── بناء الرسائل (Mobile → Desktop) ──────────────────────────────────────
def make_new_transaction(transaction: Transaction) -> str:
    """رسالة عملية جديدة"""
    return json.dumps({
        "type"    : MessageType.NEW_TRANSACTION.value,
        "payload" : transaction.to_dict(),
        "sent_at" : datetime.now().isoformat(),
    })


def make_balance_update(balance: float, wallet_id: str) -> str:
    """رسالة تحديث الرصيد"""
    return json.dumps({
        "type"    : MessageType.BALANCE_UPDATE.value,
        "payload" : {
            "balance"   : balance,
            "wallet_id" : wallet_id,
        },
        "sent_at" : datetime.now().isoformat(),
    })


def make_unclassified_sms(sms: UnclassifiedSMS) -> str:
    """رسالة SMS غير مصنف"""
    return json.dumps({
        "type"    : MessageType.UNCLASSIFIED_SMS.value,
        "payload" : {
            "id"          : sms.id,
            "raw_sms"     : sms.raw_sms,
            "sender"      : sms.sender,
            "received_at" : sms.received_at.isoformat(),
            "confidence"  : sms.confidence,
        },
        "sent_at" : datetime.now().isoformat(),
    })


# ── بناء الرسائل (Desktop → Mobile) ──────────────────────────────────────
def make_sync_request(last_sync: datetime) -> str:
    """طلب مزامنة العمليات الفائتة"""
    return json.dumps({
        "type"    : MessageType.SYNC_REQUEST.value,
        "payload" : {
            "last_sync" : last_sync.isoformat(),
        },
        "sent_at" : datetime.now().isoformat(),
    })


# ── رسائل مشتركة ──────────────────────────────────────────────────────────
def make_heartbeat() -> str:
    """ping"""
    return json.dumps({
        "type"    : MessageType.HEARTBEAT.value,
        "payload" : {},
        "sent_at" : datetime.now().isoformat(),
    })


def make_heartbeat_ack() -> str:
    """pong"""
    return json.dumps({
        "type"    : MessageType.HEARTBEAT_ACK.value,
        "payload" : {},
        "sent_at" : datetime.now().isoformat(),
    })


def make_disconnect(reason: str = "") -> str:
    """إشعار بإنهاء الجلسة"""
    return json.dumps({
        "type"    : MessageType.DISCONNECT.value,
        "payload" : {"reason": reason},
        "sent_at" : datetime.now().isoformat(),
    })


# ── تحليل الرسائل الواردة ─────────────────────────────────────────────────
def parse_message(raw: str) -> dict:
    """
    تحويل الرسالة الواردة من JSON لـ dict
    الناتج دايماً فيه: type + payload + sent_at
    """
    try:
        data = json.loads(raw)
        return {
            "type"    : MessageType(data["type"]),
            "payload" : data.get("payload", {}),
            "sent_at" : data.get("sent_at", ""),
        }
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        return {
            "type"    : None,
            "payload" : {},
            "error"   : str(e),
        }