import os
import sys
import django
from dotenv import load_dotenv

# Set up django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

# Load dotenv
load_dotenv()

django.setup()

from django.core.mail import send_mail
from django.conf import settings

def test_smtp():
    print("--- اختبار إعدادات SMTP لدفتر كاش ---")
    print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    
    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        print("\n⚠️ تنبيه: لم يتم ضبط EMAIL_HOST_USER أو EMAIL_HOST_PASSWORD في ملف الـ .env.")
        print("البرنامج حالياً يقوم بالتراجع التلقائي وعرض الرسائل في الـ Console (الشاشة) بدلاً من الإرسال الفعلي.")
        print("يرجى ملء بيانات البريد الإلكتروني وكلمة المرور في ملف .env لتشغيل الإرسال الحقيقي.")
        
        target_email = input("\nاكتب بريد إلكتروني افتراضي لتجربة الطباعة في الكونسول: ").strip()
    else:
        target_email = input("\nاكتب البريد الإلكتروني الذي ترغب في إرسال رسالة تجريبية حقيقية إليه: ").strip()
        
    if not target_email:
        print("تم الإلغاء.")
        return

    try:
        print("\nجاري محاولة إرسال البريد التجريبي...")
        send_mail(
            subject='رسالة تجريبية من دفتر كاش 🚀',
            message='أهلاً بك! هذه رسالة تجريبية للتأكد من صحة إعدادات خادم البريد الإلكتروني SMTP الخاص بك لدفتر كاش.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[target_email],
            fail_silently=False,
        )
        print("\n✅ تم إرسال الرسالة بنجاح! يرجى التحقق من صندوق الوارد أو البريد المزعج (Spam) للبريد المستهدف.")
    except Exception as e:
        print(f"\n❌ فشل إرسال البريد الإلكتروني. الخطأ التفصيلي:")
        print(str(e))
        print("\n💡 نصائح للحل:")
        if "Gmail" in settings.EMAIL_HOST or "gmail" in settings.EMAIL_HOST:
            print("1. إذا كنت تستخدم Gmail، تأكد من إنشاء وتفعيل 'كلمة مرور التطبيقات (App Password)' وليس كلمة مرور حسابك العادية.")
            print("2. تأكد من تفعيل التحقق بخطوتين (2-Step Verification) في حساب جوجل لتتمكن من إنشاء كلمة مرور التطبيق.")
        elif "sendgrid" in settings.EMAIL_HOST:
            print("1. إذا كنت تستخدم SendGrid، تأكد من أن الـ Host User هو 'apikey' (كلمة apikey حرفياً).")
            print("2. تأكد من أن الـ Host Password هي قيمة الـ API Key التي قمت بإنشائها من لوحة تحكم SendGrid.")
        print("3. تأكد من صحة المنفذ (Port) والـ TLS (غالباً المنفذ 587 مع TLS=True، أو 465 مع SSL).")

if __name__ == "__main__":
    test_smtp()
