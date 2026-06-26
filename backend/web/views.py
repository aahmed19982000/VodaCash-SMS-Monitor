import os
import uuid
import logging
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, FileResponse, Http404
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from licensing.models import LicenseKey, Coupon, PaymentRecord, SiteConfiguration
from licensing.utils import normalize_egyptian_phone
from .infobip import send_whatsapp_otp, send_whatsapp_welcome, send_whatsapp_payment_confirmation

logger = logging.getLogger(__name__)

def send_welcome_email(user):
    if not user.email:
        return
    try:
        subject = 'مرحباً بك في دفتر كاش - Daftar Cash 🚀'
        html_message = render_to_string('emails/welcome.html', {'user': user})
        send_mail(
            subject,
            '',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=True
        )
    except Exception as e:
        logger.error(f"Error sending welcome email to {user.email}: {e}")

def send_license_email(user, license_key, plan_type, expires_at):
    if not user.email:
        return
    try:
        subject = f'🔑 مفتاح تفعيل اشتراكك في دفتر كاش - {license_key}'
        html_message = render_to_string('emails/license_info.html', {
            'user': user,
            'license_key': license_key,
            'plan_type': 'شهري' if plan_type == 'MONTHLY' else 'سنوي' if plan_type == 'YEARLY' else 'تجريبي',
            'expires_at': expires_at.strftime('%Y-%m-%d %H:%M')
        })
        send_mail(
            subject,
            '',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=True
        )
    except Exception as e:
        logger.error(f"Error sending license email to {user.email}: {e}")

def download_file(request, file_type):
    if file_type == 'desktop':
        file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'dist', 'DaftarCash.exe')
        filename = 'DaftarCash.exe'
    elif file_type == 'mobile':
        file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'mobile', 'android', 'app', 'build', 'outputs', 'apk', 'debug', 'app-debug.apk')
        filename = 'DaftarCash.apk'
    else:
        raise Http404("الملف غير موجود")

    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    else:
        raise Http404("لم يتم بناء هذا الملف بعد")

def privacy_policy(request):
    return render(request, 'web/privacy_policy.html')


def landing_page(request):
    return render(request, 'web/landing.html')

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        u = request.POST.get('username', '').strip()
        e = request.POST.get('email', '').strip()
        p = request.POST.get('password', '').strip()
        p_c = request.POST.get('password_confirm', '').strip()
        phone = request.POST.get('phone', '').strip()
        
        if not u or not p or not phone:
            messages.error(request, "يرجى ملء جميع الحقول المطلوبة (اسم المستخدم، كلمة المرور، ورقم الهاتف).")
            return render(request, 'web/register.html')
            
        if p != p_c:
            messages.error(request, "كلمتا المرور غير متطابقتين.")
            return render(request, 'web/register.html')
            
        if User.objects.filter(username=u).exists():
            messages.error(request, "اسم المستخدم هذا مسجل بالفعل.")
            return render(request, 'web/register.html')
            
        if e and User.objects.filter(email=e).exists():
            messages.error(request, "البريد الإلكتروني هذا مسجل بالفعل.")
            return render(request, 'web/register.html')
            
        try:
            user = User.objects.create_user(username=u, email=e, password=p)
            
            # Save UserProfile fields
            profile = user.profile
            profile.phone = normalize_egyptian_phone(phone)
            profile.has_whatsapp = True
            profile.email_verified = False
            profile.save()
            
            # Send verification OTP code via WhatsApp
            send_whatsapp_otp(user)
            
            # Store in session for verification page lookup
            request.session['verification_username'] = user.username
            messages.success(request, "تم تسجيل حسابك بنجاح! تم إرسال رمز تفعيل مؤقت إلى حساب الواتس آب الخاص بك.")
            return redirect('verify_email')
        except Exception as ex:
            messages.error(request, f"حدث خطأ أثناء التسجيل: {ex}")
            
    return render(request, 'web/register.html')

def social_login_view(request, provider):
    import urllib.parse
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    provider = provider.lower()
    if provider not in ['google', 'facebook']:
        messages.error(request, "مزود خدمة غير مدعوم.")
        return redirect('login')

    client_id = ""
    auth_url = ""
    redirect_uri = request.build_absolute_uri(f"/social/callback/{provider}/")

    if provider == 'google':
        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', os.environ.get('GOOGLE_CLIENT_ID', ''))
        auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={client_id}&"
            f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
            "response_type=code&"
            "scope=email%20profile"
        )
    elif provider == 'facebook':
        client_id = getattr(settings, 'FACEBOOK_CLIENT_ID', os.environ.get('FACEBOOK_CLIENT_ID', ''))
        auth_url = (
            "https://www.facebook.com/v12.0/dialog/oauth?"
            f"client_id={client_id}&"
            f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
            "scope=email,public_profile"
        )

    if not client_id:
        messages.warning(
            request, 
            f"تنبيه: تم تفعيل الدخول التجريبي لـ {provider.capitalize()} لعدم تهيئة معرّفات الدخول (Client ID) في البيئة المحلية."
        )
        return redirect(f"/social/callback/{provider}/?mock=true")

    return redirect(auth_url)

