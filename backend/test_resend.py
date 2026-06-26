import os
import django
import sys

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from web.infobip import send_email_via_provider
from licensing.models import SiteConfiguration

def test_send():
    config = SiteConfiguration.get_solo()
    print("--- Test Resend Configuration ---")
    print(f"Resend API Key: {config.resend_api_key}")
    print(f"Resend From Email: {config.resend_from_email}")
    
    if not config.resend_api_key:
        print("Error: Resend API Key is empty in the database!")
        return
        
    print("\nSending test email...")
    success = send_email_via_provider(
        to_email="iik20001998@gmail.com",
        subject="Test Resend from Django",
        html_content="<p>This is a test email sent from Django database config.</p>"
    )
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")

if __name__ == "__main__":
    test_send()
