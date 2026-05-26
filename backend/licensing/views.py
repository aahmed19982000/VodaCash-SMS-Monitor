# backend/licensing/views.py
import json
import uuid
from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import LicenseKey, Coupon

def json_error(message):
    return JsonResponse({"success": False, "message": message})

@csrf_exempt
def validate_license(request):
    if request.method != 'POST':
        return json_error("Method not allowed")
    
    try:
        data = json.loads(request.body)
        license_key = data.get("key", "").strip()
        mac_addr = data.get("mac_address", "").strip().lower()
    except Exception:
        return json_error("Invalid JSON data")

    if not license_key:
        return json_error("مفتاح التفعيل مطلوب")

    try:
        lic = LicenseKey.objects.get(key=license_key)
    except LicenseKey.DoesNotExist:
        return json_error("كود التفعيل هذا غير موجود بقاعدة البيانات.")

    if lic.status == 'SUSPENDED':
        return json_error("هذا الاشتراك معطل حالياً من قبل الإدارة.")

    now = timezone.now()
    if now > lic.expires_at:
        if lic.status == 'ACTIVE':
            lic.status = 'EXPIRED'
            lic.save()
        return json_error("عذراً، هذا الاشتراك منتهي الصلاحية.")

    if lic.mac_address:
        if lic.mac_address.lower() != mac_addr:
            return json_error(f"هذا الاشتراك مفعل على جهاز آخر بـ MAC Address مختلف ({lic.mac_address}).")
    else:
        lic.mac_address = mac_addr
        lic.save()

    return JsonResponse({
        "success": True,
        "message": "تم التحقق بنجاح.",
        "license": {
            "key": lic.key,
            "client_name": lic.client_name,
            "client_phone": lic.client_phone,
            "type": lic.type,
            "status": "ACTIVE",
            "expires_at": lic.expires_at.isoformat(),
            "mac_address": lic.mac_address
        }
    })

@csrf_exempt
def register_trial(request):
    if request.method != 'POST':
        return json_error("Method not allowed")

    try:
        data = json.loads(request.body)
        client_name = data.get("client_name", "").strip()
        client_phone = data.get("client_phone", "").strip()
        mac_addr = data.get("mac_address", "").strip().lower()
    except Exception:
        return json_error("Invalid JSON data")

    if not mac_addr:
        return json_error("عنوان MAC مطلوب لتفعيل الفترة التجريبية")

    if not client_name:
        client_name = f"جهاز تجريبي ({mac_addr[:8]})"

    # Check if this MAC address already registered a trial
    if LicenseKey.objects.filter(mac_address=mac_addr).exists():
        return json_error("عذراً، هذا الجهاز مفعل عليه فترة تجريبية مسبقاً ولا يمكن تفعيل فترة تجريبية أخرى له.")

    trial_days = 3
    expires_at = timezone.now() + timedelta(days=trial_days)
    trial_key = f"VC-TRIAL-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"

    try:
        lic = LicenseKey.objects.create(
            key=trial_key,
            client_name=client_name,
            client_phone=client_phone if client_phone else None,
            type='TRIAL',
            status='ACTIVE',
            expires_at=expires_at,
            mac_address=mac_addr
        )
        return JsonResponse({
            "success": True,
            "key": lic.key,
            "expires_at": lic.expires_at.isoformat(),
            "message": f"تم تفعيل الفترة التجريبية بنجاح لمدة {trial_days} أيام! كود التفعيل الخاص بك: {lic.key}"
        })
    except Exception as e:
        return json_error(f"فشل إنشاء الفترة التجريبية: {str(e)}")

@csrf_exempt
def check_trial_mac(request):
    if request.method != 'POST':
        return JsonResponse({"has_trial": False})

    try:
        data = json.loads(request.body)
        mac_addr = data.get("mac_address", "").strip().lower()
    except Exception:
        return JsonResponse({"has_trial": False})

    has_trial = LicenseKey.objects.filter(mac_address=mac_addr).exists()
    return JsonResponse({"has_trial": has_trial})

@csrf_exempt
def validate_coupon(request):
    if request.method != 'POST':
        return json_error("Method not allowed")

    try:
        data = json.loads(request.body)
        code = data.get("code", "").strip().upper()
    except Exception:
        return json_error("Invalid JSON data")

    try:
        coupon = Coupon.objects.get(code=code)
    except Coupon.DoesNotExist:
        return json_error("كوبون غير صالح أو غير نشط.")

    if not coupon.is_valid():
        return json_error("كوبون منتهي الصلاحية أو تم تجاوزه للحد الأقصى للاستخدام.")

    return JsonResponse({
        "success": True,
        "discount_percent": coupon.discount_percent,
        "trial_days": coupon.trial_days
    })

@csrf_exempt
def use_coupon(request):
    if request.method != 'POST':
        return JsonResponse({"success": False})

    try:
        data = json.loads(request.body)
        code = data.get("code", "").strip().upper()
    except Exception:
        return JsonResponse({"success": False})

    try:
        coupon = Coupon.objects.get(code=code)
        if coupon.is_valid():
            coupon.uses_count += 1
            coupon.save()
            return JsonResponse({"success": True})
    except Coupon.DoesNotExist:
        pass

    return JsonResponse({"success": False})