def social_callback_view(request, provider):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    provider = provider.lower()
    is_mock = request.GET.get('mock', '') == 'true'
    code = request.GET.get('code', '')

    if is_mock or not code:
        user_email = f"{provider}.tester@daftarcash.com"
        user_fullname = f"مستخدم {provider.capitalize()} التجريبي"
        username = f"{provider}_user_{uuid.uuid4().hex[:6]}"
    else:
        try:
            redirect_uri = request.build_absolute_uri(f"/social/callback/{provider}/")
            import requests
            if provider == 'google':
                client_id = getattr(settings, 'GOOGLE_CLIENT_ID', os.environ.get('GOOGLE_CLIENT_ID', ''))
                client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', os.environ.get('GOOGLE_CLIENT_SECRET', ''))
                token_res = requests.post("https://oauth2.googleapis.com/token", data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                }).json()
                access_token = token_res.get('access_token')
                user_info = requests.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"}
                ).json()
                user_email = user_info.get('email', '')
                user_fullname = user_info.get('name', user_email.split('@')[0])
                username = f"google_{user_info.get('id', uuid.uuid4().hex[:6])}"
            elif provider == 'facebook':
                client_id = getattr(settings, 'FACEBOOK_CLIENT_ID', os.environ.get('FACEBOOK_CLIENT_ID', ''))
                client_secret = getattr(settings, 'FACEBOOK_CLIENT_SECRET', os.environ.get('FACEBOOK_CLIENT_SECRET', ''))
                token_res = requests.get("https://graph.facebook.com/v12.0/oauth/access_token", params={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "code": code
                }).json()
                access_token = token_res.get('access_token')
                user_info = requests.get(
                    "https://graph.facebook.com/me",
                    params={"fields": "id,name,email", "access_token": access_token}
                ).json()
                user_email = user_info.get('email', f"{user_info.get('id')}@facebook.com")
                user_fullname = user_info.get('name', '')
                username = f"facebook_{user_info.get('id', uuid.uuid4().hex[:6])}"
        except Exception as e:
            messages.error(request, f"فشل تسجيل الدخول عبر {provider.capitalize()}: {e}")
            return redirect('login')

    try:
        user = User.objects.filter(email=user_email).first()
        if not user:
            user = User.objects.create_user(username=username, email=user_email)
            trial_key = f"VC-SOCIAL-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"
            expires_at = timezone.now() + timedelta(days=7)
            LicenseKey.objects.create(
                key=trial_key,
                user=user,
                client_name=user_fullname or user.username,
                type='TRIAL',
                status='ACTIVE',
                expires_at=expires_at
            )
            profile = user.profile
            profile.phone = ""
            profile.has_whatsapp = False
            profile.email_verified = True
            profile.save()

            send_welcome_email(user)
            messages.success(request, f"مرحباً بك! تم تسجيل حسابك عبر {provider.capitalize()} وتفعيل اشتراك تجريبي 7 أيام.")
        else:
            profile = user.profile
            if not profile.email_verified:
                profile.email_verified = True
                profile.save()
            messages.success(request, f"تم تسجيل الدخول بنجاح عبر {provider.capitalize()}.")

        login(request, user)
        return redirect('dashboard')
    except Exception as ex:
        messages.error(request, f"حدث خطأ أثناء معالجة حساب {provider.capitalize()}: {ex}")
        return redirect('login')

def login_view(request):
    next_url = request.GET.get('next') or request.POST.get('next') or ''
    
    if request.user.is_authenticated:
        if next_url:
            return redirect(next_url)
        if request.user.is_staff or request.user.is_superuser:
            return redirect('admin_panel')
        return redirect('dashboard')
        
    if request.method == 'POST':
        u = request.POST.get('username', '').strip()
        p = request.POST.get('password', '').strip()
        
        user = authenticate(request, username=u, password=p)
        if user is not None:
            profile = getattr(user, 'profile', None)
            if profile and not profile.email_verified and not user.is_staff and not user.is_superuser:
                send_whatsapp_otp(user)
                request.session['verification_username'] = user.username
                messages.warning(request, "يرجى تأكيد حسابك أولاً. تم إرسال رمز تحقق جديد إلى حساب الواتس آب الخاص بك.")
                return redirect('verify_email')

            login(request, user)
            messages.success(request, "تم تسجيل الدخول بنجاح.")
            if next_url:
                return redirect(next_url)
            if user.is_staff or user.is_superuser:
                return redirect('admin_panel')
            return redirect('dashboard')
        else:
            messages.error(request, "اسم المستخدم أو كلمة المرور غير صحيحة.")
            
    return render(request, 'web/login.html')

def logout_view(request):
    logout(request)
    messages.success(request, "تم تسجيل الخروج بنجاح.")
    return redirect('landing')

@login_required
def dashboard_view(request):
    user_licenses = LicenseKey.objects.filter(user=request.user).order_by('-created_at')
    user_payments = PaymentRecord.objects.filter(user=request.user).order_by('-created_at')
    
    # Check if there's any active license
    active_license = None
    for lic in user_licenses:
        if lic.is_valid():
            active_license = lic
            break

    # ── طبقة التحليلات وحساب الإحصائيات الخاصة بهذا التاجر فقط ──
    from licensing.models import MerchantTransaction, CashLedger
    import datetime
    
    txs = MerchantTransaction.objects.filter(user=request.user).order_by('-sms_timestamp')
    
    # ── دالة مساعدة لحساب الرسوم (الأرباح) المقدرة ──
    def calculate_tx_fee(tx):
        w_id = (tx.wallet_id or "").strip().lower()
        if not w_id or w_id in ["unspecified", ""]:
            return 0.0
        amount = float(tx.amount)
        if tx.type == 'RECEIVED': # سحب للعميل
            return max(amount * 0.01, 5.0) if amount > 0 else 0.0
        elif tx.type in ['SENT', 'BILL', 'PURCHASE', 'TOPUP']: # إيداع للعميل
            return max(amount * 0.005, 5.0) if amount > 0 else 0.0
        return 0.0

    # حساب الإحصائيات الأساسية
    total_received = sum(t.amount for t in txs if t.type == 'RECEIVED')
    total_sent = sum(t.amount for t in txs if t.type == 'SENT')
    
    # حساب الأرباح والرسوم المفصلة
    total_fee = 0.0
    profit_cash = 0.0
    profit_in_wallet = 0.0
    profit_unset = 0.0
    wallet_profits = {}
    
    for t in txs:
        fee = calculate_tx_fee(t)
        total_fee += fee
        
        # ربح المحفظة
        w_id = t.wallet_id or "غير محدد"
        wallet_profits[w_id] = wallet_profits.get(w_id, 0.0) + fee
        
        # أرباح مصنفة
        p_status = t.profit_status or "UNSET"
        if p_status == 'CASH':
            profit_cash += fee
        elif p_status == 'IN_WALLET':
            profit_in_wallet += fee
        else:
            profit_unset += fee

    tx_count = txs.count()

    # 1. المخطط الدائري: توزيع المحافظ
    wallets_data = {}
    for t in txs:
        w = t.wallet_id or "غير محدد"
        wallets_data[w] = wallets_data.get(w, 0) + 1
    
    # 2. المخطط الشريطي: ساعات الذروة (24 ساعة)
    hours_data = [0] * 24
    for t in txs:
        try:
            local_time = timezone.localtime(t.sms_timestamp)
            hours_data[local_time.hour] += 1
        except Exception:
            hours_data[t.sms_timestamp.hour] += 1

    # 3. المخطط الخطي: اتجاهات الأرباح/الحركات اليومية للـ 7 أيام الأخيرة
    today = timezone.localtime(timezone.now()).date()
    days = [today - datetime.timedelta(days=i) for i in range(6, -1, -1)]
    days_str = [d.strftime('%Y-%m-%d') for d in days]
    daily_received = [0.0] * 7
    daily_sent = [0.0] * 7

    for t in txs:
        try:
            t_date = timezone.localtime(t.sms_timestamp).date()
        except Exception:
            t_date = t.sms_timestamp.date()
            
        if t_date in days:
            idx = days.index(t_date)
            if t.type == 'RECEIVED':
                daily_received[idx] += float(t.amount)
            elif t.type == 'SENT':
                daily_sent[idx] += float(t.amount)

    # ── جلب وحساب حركات الخزينة والنقدية (Cash Ledger) ──
    cash_records = CashLedger.objects.filter(user=request.user).order_by('-created_at')
    cash_deposits = sum(r.amount for r in cash_records if r.type == 'DEPOSIT')
    cash_withdrawals = sum(r.amount for r in cash_records if r.type == 'WITHDRAWAL')
    cash_balance = cash_deposits - cash_withdrawals

    # ── حساب جهات الاتصال الأكثر تعاملاً (Top Contacts) ──
    contacts = {}
    for t in txs:
        c = t.decrypted_counterpart
        if c:
            if c not in contacts:
                contacts[c] = {"received_count": 0, "sent_count": 0, "received_amount": 0.0, "sent_amount": 0.0}
            if t.type == 'RECEIVED':
                contacts[c]["received_count"] += 1
                contacts[c]["received_amount"] += float(t.amount)
            elif t.type in ['SENT', 'BILL', 'PURCHASE', 'TOPUP']:
                contacts[c]["sent_count"] += 1
                contacts[c]["sent_amount"] += float(t.amount)

    sorted_contacts = sorted(
        [{"phone": k, **v, "total_count": v["received_count"] + v["sent_count"], "total_amount": v["received_amount"] + v["sent_amount"]} for k, v in contacts.items()],
        key=lambda x: x["total_amount"],
        reverse=True
    )[:15]

    # تجهيز مصفوفة العمليات مع إضافة حقل الربح المحسوب
    decorated_txs = []
    for t in txs[:200]: # زيادة الحد إلى 200 لعرض سجل كامل في جدول المعاملات
        t.calculated_fee = calculate_tx_fee(t)
        decorated_txs.append(t)

    analytics = {
        "total_received": total_received,
        "total_sent": total_sent,
        "total_fee": total_fee,
        "count": tx_count,
        "wallets_labels": list(wallets_data.keys()),
        "wallets_values": list(wallets_data.values()),
        "hours_values": hours_data,
        "days_labels": days_str,
        "daily_received": daily_received,
        "daily_sent": daily_sent,
        
        # بيانات الأرباح المفصلة
        "profit_cash": profit_cash,
        "profit_in_wallet": profit_in_wallet,
        "profit_unset": profit_unset,
        "wallet_profits_labels": list(wallet_profits.keys()),
        "wallet_profits_values": list(wallet_profits.values()),
    }
            
    context = {
        "licenses": user_licenses,
        "payments": user_payments,
        "active_license": active_license,
        "is_admin": request.user.is_staff or request.user.is_superuser,
        "user_transactions": decorated_txs,
        "analytics": analytics,
        
        # صفحات الديسكتوب الإضافية
        "cash_records": cash_records,
        "cash_balance": cash_balance,
        "top_contacts": sorted_contacts,
    }
    return render(request, 'web/dashboard.html', context)


