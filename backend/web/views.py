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
from licensing.models import LicenseKey, Coupon, PaymentRecord

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

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        u = request.POST.get('username', '').strip()
        p = request.POST.get('password', '').strip()
        
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            messages.success(request, "تم تسجيل الدخول بنجاح.")
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
            # Perform payment mockup
            payment_method = request.POST.get('payment_method', 'Credit Card')
            client_phone = request.POST.get('client_phone', '').strip()
            
            # Generate a new license key
            key_format = f"VC-{plan_type[:4]}-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"
            duration = 30 if plan_type == 'MONTHLY' else 365
            
            # If coupon was valid, apply it and use it
            if coupon_code:
                try:
                    coupon = Coupon.objects.get(code=coupon_code)
                    if coupon.is_valid():
                        coupon.uses_count += 1
                        coupon.save()
                except Coupon.DoesNotExist:
                    pass

            expires_at = timezone.now() + timedelta(days=duration)
            
            # Create license
            lic = LicenseKey.objects.create(
                key=key_format,
                user=request.user,
                client_name=request.user.username,
                client_phone=client_phone or getattr(request.user, 'phone', ''),
                type=plan_type,
                status='ACTIVE',
                expires_at=expires_at,
                coupon_used=coupon_code or None
            )
            
            # Create payment record
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
def admin_panel_view(request):
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

        return redirect('admin_panel')
        
    context = {
        "stats": stats,
        "licenses": licenses,
        "coupons": coupons,
        "payments": payments
    }
    return render(request, 'web/admin_panel.html', context)
