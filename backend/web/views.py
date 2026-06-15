import os
import uuid
import logging
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, FileResponse, Http404
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from licensing.models import LicenseKey, Coupon, PaymentRecord, SiteConfiguration
from licensing.utils import normalize_egyptian_phone

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
        has_whatsapp = request.POST.get('has_whatsapp', '') == 'true'
        
        if not u or not p:
            messages.error(request, "يرجى ملء جميع الحقول المطلوبة.")
            return render(request, 'web/register.html')
            
        if p != p_c:
            messages.error(request, "كلمتا المرور غير متطابقتين.")
            return render(request, 'web/register.html')
            
        if User.objects.filter(username=u).exists():
            messages.error(request, "اسم المستخدم هذا مسجل بالفعل.")
            return render(request, 'web/register.html')
            
        try:
            user = User.objects.create_user(username=u, email=e, password=p)
            
            # Save UserProfile fields
            profile = user.profile
            profile.phone = phone
            profile.has_whatsapp = has_whatsapp
            profile.save()
            
            login(request, user)
            
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
            
            send_welcome_email(user)
            send_license_email(user, lic.key, lic.type, lic.expires_at)
            
            messages.success(request, f"تم تسجيل الحساب وتفعيل فترة تجريبية مجانية (7 أيام)! مفتاح التفعيل الخاص بك: {lic.key}")
            return redirect('dashboard')
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
            profile.save()

            send_welcome_email(user)
            messages.success(request, f"مرحباً بك! تم تسجيل حسابك عبر {provider.capitalize()} وتفعيل اشتراك تجريبي 7 أيام.")
        else:
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
            
    context = {
        "licenses": user_licenses,
        "payments": user_payments,
        "active_license": active_license,
        "is_admin": request.user.is_staff or request.user.is_superuser
    }
    return render(request, 'web/dashboard.html', context)

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

            if user_obj.email:
                send_license_email(user_obj, lic.key, lic.type, lic.expires_at)

        elif action == 'delete_payment':
            pay_id = request.POST.get('payment_id', '')
            pay_obj = get_object_or_404(PaymentRecord, id=pay_id)
            pay_obj.delete()
            messages.success(request, "تم حذف سجل العملية المالي بنجاح.")

        return redirect('admin_panel')

    users = User.objects.all().order_by('-date_joined')

    context = {
        "stats": stats,
        "licenses": licenses,
        "coupons": coupons,
        "payments": payments,
        "users": users
    }
    return render(request, 'web/admin_panel.html', context)
