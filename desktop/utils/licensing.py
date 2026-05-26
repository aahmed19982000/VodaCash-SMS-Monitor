# desktop/utils/licensing.py
import os
import json
import uuid
import logging
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger("VodaCash.Licensing")

def get_mac_address() -> str:
    """Retrieve the MAC address of the system reliably."""
    try:
        node = uuid.getnode()
        mac = ':'.join(['{:02x}'.format((node >> ele) & 0xff) for ele in range(0, 8*6, 8)][::-1])
        return mac.lower()
    except Exception as e:
        logger.error(f"Error getting MAC address: {e}")
        return "00:00:00:00:00:00"

def get_supabase_credentials(db=None) -> tuple:
    """
    Get Supabase URL and Key in order of precedence:
    1. Environment variables (SUPABASE_URL, SUPABASE_KEY)
    2. SQLite database settings table (supabase_url, supabase_key)
    3. supabase_config.json file in the root
    """
    # 1. Environment
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if url and key:
        return url.strip(), key.strip()

    # 2. SQLite DB
    if db:
        url = db.get_setting("supabase_url", "")
        key = db.get_setting("supabase_key", "")
        if url and key:
            return url.strip(), key.strip()

    # 3. JSON file
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "supabase_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                u = data.get("SUPABASE_URL") or data.get("supabase_url")
                k = data.get("SUPABASE_KEY") or data.get("supabase_key")
                if u and k:
                    return u.strip(), k.strip()
        except Exception as e:
            logger.error(f"Error reading supabase_config.json: {e}")

    return "", ""

