import os
import random
import logging
import requests
import re
from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from licensing.models import SiteConfiguration

logger = logging.getLogger(__name__)

def format_whatsapp_phone(phone: str) -> str:
    """
    Formats a phone number to international WhatsApp format (e.g. 201099437596).
    """
    if not phone:
        return ""
    # Remove all non-numeric characters
    digits = re.sub(r'\D', '', phone)
    
    # Handle Egypt specific normalization
    # If starting with +2 or 002, strip it
    if digits.startswith('002'):
        digits = digits[3:]
    elif digits.startswith('2') and len(digits) > 11:
        # Keep it as is if it looks like a valid international number starting with 2 (e.g. 2010...)
        pass
    # If starting with a single 0 followed by 1 (e.g. 010xxx, 011xxx, 012xxx, 015xxx)
    elif digits.startswith('01') and len(digits) == 11:
        digits = '2' + digits[1:]
    # If starting with 1 (e.g. 10xxx, 11xxx, 12xxx)
    elif digits.startswith('1') and len(digits) == 10:
        digits = '20' + digits
        
    return digits

def send_whatsapp_template(to_phone, template_name, placeholders):
    """
    Sends a WhatsApp message using an Infobip template.
    """
    config = SiteConfiguration.get_solo()
    if not config.whatsapp_enabled:
        logger.info("WhatsApp notifications are disabled in SiteConfiguration.")
        return False

    api_key = config.infobip_api_key or os.environ.get('INFOBIP_API_KEY')
    base_url = config.infobip_base_url or os.environ.get('INFOBIP_BASE_URL')
    from_number = config.whatsapp_from_number or "447860088970"
    template_lang = config.whatsapp_template_language or "en"

    if not api_key or not base_url:
        logger.error("Infobip API Key or Base URL is missing. Cannot send WhatsApp template.")
        return False

    # Normalize phone
    formatted_to = format_whatsapp_phone(to_phone)
    if not formatted_to:
        logger.error(f"Cannot send WhatsApp, invalid phone number: {to_phone}")
        return False

    # Standardize Base URL
    base_url = base_url.strip()
    if not base_url.startswith('http'):
        base_url = 'https://' + base_url
    base_url = base_url.rstrip('/')

    url = f"{base_url}/whatsapp/1/message/template"
    headers = {
        'Authorization': f'App {api_key}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    payload = {
        "messages": [
            {
                "from": from_number,
                "to": formatted_to,
                "content": {
                    "templateName": template_name,
                    "templateData": {
                        "body": {
                            "placeholders": placeholders
                        }
                    },
                    "language": template_lang
                }
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code >= 400:
            logger.error(f"Infobip WhatsApp API returned error: {response.status_code} - {response.text}")
            return False
        logger.info(f"WhatsApp template '{template_name}' successfully sent to {formatted_to}")
        return True
    except Exception as e:
        logger.error(f"Exception sending WhatsApp template: {e}")
        return False

def send_whatsapp_otp(user):
    """
    Generates a 6-digit OTP code, stores it in the user's profile, and sends it via WhatsApp.
    """
    otp = f"{random.randint(100000, 999999)}"
    
    profile = user.profile
    profile.otp_code = otp
    profile.otp_created_at = timezone.now()
    profile.save()
    
    config = SiteConfiguration.get_solo()
    template_name = config.whatsapp_template_otp or "test_whatsapp_template_en"
    
    # Most OTP templates accept either the name first then the OTP, or just the OTP
    # We will pass [otp] and if they have user name we can pass [user.username, otp]
    # Let's check template configurations or just pass [otp]
    placeholders = [otp]
    
    phone = profile.phone
    if not phone:
        logger.error(f"Cannot send WhatsApp OTP for user {user.username}, no phone number stored.")
        return False
        
    return send_whatsapp_template(phone, template_name, placeholders)

def send_whatsapp_welcome(user, license_key):
    """
    Sends a welcome WhatsApp message to the user with their license details.
    """
    config = SiteConfiguration.get_solo()
    template_name = config.whatsapp_template_welcome
    if not template_name:
        logger.info("WhatsApp welcome template not configured.")
        return False

    phone = user.profile.phone
    if not phone:
        return False

    placeholders = [user.username, license_key]
    return send_whatsapp_template(phone, template_name, placeholders)

def send_whatsapp_payment_confirmation(user, amount, license_key):
    """
    Sends a payment confirmation WhatsApp message to the user.
    """
    config = SiteConfiguration.get_solo()
    template_name = config.whatsapp_template_payment
    if not template_name:
        logger.info("WhatsApp payment template not configured.")
        return False

    phone = user.profile.phone
    if not phone:
        return False

    placeholders = [user.username, f"{amount:.2f}", license_key]
    return send_whatsapp_template(phone, template_name, placeholders)