@login_required
@csrf_exempt
def dashboard_update_profit_status(request):
    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        tx_id = data.get("transaction_id")
        profit_status = data.get("profit_status")
    except Exception:
        tx_id = request.POST.get("transaction_id")
        profit_status = request.POST.get("profit_status")
        
    if not tx_id or not profit_status:
        return JsonResponse({"success": False, "message": "Missing arguments"}, status=400)
        
    from licensing.models import MerchantTransaction
    tx = get_object_or_404(MerchantTransaction, transaction_id=tx_id, user=request.user)
    tx.profit_status = profit_status
    tx.save()
    return JsonResponse({"success": True, "message": "تم تحديث حالة الأرباح بنجاح."})


@login_required
@csrf_exempt
def dashboard_add_cash_movement(request):
    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        m_type = data.get("type")
        amount = float(data.get("amount", 0))
        description = data.get("description", "")
    except Exception:
        m_type = request.POST.get("type")
        amount = float(request.POST.get("amount", 0))
        description = request.POST.get("description", "")
        
    if not m_type or m_type not in ['DEPOSIT', 'WITHDRAWAL'] or amount <= 0:
        return JsonResponse({"success": False, "message": "بيانات الحركة غير صالحة"}, status=400)
        
    from licensing.models import CashLedger
    CashLedger.objects.create(
        user=request.user,
        type=m_type,
        amount=amount,
        description=description
    )
    return JsonResponse({"success": True, "message": "تم تسجيل الحركة في الخزينة بنجاح."})


@login_required
@csrf_exempt
def dashboard_delete_cash_movement(request, record_id):
    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)
    from licensing.models import CashLedger
    record = get_object_or_404(CashLedger, id=record_id, user=request.user)
    record.delete()
    return JsonResponse({"success": True, "message": "تم حذف حركة الخزينة."})