class LicensingManager:
    def __init__(self, db=None):
        self.db = db
        self.refresh_credentials()
        
        if self.backend_type == "MOCK" and self.db:
            self._setup_local_mock_tables()

    def _setup_local_mock_tables(self):
        """Create mock tables in local SQLite for license testing without an online server."""
        try:
            self.db._conn.execute("""
                CREATE TABLE IF NOT EXISTS mock_license_keys (
                    key TEXT PRIMARY KEY,
                    client_name TEXT NOT NULL,
                    client_phone TEXT,
                    type TEXT CHECK (type IN ('TRIAL', 'MONTHLY', 'YEARLY')) DEFAULT 'MONTHLY',
                    status TEXT CHECK (status IN ('ACTIVE', 'EXPIRED', 'SUSPENDED')) DEFAULT 'ACTIVE',
                    created_at TEXT,
                    expires_at TEXT NOT NULL,
                    mac_address TEXT,
                    coupon_used TEXT
                )
            """)
            self.db._conn.execute("""
                CREATE TABLE IF NOT EXISTS mock_coupons (
                    code TEXT PRIMARY KEY,
                    discount_percent REAL DEFAULT 0,
                    trial_days INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    max_uses INTEGER DEFAULT 1,
                    uses_count INTEGER DEFAULT 0,
                    expires_at TEXT
                )
            """)
            # Insert default coupons in local sqlite mock
            self.db._conn.execute("""
                INSERT OR IGNORE INTO mock_coupons (code, discount_percent, trial_days, is_active, max_uses, uses_count, expires_at)
                VALUES 
                ('WELCOME50', 50.0, 0, 1, 100, 0, '2030-12-31 23:59:59'),
                ('FREE3TRIAL', 0.0, 3, 1, 1000, 0, '2030-12-31 23:59:59'),
                ('SUPER90', 90.0, 0, 1, 10, 0, '2030-12-31 23:59:59')
            """)
            self.db._conn.commit()
        except Exception as e:
            logger.error(f"Error creating local mock licensing tables: {e}")

    def refresh_credentials(self):
        """Re-read database and config file settings."""
        self.url, self.key = get_supabase_credentials(self.db)
        
        if self.db:
            self.backend_type = self.db.get_setting("license_backend", "MOCK")
            self.django_url = self.db.get_setting("django_api_url", "http://localhost:8000/api")
        else:
            self.backend_type = "MOCK"
            self.django_url = "http://localhost:8000/api"

        # Auto-configure to SUPABASE if credentials are set but it is still MOCK
        if self.url and self.key and self.backend_type == "MOCK":
            self.backend_type = "SUPABASE"
            if self.db:
                self.db.set_setting("license_backend", "SUPABASE")
                
        self.is_mock = (self.backend_type == "MOCK")

    def _get_supabase_headers(self) -> dict:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    # --- Unified API Helper methods ---
    
    def login_license(self, username: str, password: str, mac_addr: str) -> dict:
        self.refresh_credentials()
        username = username.strip()
        mac_addr = mac_addr.lower()

        # Account login always uses Django API regardless of backend_type
        try:
            api_url = f"{self.django_url}/login-license/"
            payload = {
                "username": username,
                "password": password,
                "mac_address": mac_addr
            }
            response = httpx.post(api_url, json=payload, timeout=10.0)
            if response.status_code == 200:
                return response.json()
            else:
                try:
                    err_msg = response.json().get("message", "فشل تسجيل الدخول والتحقق.")
                except Exception:
                    err_msg = f"فشل تسجيل الدخول والتحقق ({response.status_code})"
                return {"success": False, "message": err_msg}
        except Exception as e:
            logger.error(f"Error logging in with license: {e}")
            return {"success": False, "message": f"خطأ اتصال بخادم Django: {str(e)}"}

    def validate_license(self, license_key: str, mac_addr: str) -> dict:
        self.refresh_credentials()
        license_key = license_key.strip()
        mac_addr = mac_addr.lower()

        # 1. Local SQLite Mock Mode
        if self.backend_type == "MOCK":
            return self._validate_license_mock(license_key, mac_addr)

        # 2. Django Backend Mode
        if self.backend_type == "DJANGO":
            try:
                api_url = f"{self.django_url}/validate-license/"
                payload = {"key": license_key, "mac_address": mac_addr}
                response = httpx.post(api_url, json=payload, timeout=10.0)
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"success": False, "message": f"فشل التحقق من خادم Django ({response.status_code})"}
            except Exception as e:
                logger.error(f"Error checking Django license: {e}")
                return {"success": False, "message": f"خطأ اتصال بخادم Django: {str(e)}"}

        # 3. Supabase Backend Mode (Default)
        try:
            api_url = f"{self.url}/rest/v1/license_keys?key=eq.{license_key}&select=*"
            response = httpx.get(api_url, headers=self._get_supabase_headers(), timeout=10.0)
            
            if response.status_code != 200:
                return {"success": False, "message": f"خطأ في الاتصال بالخادم السحابي ({response.status_code})"}
            
            data = response.json()
            if not data:
                return {"success": False, "message": "كود التفعيل هذا غير موجود بقاعدة البيانات."}
            
            license_data = data[0]
            status = license_data.get("status", "ACTIVE")
            expires_at_str = license_data.get("expires_at")
            locked_mac = license_data.get("mac_address")

            if status == "SUSPENDED":
                return {"success": False, "message": "هذا الاشتراك معطل حالياً من قبل الإدارة."}
            
            expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
            now_utc = datetime.now(expires_at.tzinfo)
            if now_utc > expires_at:
                if status == "ACTIVE":
                    self.update_license_status(license_key, "EXPIRED")
                return {"success": False, "message": "عذراً، هذا الاشتراك منتهي الصلاحية."}

            if locked_mac:
                if locked_mac.lower() != mac_addr:
                    return {
                        "success": False, 
                        "message": f"هذا الاشتراك مفعل على جهاز آخر بـ MAC Address مختلف ({locked_mac})."
                    }
            else:
                bind_success = self.bind_mac_to_license(license_key, mac_addr)
                if not bind_success:
                    return {"success": False, "message": "فشل ربط كود الاشتراك بهذا الجهاز سحابياً."}
                license_data["mac_address"] = mac_addr

            return {
                "success": True, 
                "message": "تم التحقق بنجاح.", 
                "license": {
                    "key": license_key,
                    "client_name": license_data.get("client_name"),
                    "client_phone": license_data.get("client_phone"),
                    "type": license_data.get("type"),
                    "status": "ACTIVE",
                    "expires_at": expires_at.isoformat(),
                    "mac_address": mac_addr
                }
            }
        except Exception as e:
            logger.error(f"Error validating license online: {e}")
            return {"success": False, "message": f"فشل التحقق بسبب خطأ اتصال: {str(e)}"}

    def check_mac_has_trial(self, mac_addr: str) -> bool:
        self.refresh_credentials()
        mac_addr = mac_addr.lower()
        
        if self.backend_type == "MOCK":
            row = self.db._conn.execute(
                "SELECT COUNT(*) as count FROM mock_license_keys WHERE LOWER(mac_address) = ?",
                (mac_addr,)
            ).fetchone()
            return row["count"] > 0 if row else False

        if self.backend_type == "DJANGO":
            try:
                api_url = f"{self.django_url}/check-trial-mac/"
                payload = {"mac_address": mac_addr}
                response = httpx.post(api_url, json=payload, timeout=10.0)
                if response.status_code == 200:
                    return response.json().get("has_trial", False)
            except Exception as e:
                logger.error(f"Error checking Django trial MAC: {e}")
            return False

        try:
            api_url = f"{self.url}/rest/v1/license_keys?mac_address=eq.{mac_addr}&select=key"
            response = httpx.get(api_url, headers=self._get_supabase_headers(), timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                return len(data) > 0
        except Exception as e:
            logger.error(f"Error checking trial MAC address: {e}")
        return False

    def validate_coupon(self, code: str) -> dict:
        self.refresh_credentials()
        code = code.strip().upper()

        if self.backend_type == "MOCK":
            row = self.db._conn.execute(
                "SELECT * FROM mock_coupons WHERE code = ? AND is_active = 1", (code,)
            ).fetchone()
            if not row:
                return {"success": False, "message": "كوبون غير صالح أو غير نشط."}
            if row["uses_count"] >= row["max_uses"]:
                return {"success": False, "message": "انتهت صلاحية استخدام هذا الكوبون."}
            if row["expires_at"]:
                expiry = datetime.fromisoformat(row["expires_at"])
                if datetime.now() > expiry:
                    return {"success": False, "message": "انتهت مدة صلاحية هذا الكوبون."}
            return {
                "success": True,
                "discount_percent": row["discount_percent"],
                "trial_days": row["trial_days"]
            }

        if self.backend_type == "DJANGO":
            try:
                api_url = f"{self.django_url}/validate-coupon/"
                payload = {"code": code}
                response = httpx.post(api_url, json=payload, timeout=10.0)
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"success": False, "message": "كوبون خصم غير صحيح أو منتهي الصلاحية."}
            except Exception as e:
                logger.error(f"Error checking Django coupon: {e}")
                return {"success": False, "message": "خطأ اتصال بالخادم."}

        try:
            api_url = f"{self.url}/rest/v1/coupons?code=eq.{code}&is_active=eq.true&select=*"
            response = httpx.get(api_url, headers=self._get_supabase_headers(), timeout=10.0)
            if response.status_code != 200:
                return {"success": False, "message": "فشل التحقق من الكوبون."}
            
            data = response.json()
            if not data:
                return {"success": False, "message": "كوبون خصم غير صحيح أو منتهي الصلاحية."}
            
            coupon = data[0]
            uses_count = coupon.get("uses_count", 0)
            max_uses = coupon.get("max_uses", 1)
            if uses_count >= max_uses:
                return {"success": False, "message": "هذا الكوبون نفذت عدد مرات استخدامه المسموحة."}
            
            expires_at_str = coupon.get("expires_at")
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                now_utc = datetime.now(expires_at.tzinfo)
                if now_utc > expires_at:
                    return {"success": False, "message": "هذا الكوبون منتهي تاريخ الصلاحية."}
            
            return {
                "success": True,
                "discount_percent": coupon.get("discount_percent", 0.0),
                "trial_days": coupon.get("trial_days", 0)
            }
        except Exception as e:
            logger.error(f"Error checking coupon online: {e}")
            return {"success": False, "message": "خطأ اتصال أثناء التحقق من الكوبون."}

    def register_trial(self, client_name: str, client_phone: str, mac_addr: str) -> dict:
        self.refresh_credentials()
        mac_addr = mac_addr.lower()

        if self.check_mac_has_trial(mac_addr):
            return {"success": False, "message": "عذراً، هذا الجهاز مفعل عليه فترة تجريبية مسبقاً ولا يمكن تفعيل فترة تجريبية أخرى له."}

        trial_key = f"VC-TRIAL-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"
        trial_days = 3
        
        if self.backend_type == "MOCK":
            if self.db:
                try:
                    row = self.db._conn.execute("SELECT value FROM settings WHERE key = 'trial_duration_days'").fetchone()
                    if row:
                        trial_days = int(row["value"])
                except Exception:
                    pass
            expires_at = datetime.now() + timedelta(days=trial_days)
            try:
                self.db._conn.execute("""
                    INSERT INTO mock_license_keys (key, client_name, client_phone, type, status, created_at, expires_at, mac_address)
                    VALUES (?, ?, ?, 'TRIAL', 'ACTIVE', ?, ?, ?)
                """, (
                    trial_key, client_name, client_phone,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    expires_at.strftime("%Y-%m-%d %H:%M:%S"),
                    mac_addr
                ))
                self.db._conn.commit()
                return {
                    "success": True,
                    "key": trial_key,
                    "expires_at": expires_at.isoformat(),
                    "message": f"تم تفعيل الفترة التجريبية بنجاح لمدة {trial_days} أيام!"
                }
            except Exception as e:
                return {"success": False, "message": f"فشل تفعيل الفترة التجريبية محلياً: {e}"}

        if self.backend_type == "DJANGO":
            try:
                api_url = f"{self.django_url}/register-trial/"
                payload = {
                    "client_name": client_name,
                    "client_phone": client_phone,
                    "mac_address": mac_addr
                }
                response = httpx.post(api_url, json=payload, timeout=10.0)
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"success": False, "message": "فشل إنشاء الفترة التجريبية على خادم Django."}
            except Exception as e:
                logger.error(f"Error registering Django trial: {e}")
                return {"success": False, "message": f"خطأ اتصال بخادم Django: {str(e)}"}

        # Supabase Mode
        try:
            try:
                api_url = f"{self.url}/rest/v1/admin_settings?key=eq.trial_duration_days&select=value"
                resp = httpx.get(api_url, headers=self._get_supabase_headers(), timeout=5.0)
                if resp.status_code == 200 and resp.json():
                    trial_days = int(resp.json()[0]["value"])
            except Exception:
                pass

            expires_at = datetime.now() + timedelta(days=trial_days)
            payload = {
                "key": trial_key,
                "client_name": client_name,
                "client_phone": client_phone,
                "type": "TRIAL",
                "status": "ACTIVE",
                "expires_at": expires_at.isoformat(),
                "mac_address": mac_addr
            }
            response = httpx.post(f"{self.url}/rest/v1/license_keys", headers=self._get_supabase_headers(), json=payload, timeout=10.0)
            if response.status_code in (200, 201):
                return {
                    "success": True,
                    "key": trial_key,
                    "expires_at": expires_at.isoformat(),
                    "message": f"تم تفعيل الفترة التجريبية بنجاح لمدة {trial_days} أيام! مفتاحك: {trial_key}"
                }
            else:
                return {"success": False, "message": f"فشل تفعيل الفترة التجريبية على الخادم السحابي ({response.status_code})"}
        except Exception as e:
            return {"success": False, "message": f"خطأ اتصال أثناء تفعيل الفترة التجريبية: {str(e)}"}

    def bind_mac_to_license(self, license_key: str, mac_addr: str) -> bool:
        if self.backend_type == "MOCK":
            try:
                self.db._conn.execute("UPDATE mock_license_keys SET mac_address = ? WHERE key = ?", (mac_addr, license_key))
                self.db._conn.commit()
                return True
            except Exception:
                return False

        if self.backend_type == "DJANGO":
            try:
                api_url = f"{self.django_url}/bind-mac/"
                payload = {"key": license_key, "mac_address": mac_addr}
                response = httpx.post(api_url, json=payload, timeout=10.0)
                return response.status_code == 200 and response.json().get("success", False)
            except Exception:
                return False

        try:
            api_url = f"{self.url}/rest/v1/license_keys?key=eq.{license_key}"
            payload = {"mac_address": mac_addr}
            response = httpx.patch(api_url, headers=self._get_supabase_headers(), json=payload, timeout=10.0)
            return response.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Error binding MAC address online: {e}")
            return False

    def update_license_status(self, license_key: str, status: str) -> bool:
        if self.backend_type == "MOCK":
            try:
                self.db._conn.execute("UPDATE mock_license_keys SET status = ? WHERE key = ?", (status, license_key))
                self.db._conn.commit()
                return True
            except Exception:
                return False

        if self.backend_type == "DJANGO":
            try:
                api_url = f"{self.django_url}/update-license-status/"
                payload = {"key": license_key, "status": status}
                response = httpx.post(api_url, json=payload, timeout=10.0)
                return response.status_code == 200 and response.json().get("success", False)
            except Exception:
                return False

        try:
            api_url = f"{self.url}/rest/v1/license_keys?key=eq.{license_key}"
            payload = {"status": status}
            response = httpx.patch(api_url, headers=self._get_supabase_headers(), json=payload, timeout=10.0)
            return response.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Error updating license status: {e}")
            return False

    def increment_coupon_uses(self, code: str) -> bool:
        self.refresh_credentials()
        code = code.strip().upper()

        if self.backend_type == "MOCK":
            try:
                self.db._conn.execute("UPDATE mock_coupons SET uses_count = uses_count + 1 WHERE code = ?", (code,))
                self.db._conn.commit()
                return True
            except Exception:
                return False

        if self.backend_type == "DJANGO":
            try:
                api_url = f"{self.django_url}/use-coupon/"
                payload = {"code": code}
                response = httpx.post(api_url, json=payload, timeout=10.0)
                return response.status_code == 200 and response.json().get("success", False)
            except Exception:
                return False

        try:
            api_url = f"{self.url}/rest/v1/coupons?code=eq.{code}&select=uses_count"
            resp = httpx.get(api_url, headers=self._get_supabase_headers(), timeout=5.0)
            if resp.status_code == 200 and resp.json():
                curr = resp.json()[0].get("uses_count", 0)
                update_url = f"{self.url}/rest/v1/coupons?code=eq.{code}"
                payload = {"uses_count": curr + 1}
                httpx.patch(update_url, headers=self._get_supabase_headers(), json=payload, timeout=5.0)
                return True
        except Exception as e:
            logger.error(f"Error incrementing coupon count: {e}")
        return False

    # --- MOCK IMPLEMENTATION DETAILS ---

    def _validate_license_mock(self, license_key: str, mac_addr: str) -> dict:
        if not self.db:
            return {"success": False, "message": "قاعدة البيانات المحلية غير متوفرة."}
        try:
            row = self.db._conn.execute("SELECT * FROM mock_license_keys WHERE key = ?", (license_key,)).fetchone()
            if not row:
                return {"success": False, "message": "كود التفعيل هذا غير موجود في النظام التجريبي المحلي."}
            
            status = row["status"]
            expires_at_str = row["expires_at"]
            locked_mac = row["mac_address"]

            if status == "SUSPENDED":
                return {"success": False, "message": "هذا الاشتراك معطل حالياً من قبل الإدارة."}

            expires_at = datetime.fromisoformat(expires_at_str)
            if datetime.now() > expires_at:
                if status == "ACTIVE":
                    self.update_license_status(license_key, "EXPIRED")
                return {"success": False, "message": "عذراً، هذا الاشتراك منتهي الصلاحية."}

            if locked_mac:
                if locked_mac.lower() != mac_addr:
                    return {
                        "success": False, 
                        "message": f"هذا الاشتراك مفعل على جهاز آخر ({locked_mac})."
                    }
            else:
                self.bind_mac_to_license(license_key, mac_addr)
                locked_mac = mac_addr

            return {
                "success": True,
                "message": "تم التحقق بنجاح (النظام التجريبي المحلي).",
                "license": {
                    "key": license_key,
                    "client_name": row["client_name"],
                    "client_phone": row["client_phone"],
                    "type": row["type"],
                    "status": "ACTIVE",
                    "expires_at": expires_at.isoformat(),
                    "mac_address": locked_mac
                }
            }
        except Exception as e:
            return {"success": False, "message": f"خطأ في قراءة قاعدة البيانات المحلية: {e}"}

    def report_unclassified_sms(self, sender: str, raw_sms: str, received_at: str) -> bool:
        self.refresh_credentials()
        try:
            api_url = f"{self.django_url}/report-unclassified-sms/"
            mac = get_mac_address()
            license_key = ""
            if self.db:
                license_key = self.db.get_setting("license_key", "")
                
            payload = {
                "sender": sender,
                "raw_sms": raw_sms,
                "received_at": received_at,
                "mac_address": mac,
                "license_key": license_key
            }
            response = httpx.post(api_url, json=payload, timeout=10.0)
            return response.status_code == 200 and response.json().get("success", False)
        except Exception as e:
            logger.error(f"Error reporting unclassified SMS to Django: {e}")
            return False

