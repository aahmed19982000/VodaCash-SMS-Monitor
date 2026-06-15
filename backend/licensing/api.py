import os
import sys
import json
import logging
import uuid
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.http import require_POST

# Setup logging
logger = logging.getLogger(__name__)

# Add root directory to python path to import mobile parser
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/licensing/ -> backend/
ROOT_DIR = os.path.dirname(BASE_DIR)  # -> root/
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from mobile.parser.engine import SMSEngine
from shared.models import TransactionType
from .models import PaymentRecord, LicenseKey, UnmatchedTransaction, SiteConfiguration
from .utils import normalize_egyptian_phone

@csrf_exempt
@require_POST
def payment_callback_api(request):
    # 1. API Key Authorization
    gateway_key = request.headers.get('Authorization')
    if gateway_key and gateway_key.startswith('Bearer '):
        gateway_key = gateway_key[7:]
    else:
        # Fallback to X-Gateway-Key header
        gateway_key = request.headers.get('X-Gateway-Key')

    config = SiteConfiguration.get_solo()
    if not gateway_key or gateway_key != config.gateway_api_key:
        return JsonResponse({"success": False, "message": "Unauthorized"}, status=401)

    # 2. Parse Body Data
    try:
        data = json.loads(request.body)
        sender = data.get("sender", "").strip()
        body = data.get("body", "").strip()
        timestamp = data.get("timestamp")  # Unix timestamp in seconds
    except Exception:
        return JsonResponse({"success": False, "message": "Invalid JSON payload"}, status=400)

    if not body:
        return JsonResponse({"success": False, "message": "SMS body is empty"}, status=400)

    # 3. Check Timestamp (10 minutes window)
    if timestamp is not None:
        try:
            timestamp_val = float(timestamp)
            current_time = timezone.now().timestamp()
            if abs(current_time - timestamp_val) > 600:  # 10 minutes (600 seconds)
                return JsonResponse({"success": False, "message": "Request expired (timestamp older than 10 mins)"}, status=400)
        except ValueError:
            return JsonResponse({"success": False, "message": "Invalid timestamp format"}, status=400)

    # 4. Parse SMS using SMSEngine
    try:
        tx = SMSEngine.parse(body, sender=sender)
    except Exception as e:
        logger.error(f"Error parsing SMS in callback: {str(e)}")
        return JsonResponse({"success": False, "message": f"Parsing failed: {str(e)}"}, status=500)

    # Check if transaction is a received transfer
    if tx.type == TransactionType.RECEIVED:
        # Extract counterpart phone and normalize it
        raw_counterpart = tx.counterpart or ""
        normalized_sender = normalize_egyptian_phone(raw_counterpart)
        
        amount = tx.amount
        parsed_txn_id = tx.transaction_id or ""

        # Enforce uniqueness on transaction_id to prevent double-processing (Replay attack)
        if parsed_txn_id:
            # Check if this transaction ID was already registered in a success record
            if PaymentRecord.objects.filter(transaction_id=parsed_txn_id, status='SUCCESS').exists():
                return JsonResponse({"success": False, "message": f"Duplicate transaction ID: {parsed_txn_id}"}, status=400)
            
            # Check if it was already recorded as unmatched
            if UnmatchedTransaction.objects.filter(parsed_transaction_id=parsed_txn_id).exists():
                return JsonResponse({"success": False, "message": f"Duplicate unmatched transaction ID: {parsed_txn_id}"}, status=400)

        # Match with a PENDING payment record
        # PaymentRecord must be pending, matching amount, matching sender_wallet, and within expires_at window
        now = timezone.now()
        pending_payments = PaymentRecord.objects.filter(
            status='PENDING',
            amount=amount,
            sender_wallet=normalized_sender,
            expires_at__gte=now
        ).order_by('created_at')

        if pending_payments.exists():
            payment = pending_payments.first()
            
            # Update PaymentRecord to SUCCESS
            payment.status = 'SUCCESS'
            payment.transaction_id = parsed_txn_id if parsed_txn_id else f"CONF-{uuid.uuid4().hex[:10].upper()}"
            
            # Activate the linked LicenseKey
            lic = payment.license_key
            if lic:
                duration = 30 if lic.type == 'MONTHLY' else 365
                lic.status = 'ACTIVE'
                lic.expires_at = now + timedelta(days=duration)
                lic.save()
                
                # Increment Coupon usage if applicable
                if payment.coupon_code:
                    try:
                        coupon = Coupon.objects.get(code=payment.coupon_code)
                        if coupon.is_valid():
                            coupon.uses_count += 1
                            coupon.save()
                    except Coupon.DoesNotExist:
                        pass
                
                payment.save()
                
                # Send email notification to user with the key
                from web.views import send_license_email
                try:
                    send_license_email(payment.user, lic.key, lic.type, lic.expires_at)
                except Exception as mail_err:
                    logger.error(f"Failed to send license email: {str(mail_err)}")
                
                return JsonResponse({
                    "success": True, 
                    "message": "Payment verified and license key activated successfully.",
                    "details": {
                        "payment_id": payment.id,
                        "license_key": lic.key,
                        "status": "SUCCESS"
                    }
                })
            else:
                payment.save()
                return JsonResponse({"success": False, "message": "Payment found but no linked license key found"}, status=500)
        else:
            # No matching pending payment found -> Log as unmatched transaction
            if not parsed_txn_id:
                parsed_txn_id = f"UNM-{uuid.uuid4().hex[:10].upper()}"
                
            UnmatchedTransaction.objects.create(
                raw_sms_body=body,
                parsed_amount=amount,
                parsed_sender=normalized_sender or raw_counterpart or "Unknown",
                parsed_transaction_id=parsed_txn_id,
                resolved=False
            )
            return JsonResponse({
                "success": False, 
                "message": "No matching pending payment record found. Transaction logged for manual review."
            }, status=200)

    else:
        return JsonResponse({"success": False, "message": "SMS processed, but is not a RECEIVED transfer transaction"}, status=200)