@login_required
def checkout_view(request, plan_type):
    if plan_type not in ['MONTHLY', 'YEARLY']:
        messages.error(request, "خطة اشتراك غير صالحة.")
        return redirect('dashboard')
        
    prices = {
        'MONTHLY': 150.00,  # EGP
        'YEARLY': 1200.00,  # EGP
    }
    
    plan_names = {
        'MONTHLY': 'الخطة الشهرية (Monthly Plan)',
        'YEARLY': 'الخطة السنوية (Yearly Plan)',
    }
    
    original_price = prices[plan_type]
    discount = 0.0
    final_price = original_price
    coupon_code = ""

    if request.method == 'POST':
        coupon_code = request.POST.get('coupon', '').strip().upper()
        action = request.POST.get('action', '') # 'apply_coupon' or 'pay'
        
        # Validate coupon if any
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code)
                if coupon.is_valid():
                    discount = (coupon.discount_percent / 100.0) * original_price
                    final_price = original_price - discount
                    if action == 'apply_coupon':
                        messages.success(request, f"تم تطبيق الكوبون بنجاح! خصم {coupon.discount_percent}%")
                else:
                    if action == 'apply_coupon':
                        messages.error(request, "هذا الكوبون منتهي أو تجاوز حد الاستخدام.")
                    coupon_code = ""
            except Coupon.DoesNotExist:
                if action == 'apply_coupon':
                    messages.error(request, "كوبون خصم غير صحيح.")
                coupon_code = ""

        if action == 'pay':
            payment_method = request.POST.get('payment_method', 'Credit Card')
            client_phone = request.POST.get('client_phone', '').strip()
            
            if payment_method == 'Vodafone Cash':
                if not client_phone:
                    messages.error(request, "يرجى إدخال رقم الهاتف المرتبط بالمحفظة.")
                    return redirect('checkout', plan_type=plan_type)
                
                normalized_phone = normalize_egyptian_phone(client_phone)
                if not normalized_phone.startswith('01') or len(normalized_phone) != 11:
                    messages.error(request, "رقم الهاتف غير صحيح. يجب إدخال رقم هاتف مصري مكوّن من 11 رقماً (مثال: 01012345678).")
                    return redirect('checkout', plan_type=plan_type)
                
                # Generate a suspended license key linked to the user
                key_format = f"VC-{plan_type[:4]}-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"
                lic = LicenseKey.objects.create(
                    key=key_format,
                    user=request.user,
                    client_name=request.user.username,
                    client_phone=normalized_phone,
                    type=plan_type,
                    status='SUSPENDED',
                    expires_at=timezone.now(), # not active yet
                    coupon_used=coupon_code or None
                )
                
                # Create pending payment record linking to the license key
                tx_id = f"PEND-{uuid.uuid4().hex[:10].upper()}"
                expires_at = timezone.now() + timedelta(minutes=30)
                
                PaymentRecord.objects.create(
                    user=request.user,
                    license_key=lic,
                    amount=final_price,
                    payment_method=payment_method,
                    transaction_id=tx_id,
                    sender_wallet=normalized_phone,
                    status='PENDING',
                    expires_at=expires_at,
                    coupon_code=coupon_code or None
                )
                return redirect('checkout_pending', payment_id=tx_id)
            
            else:
                # Credit Card Mockup Logic (keeps working as mockup for testing)
                key_format = f"VC-{plan_type[:4]}-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"
                duration = 30 if plan_type == 'MONTHLY' else 365
                
                if coupon_code:
                    try:
                        coupon = Coupon.objects.get(code=coupon_code)
                        if coupon.is_valid():
                            coupon.uses_count += 1
                            coupon.save()
                    except Coupon.DoesNotExist:
                        pass

                expires_at_val = timezone.now() + timedelta(days=duration)
                
                lic = LicenseKey.objects.create(
                    key=key_format,
                    user=request.user,
                    client_name=request.user.username,
                    client_phone=client_phone or getattr(request.user, 'phone', ''),
                    type=plan_type,
                    status='ACTIVE',
                    expires_at=expires_at_val,
                    coupon_used=coupon_code or None
                )
                
                tx_id = f"TXN-{uuid.uuid4().hex[:10].upper()}"
                PaymentRecord.objects.create(
                    user=request.user,
                    license_key=lic,
                    amount=final_price,
                    payment_method=payment_method,
                    transaction_id=tx_id,
                    status='SUCCESS'
                )
                
                send_license_email(request.user, lic.key, lic.type, lic.expires_at)
                
                messages.success(request, f"🎉 تم إتمام الدفع بنجاح وتوليد كود التفعيل: {lic.key}")
                return redirect('dashboard')

    context = {
        "plan_type": plan_type,
        "plan_name": plan_names[plan_type],
        "original_price": original_price,
        "discount": discount,
        "final_price": final_price,
        "coupon_code": coupon_code
    }
    return render(request, 'web/checkout.html', context)


@login_required
def checkout_pending_view(request, payment_id):
    payment = get_object_or_404(PaymentRecord, transaction_id=payment_id, user=request.user)
    
    if payment.status == 'SUCCESS':
        messages.success(request, "🎉 تم تفعيل اشتراكك بنجاح!")
        return redirect('dashboard')
    elif payment.status == 'FAILED' or (payment.expires_at and timezone.now() > payment.expires_at):
        if payment.status == 'PENDING':
            payment.status = 'FAILED'
            payment.save()
        messages.error(request, "عذراً، انتهت صلاحية طلب الدفع هذا أو تم إلغاؤه.")
        return redirect('dashboard')
        
    config = SiteConfiguration.get_solo()
    context = {
        "payment": payment,
        "admin_wallet": config.admin_wallet,
    }
    return render(request, 'web/checkout_pending.html', context)


@login_required
def check_payment_status_api(request, payment_id):
    payment = get_object_or_404(PaymentRecord, transaction_id=payment_id, user=request.user)
    
    if payment.status == 'PENDING' and payment.expires_at and timezone.now() > payment.expires_at:
        payment.status = 'FAILED'
        payment.save()
        
    elapsed_seconds = (timezone.now() - payment.created_at).total_seconds()
    
    return JsonResponse({
        "status": payment.status,
        "elapsed_seconds": int(elapsed_seconds),
        "expires_in": int((payment.expires_at - timezone.now()).total_seconds()) if payment.expires_at else 0,
        "license_key": payment.license_key.key if payment.license_key else None
    })


def backend_login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('admin_panel')
        return redirect('dashboard')
        
    if request.method == 'POST':
        u = request.POST.get('username', '').strip()
        p = request.POST.get('password', '').strip()
        
        user = authenticate(request, username=u, password=p)
        if user is not None:
            if user.is_staff or user.is_superuser:
                login(request, user)
                messages.success(request, "تم تسجيل دخول مدير النظام بنجاح.")
                return redirect('admin_panel')
            else:
                messages.error(request, "عذراً، هذا الحساب لا يملك صلاحيات لوحة الإدارة.")
        else:
            messages.error(request, "اسم المستخدم أو كلمة المرور غير صحيحة.")
            
    return render(request, 'web/backend_login.html')

def backend_logout_view(request):
    logout(request)
    messages.success(request, "تم تسجيل الخروج بنجاح.")
    return redirect('backend_login')