@csrf_exempt
def bind_mac(request):
    if request.method != 'POST':
        return JsonResponse({"success": False})

    try:
        data = json.loads(request.body)
        license_key = data.get("key", "").strip()
        mac_addr = data.get("mac_address", "").strip().lower()
    except Exception:
        return JsonResponse({"success": False})

    try:
        lic = LicenseKey.objects.get(key=license_key)
        lic.mac_address = mac_addr
        lic.save()
        return JsonResponse({"success": True})
    except LicenseKey.DoesNotExist:
        pass

    return JsonResponse({"success": False})

@csrf_exempt
def update_license_status(request):
    if request.method != 'POST':
        return JsonResponse({"success": False})

    try:
        data = json.loads(request.body)
        license_key = data.get("key", "").strip()
        status = data.get("status", "").strip().upper()
    except Exception:
        return JsonResponse({"success": False})

    try:
        lic = LicenseKey.objects.get(key=license_key)
        if status in ['ACTIVE', 'EXPIRED', 'SUSPENDED']:
            lic.status = status
            lic.save()
            return JsonResponse({"success": True})
    except LicenseKey.DoesNotExist:
        pass

    return JsonResponse({"success": False})

@csrf_exempt
def login_license(request):
    if request.method != 'POST':
        return json_error("Method not allowed")

    try:
        data = json.loads(request.body)
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        mac_addr = data.get("mac_address", "").strip().lower()
    except Exception:
        return json_error("Invalid JSON data")

    if not username or not password:
        return json_error("اسم المستخدم وكلمة المرور مطلوبين.")

    if not mac_addr:
        return json_error("عنوان MAC للجهاز مطلوب.")

    # Authenticate user
    from django.contrib.auth import authenticate
    from django.contrib.auth.models import User
    
    user = authenticate(username=username, password=password)
    if user is None:
        # Try matching by email
        try:
            user_by_email = User.objects.get(email=username)
            user = authenticate(username=user_by_email.username, password=password)
        except User.DoesNotExist:
            pass

    if user is None:
        return json_error("اسم المستخدم أو كلمة المرور غير صحيحة.")

    # Find active licenses for this user
    now = timezone.now()
    licenses = LicenseKey.objects.filter(user=user, status='ACTIVE', expires_at__gt=now).order_by('-expires_at')

    if not licenses.exists():
        return json_error("لا يوجد اشتراك نشط لهذا الحساب. يرجى تفعيل اشتراك أو تجربة من الموقع.")

    # Find a license that matches the MAC address or is unbound
    target_lic = None
    for lic in licenses:
        if lic.mac_address and lic.mac_address.lower() == mac_addr:
            target_lic = lic
            break
    
    # If no matching MAC found, find the first unbound license
    if not target_lic:
        for lic in licenses:
            if not lic.mac_address:
                target_lic = lic
                # Bind it now
                lic.mac_address = mac_addr
                lic.save()
                break

    if not target_lic:
        # If all active licenses are bound to other MAC addresses
        first_lic = licenses[0]
        return json_error(f"هذا الاشتراك مفعل بالفعل على جهاز آخر بـ MAC مختلف ({first_lic.mac_address}).")

    return JsonResponse({
        "success": True,
        "message": "تم تسجيل الدخول والتحقق من الاشتراك بنجاح.",
        "license": {
            "key": target_lic.key,
            "client_name": target_lic.client_name,
            "client_phone": target_lic.client_phone,
            "type": target_lic.type,
            "status": "ACTIVE",
            "expires_at": target_lic.expires_at.isoformat(),
            "mac_address": target_lic.mac_address
        }
    })


@csrf_exempt
def report_unclassified_sms(request):
    if request.method != 'POST':
        return json_error("Method not allowed")

    try:
        data = json.loads(request.body)
        sender = data.get("sender", "").strip()
        raw_sms = data.get("raw_sms", "").strip()
        received_at_str = data.get("received_at", "")
        mac_addr = data.get("mac_address", "").strip().lower()
        license_key = data.get("license_key", "").strip()
    except Exception:
        return json_error("Invalid JSON data")

    if not sender or not raw_sms:
        return json_error("Sender and raw_sms are required.")

    received_at = timezone.now()
    if received_at_str:
        try:
            received_at = timezone.datetime.fromisoformat(received_at_str)
        except ValueError:
            pass

    from .models import UnclassifiedSMSReport
    try:
        report = UnclassifiedSMSReport.objects.create(
            sender=sender,
            raw_sms=raw_sms,
            received_at=received_at,
            mac_address=mac_addr,
            license_key=license_key
        )
        return JsonResponse({"success": True, "message": "تم إرسال الرسالة للتحليل بنجاح."})
    except Exception as e:
        return json_error(f"Failed to save report: {str(e)}")