def admin_panel_view(request):
    if not request.user.is_authenticated:
        return redirect('backend_login')
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "غير مصرح لك بدخول لوحة تحكم الإدارة.")
        return redirect('dashboard')
        
    licenses = LicenseKey.objects.all().order_by('-created_at')
    coupons = Coupon.objects.all().order_by('-expires_at')
    payments = PaymentRecord.objects.all().order_by('-created_at')
    
    # Calculate stats
    stats = {
        "total_keys": licenses.count(),
        "active_keys": licenses.filter(status='ACTIVE', expires_at__gt=timezone.now()).count(),
        "expired_keys": licenses.filter(status='EXPIRED').count() + licenses.filter(status='ACTIVE', expires_at__lte=timezone.now()).count(),
        "total_revenue": sum(p.amount for p in payments),
        "total_users": User.objects.count()
    }
    
    if request.method == 'POST':
        action = request.POST.get('action', '')
        
        if action == 'generate_key':
            name = request.POST.get('client_name', '').strip()
            phone = request.POST.get('client_phone', '').strip()
            k_type = request.POST.get('key_type', 'MONTHLY')
            custom_days = request.POST.get('custom_days', '').strip()
            
            if not name:
                messages.error(request, "اسم العميل مطلوب لتوليد مفتاح تفعيل.")
            else:
                duration = 30
                if k_type == 'YEARLY':
                    duration = 365
                elif k_type == 'TRIAL':
                    duration = 3
                elif custom_days.isdigit():
                    duration = int(custom_days)
                    k_type = 'MONTHLY'
                    
                key_format = f"VC-{k_type[:4]}-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"
                expires_at = timezone.now() + timedelta(days=duration)
                
                user_obj = None
                try:
                    user_obj = User.objects.get(username=name)
                except User.DoesNotExist:
                    pass

                lic = LicenseKey.objects.create(
                    key=key_format,
                    user=user_obj,
                    client_name=name,
                    client_phone=phone,
                    type=k_type,
                    status='ACTIVE',
                    expires_at=expires_at
                )
                if user_obj and user_obj.email:
                    send_license_email(user_obj, lic.key, lic.type, lic.expires_at)
                    
                messages.success(request, f"تم توليد مفتاح الاشتراك بنجاح: {key_format}")
                
        elif action == 'create_coupon':
            code = request.POST.get('code', '').strip().upper()
            pct = float(request.POST.get('discount_percent', 0.0))
            days = int(request.POST.get('trial_days', 0))
            max_u = int(request.POST.get('max_uses', 100))
            exp_days = int(request.POST.get('expiry_days', 30))
            
            if not code:
                messages.error(request, "كود الكوبون مطلوب.")
            else:
                expires_at = timezone.now() + timedelta(days=exp_days)
                Coupon.objects.create(
                    code=code,
                    discount_percent=pct,
                    trial_days=days,
                    max_uses=max_u,
                    expires_at=expires_at,
                    is_active=True
                )
                messages.success(request, f"تم إنشاء الكوبون بنجاح: {code}")
                
        elif action == 'reset_mac':
            key = request.POST.get('license_key', '')
            lic = get_object_or_404(LicenseKey, key=key)
            lic.mac_address = None
            lic.save()
            messages.success(request, "تم إلغاء قفل الجهاز (Reset MAC) لهذا الترخيص بنجاح.")
            
        elif action == 'toggle_status':
            key = request.POST.get('license_key', '')
            lic = get_object_or_404(LicenseKey, key=key)
            lic.status = 'SUSPENDED' if lic.status == 'ACTIVE' else 'ACTIVE'
            lic.save()
            messages.success(request, f"تم تعديل حالة الترخيص إلى {lic.get_status_display()}")
            
        elif action == 'extend_expiry':
            key = request.POST.get('license_key', '')
            lic = get_object_or_404(LicenseKey, key=key)
            lic.expires_at += timedelta(days=30)
            if lic.status == 'EXPIRED':
                lic.status = 'ACTIVE'
            lic.save()
            messages.success(request, "تم تمديد فترة صلاحية الترخيص بمقدار 30 يوماً إضافية.")
            
        elif action == 'delete_key':
            key = request.POST.get('license_key', '')
            lic = get_object_or_404(LicenseKey, key=key)
            lic.delete()
            messages.success(request, "تم حذف مفتاح الاشتراك بنجاح.")
            
        elif action == 'delete_coupon':
            code = request.POST.get('code', '')
            c = get_object_or_404(Coupon, code=code)
            c.delete()
            messages.success(request, "تم حذف الكوبون بنجاح.")

        elif action == 'delete_user':
            user_id = request.POST.get('user_id', '')
            u_obj = get_object_or_404(User, id=user_id)
            if u_obj == request.user:
                messages.error(request, "لا يمكنك حذف حسابك الحالي.")
            else:
                u_obj.delete()
                messages.success(request, "تم حذف حساب المشترك بنجاح.")

        elif action == 'toggle_staff':
            user_id = request.POST.get('user_id', '')
            u_obj = get_object_or_404(User, id=user_id)
            if u_obj == request.user:
                messages.error(request, "لا يمكنك تعديل صلاحيات حسابك الحالي.")
            else:
                u_obj.is_staff = not u_obj.is_staff
                u_obj.save()
                messages.success(request, f"تم تعديل صلاحيات المشترك {u_obj.username} بنجاح.")

        elif action == 'create_user':
            username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip()
            pwd = request.POST.get('password', '').strip()
            is_admin_check = request.POST.get('is_admin', '') == 'true'

            if not username or not pwd:
                messages.error(request, "اسم المستخدم وكلمة المرور مطلوبة.")
            elif User.objects.filter(username=username).exists():
                messages.error(request, "اسم المستخدم هذا مسجل بالفعل.")
            else:
                new_u = User.objects.create_user(username=username, email=email, password=pwd)
                if is_admin_check:
                    new_u.is_staff = True
                    new_u.save()
                messages.success(request, f"تم إنشاء حساب المشترك الجديد بنجاح: {username}")

        elif action == 'record_payment':
            user_id = request.POST.get('user_id', '')
            amount_str = request.POST.get('amount', '0').strip()
            pay_method = request.POST.get('payment_method', 'Other').strip()
            txn_id = request.POST.get('transaction_id', '').strip()
            dur_type = request.POST.get('duration_type', 'MONTHLY').strip()
            custom_days_str = request.POST.get('custom_days', '').strip()
            op_type = request.POST.get('operation_type', 'new').strip()

            try:
                user_obj = User.objects.get(id=user_id)
            except User.DoesNotExist:
                messages.error(request, "المشترك المحدد غير موجود.")
                return redirect('admin_panel')

            try:
                amount = float(amount_str)
            except ValueError:
                messages.error(request, "المبلغ المدفوع غير صحيح.")
                return redirect('admin_panel')

            if not txn_id:
                txn_id = f"MANUAL-{uuid.uuid4().hex[:10].upper()}"

            if PaymentRecord.objects.filter(transaction_id=txn_id).exists():
                messages.error(request, f"رقم العملية المالي {txn_id} مسجل بالفعل.")
                return redirect('admin_panel')

            days = 30
            if dur_type == 'YEARLY':
                days = 365
            elif dur_type == 'TRIAL':
                days = 3
            elif dur_type == 'CUSTOM' and custom_days_str.isdigit():
                days = int(custom_days_str)
            else:
                dur_type = 'MONTHLY'

            lic = None
            if op_type == 'extend':
                lic = LicenseKey.objects.filter(user=user_obj, status='ACTIVE', expires_at__gt=timezone.now()).order_by('-expires_at').first()
                if lic:
                    lic.expires_at += timedelta(days=days)
                    lic.save()
                    messages.success(request, f"تم تمديد الترخيص النشط ({lic.key}) للمشترك {user_obj.username} بمقدار {days} يوماً.")
                else:
                    op_type = 'new'
                    messages.warning(request, f"لم يعثر على ترخيص نشط للمشترك {user_obj.username}، تم توليد ترخيص جديد بدلاً من التمديد.")

            if op_type == 'new':
                key_format = f"VC-{dur_type[:4]}-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"
                expires_at = timezone.now() + timedelta(days=days)
                lic = LicenseKey.objects.create(
                    key=key_format,
                    user=user_obj,
                    client_name=user_obj.username,
                    client_phone=getattr(user_obj, 'phone', ''),
                    type=dur_type if dur_type in ['MONTHLY', 'YEARLY', 'TRIAL'] else 'MONTHLY',
                    status='ACTIVE',
                    expires_at=expires_at
                )
                messages.success(request, f"تم إنشاء ترخيص جديد للمشترك {user_obj.username} بنجاح: {key_format}")

            PaymentRecord.objects.create(
                user=user_obj,
                license_key=lic,
                amount=amount,
                payment_method=pay_method,
                transaction_id=txn_id,
                status='SUCCESS'
            )

            # Send payment confirmation and license details via WhatsApp
            send_whatsapp_payment_confirmation(user_obj, amount, lic.key)

        elif action == 'delete_payment':
            pay_id = request.POST.get('payment_id', '')
            pay_obj = get_object_or_404(PaymentRecord, id=pay_id)
            pay_obj.delete()
            messages.success(request, "تم حذف سجل العملية المالي بنجاح.")

        elif action == 'delete_pattern':
            p_id = request.POST.get('pattern_id', '')
            from licensing.models import SMSPattern
            p = get_object_or_404(SMSPattern, pattern_id=p_id)
            p.delete()
            messages.success(request, "تم حذف نمط تحليل الرسائل بنجاح.")

        elif action == 'delete_merchant_transaction':
            tx_id = request.POST.get('transaction_id', '')
            from licensing.models import MerchantTransaction
            tx_obj = get_object_or_404(MerchantTransaction, transaction_id=tx_id)
            tx_obj.delete()
            messages.success(request, "تم حذف معاملة التاجر بنجاح.")

        elif action == 'update_settings':
            cfg = SiteConfiguration.get_solo()
            cfg.admin_wallet = request.POST.get('admin_wallet', '').strip()
            cfg.gateway_api_key = request.POST.get('gateway_api_key', '').strip()
            cfg.infobip_api_key = request.POST.get('infobip_api_key', '').strip()
            cfg.infobip_base_url = request.POST.get('infobip_base_url', '').strip()
            cfg.infobip_from_email = request.POST.get('infobip_from_email', '').strip()
            cfg.resend_api_key = request.POST.get('resend_api_key', '').strip()
            cfg.resend_from_email = request.POST.get('resend_from_email', '').strip()
            
            cfg.whatsapp_enabled = request.POST.get('whatsapp_enabled', '') == 'true' or request.POST.get('whatsapp_enabled', '') == 'on'
            cfg.whatsapp_from_number = request.POST.get('whatsapp_from_number', '').strip()
            cfg.whatsapp_template_otp = request.POST.get('whatsapp_template_otp', '').strip()
            cfg.whatsapp_template_welcome = request.POST.get('whatsapp_template_welcome', '').strip()
            cfg.whatsapp_template_payment = request.POST.get('whatsapp_template_payment', '').strip()
            cfg.whatsapp_template_language = request.POST.get('whatsapp_template_language', '').strip() or 'en'
            cfg.save()
            messages.success(request, "تم تحديث إعدادات النظام بنجاح.")

        return redirect('admin_panel')

    users = User.objects.all().order_by('-date_joined')
    from licensing.models import UnclassifiedSMSReport, SMSPattern, MerchantTransaction
    from django.db.models import Count, Sum
    
    unclassified_reports = UnclassifiedSMSReport.objects.all().order_by('-received_at')
    patterns_list = SMSPattern.objects.all().order_by('-created_at')
    merchant_transactions = MerchantTransaction.objects.all().order_by('-sms_timestamp')

    # ── حساب إحصائيات التحليلات التجارية للإدارة ──
    merchant_tx_stats = MerchantTransaction.objects.values('user__username').annotate(
        tx_count=Count('transaction_id'),
        total_amount=Sum('amount')
    ).order_by('-total_amount')
    
    admin_merchant_names = [item['user__username'] for item in merchant_tx_stats]
    admin_merchant_counts = [item['tx_count'] for item in merchant_tx_stats]
    admin_merchant_amounts = [float(item['total_amount']) for item in merchant_tx_stats]

    wallet_dist = MerchantTransaction.objects.values('wallet_id').annotate(
        count=Count('transaction_id')
    ).order_by('-count')
    admin_wallet_labels = [item['wallet_id'] or "غير محدد" for item in wallet_dist]
    admin_wallet_counts = [item['count'] for item in wallet_dist]

    # ── حساب تحليلات تفصيلية لكل تاجر بشكل منفصل ──
    import json
    import datetime
    merchant_analytics_data = {}
    
    def calculate_tx_fee_helper(tx):
        w_id = (tx.wallet_id or "").strip().lower()
        if not w_id or w_id in ["unspecified", ""]:
            return 0.0
        amount = float(tx.amount)
        if tx.type == 'RECEIVED': # سحب للعميل
            return max(amount * 0.01, 5.0) if amount > 0 else 0.0
        elif tx.type in ['SENT', 'BILL', 'PURCHASE', 'TOPUP']: # إيداع للعميل
            return max(amount * 0.005, 5.0) if amount > 0 else 0.0
        return 0.0

    today = timezone.localtime(timezone.now()).date()
    days_range = [today - datetime.timedelta(days=i) for i in range(6, -1, -1)]
    days_str = [d.strftime('%Y-%m-%d') for d in days_range]

    all_txs_by_user = {}
    for tx in MerchantTransaction.objects.all().order_by('-sms_timestamp'):
        all_txs_by_user.setdefault(tx.user_id, []).append(tx)

    for u in users:
        u_txs = all_txs_by_user.get(u.id, [])
        u_total_received = sum(t.amount for t in u_txs if t.type == 'RECEIVED')
        u_total_sent = sum(t.amount for t in u_txs if t.type == 'SENT')
        
        u_total_fee = 0.0
        u_profit_cash = 0.0
        u_profit_in_wallet = 0.0
        u_profit_unset = 0.0
        u_wallet_profits = {}
        
        u_wallets_data = {}
        u_hours_data = [0] * 24
        
        u_daily_received = [0.0] * 7
        u_daily_sent = [0.0] * 7
        
        u_contacts = {}
        
        for t in u_txs:
            fee = calculate_tx_fee_helper(t)
            u_total_fee += fee
            
            w_id = t.wallet_id or "غير محدد"
            u_wallet_profits[w_id] = u_wallet_profits.get(w_id, 0.0) + fee
            
            p_status = t.profit_status or "UNSET"
            if p_status == 'CASH':
                u_profit_cash += fee
            elif p_status == 'IN_WALLET':
                u_profit_in_wallet += fee
            else:
                u_profit_unset += fee
                
            u_wallets_data[w_id] = u_wallets_data.get(w_id, 0) + 1
            
            try:
                local_time = timezone.localtime(t.sms_timestamp)
                u_hours_data[local_time.hour] += 1
            except Exception:
                u_hours_data[t.sms_timestamp.hour] += 1
                
            try:
                t_date = timezone.localtime(t.sms_timestamp).date()
            except Exception:
                t_date = t.sms_timestamp.date()
                
            if t_date in days_range:
                idx = days_range.index(t_date)
                if t.type == 'RECEIVED':
                    u_daily_received[idx] += float(t.amount)
                elif t.type == 'SENT':
                    u_daily_sent[idx] += float(t.amount)
                    
            c = t.decrypted_counterpart
            if c:
                if c not in u_contacts:
                    u_contacts[c] = {"received_count": 0, "sent_count": 0, "received_amount": 0.0, "sent_amount": 0.0}
                if t.type == 'RECEIVED':
                    u_contacts[c]["received_count"] += 1
                    u_contacts[c]["received_amount"] += float(t.amount)
                elif t.type in ['SENT', 'BILL', 'PURCHASE', 'TOPUP']:
                    u_contacts[c]["sent_count"] += 1
                    u_contacts[c]["sent_amount"] += float(t.amount)

        u_sorted_contacts = sorted(
            [{"phone": k, **v, "total_count": v["received_count"] + v["sent_count"], "total_amount": v["received_amount"] + v["sent_amount"]} for k, v in u_contacts.items()],
            key=lambda x: x["total_amount"],
            reverse=True
        )[:10]

        merchant_analytics_data[u.username] = {
            "total_received": float(u_total_received),
            "total_sent": float(u_total_sent),
            "total_fee": float(u_total_fee),
            "count": len(u_txs),
            "wallets_labels": list(u_wallets_data.keys()),
            "wallets_values": list(u_wallets_data.values()),
            "hours_values": u_hours_data,
            "days_labels": days_str,
            "daily_received": u_daily_received,
            "daily_sent": u_daily_sent,
            "profit_cash": float(u_profit_cash),
            "profit_in_wallet": float(u_profit_in_wallet),
            "profit_unset": float(u_profit_unset),
            "wallet_profits_labels": list(u_wallet_profits.keys()),
            "wallet_profits_values": list(u_wallet_profits.values()),
            "top_contacts": u_sorted_contacts
        }

    context = {
        "stats": stats,
        "licenses": licenses,
        "coupons": coupons,
        "payments": payments,
        "users": users,
        "config": SiteConfiguration.get_solo(),
        "unclassified_reports": unclassified_reports,
        "patterns_list": patterns_list,
        "merchant_transactions": merchant_transactions,
        
        # بيانات التحليلات التجارية المركزية والتفصيلية
        "admin_merchant_names": admin_merchant_names,
        "admin_merchant_counts": admin_merchant_counts,
        "admin_merchant_amounts": admin_merchant_amounts,
        "admin_wallet_labels": admin_wallet_labels,
        "admin_wallet_counts": admin_wallet_counts,
        "merchant_analytics_json": json.dumps(merchant_analytics_data),
    }
    return render(request, 'web/admin_panel.html', context)


def verify_email_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    username = request.session.get('verification_username')
    if not username:
        messages.error(request, "لم يتم العثور على جلسة تحقق صالحة. يرجى تسجيل الدخول أو إنشاء حساب.")
        return redirect('login')
        
    user = get_object_or_404(User, username=username)
    profile = user.profile
    
    if profile.email_verified:
        messages.success(request, "الحساب مؤكد بالفعل. يرجى تسجيل الدخول.")
        return redirect('login')
        
    if request.method == 'POST':
        otp_input = request.POST.get('otp', '').strip()
        
        if not otp_input:
            messages.error(request, "يرجى إدخال رمز التحقق.")
        elif profile.otp_code != otp_input:
            messages.error(request, "رمز التحقق غير صحيح.")
        else:
            # Check expiration (15 minutes)
            if profile.otp_created_at:
                expiration_time = profile.otp_created_at + timedelta(minutes=15)
                if timezone.now() > expiration_time:
                    messages.error(request, "انتهت صلاحية رمز التحقق. يرجى طلب رمز جديد.")
                    return render(request, 'web/verify_email.html', {'phone': profile.phone})
            
            # OTP is correct! Mark verified
            profile.email_verified = True
            profile.otp_code = None
            profile.otp_created_at = None
            profile.save()
            
            # Create a 7-day trial license key for this user
            trial_key = f"VC-TRIAL-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"
            expires_at = timezone.now() + timedelta(days=7)
            
            lic = LicenseKey.objects.create(
                key=trial_key,
                user=user,
                client_name=user.username,
                type='TRIAL',
                status='ACTIVE',
                expires_at=expires_at
            )
            
            # Send welcome & activation details via WhatsApp
            send_whatsapp_welcome(user, lic.key)
            
            # Log user in
            login(request, user)
            
            # Clear session
            if 'verification_username' in request.session:
                del request.session['verification_username']
                
            messages.success(request, f"تم تأكيد حسابك وتفعيل فترة تجريبية مجانية (7 أيام)! مفتاح التفعيل الخاص بك: {lic.key}")
            return redirect('dashboard')
            
    return render(request, 'web/verify_email.html', {'phone': profile.phone})


def resend_otp_view(request):
    username = request.session.get('verification_username')
    if not username:
        return JsonResponse({'success': False, 'message': 'جلسة غير صالحة.'}, status=400)
        
    try:
        user = User.objects.get(username=username)
        if user.profile.email_verified:
            return JsonResponse({'success': False, 'message': 'الحساب مؤكد بالفعل.'}, status=400)
            
        # Send new verification OTP via WhatsApp
        send_whatsapp_otp(user)
        return JsonResponse({'success': True, 'message': 'تم إعادة إرسال رمز التحقق بنجاح عبر الواتس آب!'})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'المستخدم غير موجود.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'فشل الإرسال: {str(e)}'}, status=500)


from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def admin_api_analyze_sms(request):
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({"success": False, "message": "Unauthorized"}, status=403)
    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)
    
    try:
        body_unicode = request.body.decode('utf-8')
        data = json.loads(body_unicode)
        sms_id = data.get("sms_id")
    except Exception as e:
        import traceback
        logger.error(f"JSON Parse error: {e}\n{traceback.format_exc()}")
        return JsonResponse({"success": False, "message": f"Invalid JSON: {str(e)}"}, status=400)
        
    from licensing.models import UnclassifiedSMSReport
    try:
        report = UnclassifiedSMSReport.objects.get(id=sms_id)
    except UnclassifiedSMSReport.DoesNotExist:
        return JsonResponse({"success": False, "message": "SMS Report not found"}, status=404)
        
    from dotenv import load_dotenv
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # backend/
    load_dotenv(os.path.join(base_dir, '.env'))

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return JsonResponse({"success": False, "message": f"لم يتم ضبط مفتاح GEMINI_API_KEY في السيرفر. المسار المستهدف: {os.path.join(base_dir, '.env')}"}, status=400)
        
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
                {"text": f"SMS Message to analyze:\nSender: {report.sender}\nBody: {report.raw_sms}"}
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
        import httpx
        response = httpx.post(url, json=payload, timeout=20.0)
        if response.status_code != 200:
            # Fallback to local heuristics if Gemini fails (e.g. 429 quota reached)
            logger.warning(f"Gemini API returned error status {response.status_code}. Falling back to local heuristics.")
            fallback_data = heuristic_regex_proposer(report.raw_sms)
            return JsonResponse({"success": True, "analysis": fallback_data, "note": "تحذير: تم استخدام التحليل المحلي الاحتياطي لانتهاء حصة مفتاح Gemini."})
        
        result = response.json()
        text_response = result['candidates'][0]['content']['parts'][0]['text']
        parsed_data = json.loads(text_response.strip())
        return JsonResponse({"success": True, "analysis": parsed_data})
    except Exception as e:
        logger.error(f"Failed to analyze using Gemini: {e}. Falling back to local heuristics.")
        try:
            fallback_data = heuristic_regex_proposer(report.raw_sms)
            return JsonResponse({"success": True, "analysis": fallback_data, "note": "تحذير: تم استخدام التحليل المحلي الاحتياطي بسبب خطأ في الشبكة."})
        except Exception as fallback_err:
            return JsonResponse({"success": False, "message": f"Failed to analyze: {str(e)}"}, status=500)


def heuristic_regex_proposer(raw_sms: str) -> dict:
    """
    محلل احتياطي ذكي (Heuristic Fallback) لتوليد نمط عندما يفشل الـ API الخاص بـ Gemini.
    """
    import re
    pattern = raw_sms
    groups = {}
    group_idx = 1
    
    # 1. Date (e.g., 2026-06-26 or 26-06-26)
    date_match = re.search(r'(\d{2,4}-\d{2}-\d{2,4})', raw_sms)
    if date_match:
        pattern = pattern.replace(date_match.group(1), r"(\d{2,4}-\d{2}-\d{2,4})")
        groups["date"] = group_idx
        group_idx += 1

    # 2. Time (e.g., 14:30)
    time_match = re.search(r'(\d{2}:\d{2}(?::\d{2})?)', raw_sms)
    if time_match:
        pattern = pattern.replace(time_match.group(1), r"(\d{2}:\d{2}(?::\d{2})?)")
        groups["time"] = group_idx
        group_idx += 1

    # 3. Transaction ID (large integer, usually 10+ digits)
    trx_match = re.search(r'\b(\d{10,15})\b', raw_sms)
    if trx_match:
        pattern = pattern.replace(trx_match.group(1), r"(\d{10,15})")
        groups["trx_id"] = group_idx
        group_idx += 1

    # 4. Phone numbers (11 digits starting with 01)
    phone_match = re.search(r'\b(01\d{9})\b', raw_sms)
    if phone_match:
        pattern = pattern.replace(phone_match.group(1), r"(\d{11})")
        groups["counterpart"] = group_idx
        group_idx += 1

    # Clean escaping for regex metacharacters
    escaped_pattern = re.escape(pattern)
    # Restore the captured group placeholders
    escaped_pattern = escaped_pattern.replace(r"\(\d\{2,4\}\-\\d\{2\}\-\\d\{2,4\}\)", r"(\d{2,4}-\d{2}-\d{2,4})")
    escaped_pattern = escaped_pattern.replace(r"\(\d\{2\}\:\\d\{2\}\(\?\:\\\:\\d\{2\}\)\?\)", r"(\d{2}:\d{2}(?::\d{2})?)")
    escaped_pattern = escaped_pattern.replace(r"\(\d\{10,15\}\)", r"(\d{10,15})")
    escaped_pattern = escaped_pattern.replace(r"\(\d\{11\}\)", r"(\d{11})")

    # Guess type
    tx_type = "RECEIVED"
    if "تحويل" in raw_sms and ("إلى" in raw_sms or "لرقم" in raw_sms):
        tx_type = "SENT"
    elif "سحب" in raw_sms or "atm" in raw_sms.lower():
        tx_type = "ATM_WITHDRAWAL"
    elif "إيداع" in raw_sms or "deposit" in raw_sms.lower():
        tx_type = "ATM_DEPOSIT"
    elif "رصيد" in raw_sms:
        tx_type = "BALANCE"

    return {
        "type": tx_type,
        "regex_pattern": escaped_pattern,
        "groups": groups,
        "confidence": 0.5
    }


@csrf_exempt
def admin_api_save_pattern(request):
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({"success": False, "message": "Unauthorized"}, status=403)
    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)
        
    try:
        data = json.loads(request.body)
        pattern_id = data.get("pattern_id")
        tx_type = data.get("type")
        regex_pattern = data.get("regex_pattern")
        groups = data.get("groups", {})
        sms_id = data.get("sms_id")
    except Exception:
        return JsonResponse({"success": False, "message": "Invalid JSON"}, status=400)
        
    if not pattern_id or not tx_type or not regex_pattern:
        return JsonResponse({"success": False, "message": "Missing required fields"}, status=400)
        
    from licensing.models import SMSPattern, UnclassifiedSMSReport
    try:
        SMSPattern.objects.update_or_create(
            pattern_id=pattern_id,
            defaults={
                "type": tx_type,
                "regex_pattern": regex_pattern,
                "groups_json": json.dumps(groups),
                "is_active": True
            }
        )
        
        if sms_id:
            UnclassifiedSMSReport.objects.filter(id=sms_id).delete()
            
        return JsonResponse({"success": True, "message": "تم حفظ النمط بنجاح وصياغته وتحديث النظام."})
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Failed to save: {str(e)}"}, status=500)


@csrf_exempt
def admin_api_delete_unclassified(request):
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({"success": False, "message": "Unauthorized"}, status=403)
    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)
        
    try:
        data = json.loads(request.body)
        sms_id = data.get("sms_id")
    except Exception:
        return JsonResponse({"success": False, "message": "Invalid JSON"}, status=400)
        
    from licensing.models import UnclassifiedSMSReport
    UnclassifiedSMSReport.objects.filter(id=sms_id).delete()
    return JsonResponse({"success": True, "message": "تم حذف الرسالة بنجاح."})


