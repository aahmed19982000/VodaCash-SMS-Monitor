# admin/admin_dashboard.py
import os
import sys
import json
import uuid
import datetime
import httpx
import sqlite3
import flet as ft

# Add parent directory to path so we can import from desktop
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from desktop.utils.licensing import get_supabase_credentials

class AdminBackend:
    def __init__(self):
        self.url, self.key = get_supabase_credentials()
        self.is_mock = not (self.url and self.key)
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "desktop", "db", "desktop_cache.db")
        
        if self.is_mock:
            self._setup_local_mock_tables()

    def _setup_local_mock_tables(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
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
            conn.execute("""
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
            conn.commit()
        except Exception as e:
            print(f"Error initializing local mock admin tables: {e}")
        finally:
            conn.close()

    def _get_headers(self):
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    # --- Licenses admin APIs ---

    def get_licenses(self):
        if self.is_mock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM mock_license_keys ORDER BY created_at DESC").fetchall()
            conn.close()
            return [dict(r) for r in rows]

        try:
            api_url = f"{self.url}/rest/v1/license_keys?select=*&order=created_at.desc"
            resp = httpx.get(api_url, headers=self._get_headers(), timeout=10.0)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"Error fetching licenses: {e}")
        return []

    def create_license(self, key, name, phone, type_val, expires_at, coupon_used=None):
        if self.is_mock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("""
                    INSERT INTO mock_license_keys (key, client_name, client_phone, type, status, created_at, expires_at, coupon_used)
                    VALUES (?, ?, ?, ?, 'ACTIVE', ?, ?, ?)
                """, (
                    key, name, phone, type_val,
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    expires_at.strftime("%Y-%m-%d %H:%M:%S"),
                    coupon_used
                ))
                conn.commit()
                return True
            except Exception as e:
                print(f"Error creating local mock license: {e}")
                return False
            finally:
                conn.close()

        try:
            payload = {
                "key": key,
                "client_name": name,
                "client_phone": phone,
                "type": type_val,
                "status": "ACTIVE",
                "expires_at": expires_at.isoformat(),
                "coupon_used": coupon_used
            }
            api_url = f"{self.url}/rest/v1/license_keys"
            resp = httpx.post(api_url, headers=self._get_headers(), json=payload, timeout=10.0)
            return resp.status_code in (200, 201)
        except Exception as e:
            print(f"Error creating license: {e}")
            return False

    def update_license(self, key, payload):
        if self.is_mock:
            conn = sqlite3.connect(self.db_path)
            try:
                set_clauses = []
                params = []
                for k, v in payload.items():
                    set_clauses.append(f"{k} = ?")
                    params.append(v)
                params.append(key)
                conn.execute(f"UPDATE mock_license_keys SET {', '.join(set_clauses)} WHERE key = ?", params)
                conn.commit()
                return True
            except Exception as e:
                print(f"Error updating local mock license: {e}")
                return False
            finally:
                conn.close()

        try:
            # Map iso dates
            if "expires_at" in payload and isinstance(payload["expires_at"], datetime.datetime):
                payload["expires_at"] = payload["expires_at"].isoformat()

            api_url = f"{self.url}/rest/v1/license_keys?key=eq.{key}"
            resp = httpx.patch(api_url, headers=self._get_headers(), json=payload, timeout=10.0)
            return resp.status_code in (200, 204)
        except Exception as e:
            print(f"Error updating license: {e}")
            return False

    def delete_license(self, key):
        if self.is_mock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("DELETE FROM mock_license_keys WHERE key = ?", (key,))
                conn.commit()
                return True
            except Exception:
                return False
            finally:
                conn.close()

        try:
            api_url = f"{self.url}/rest/v1/license_keys?key=eq.{key}"
            resp = httpx.delete(api_url, headers=self._get_headers(), timeout=10.0)
            return resp.status_code in (200, 204)
        except Exception as e:
            print(f"Error deleting license: {e}")
            return False

    # --- Coupon admin APIs ---

    def get_coupons(self):
        if self.is_mock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM mock_coupons").fetchall()
            conn.close()
            return [dict(r) for r in rows]

        try:
            api_url = f"{self.url}/rest/v1/coupons?select=*"
            resp = httpx.get(api_url, headers=self._get_headers(), timeout=10.0)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"Error fetching coupons: {e}")
        return []

    def create_coupon(self, code, discount, trial_days, max_uses, expires_at):
        code = code.upper().strip()
        if self.is_mock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("""
                    INSERT INTO mock_coupons (code, discount_percent, trial_days, is_active, max_uses, uses_count, expires_at)
                    VALUES (?, ?, ?, 1, ?, 0, ?)
                """, (
                    code, discount, trial_days, max_uses,
                    expires_at.strftime("%Y-%m-%d %H:%M:%S") if expires_at else None
                ))
                conn.commit()
                return True
            except Exception as e:
                print(f"Error creating local mock coupon: {e}")
                return False
            finally:
                conn.close()

        try:
            payload = {
                "code": code,
                "discount_percent": discount,
                "trial_days": trial_days,
                "is_active": True,
                "max_uses": max_uses,
                "uses_count": 0,
                "expires_at": expires_at.isoformat() if expires_at else None
            }
            api_url = f"{self.url}/rest/v1/coupons"
            resp = httpx.post(api_url, headers=self._get_headers(), json=payload, timeout=10.0)
            return resp.status_code in (200, 201)
        except Exception as e:
            print(f"Error creating coupon: {e}")
            return False

    def update_coupon(self, code, payload):
        if self.is_mock:
            conn = sqlite3.connect(self.db_path)
            try:
                set_clauses = []
                params = []
                for k, v in payload.items():
                    set_clauses.append(f"{k} = ?")
                    params.append(v)
                params.append(code)
                conn.execute(f"UPDATE mock_coupons SET {', '.join(set_clauses)} WHERE code = ?", params)
                conn.commit()
                return True
            except Exception:
                return False
            finally:
                conn.close()

        try:
            api_url = f"{self.url}/rest/v1/coupons?code=eq.{code}"
            resp = httpx.patch(api_url, headers=self._get_headers(), json=payload, timeout=10.0)
            return resp.status_code in (200, 204)
        except Exception as e:
            print(f"Error updating coupon: {e}")
            return False

    def delete_coupon(self, code):
        if self.is_mock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("DELETE FROM mock_coupons WHERE code = ?", (code,))
                conn.commit()
                return True
            except Exception:
                return False
            finally:
                conn.close()

        try:
            api_url = f"{self.url}/rest/v1/coupons?code=eq.{code}"
            resp = httpx.delete(api_url, headers=self._get_headers(), timeout=10.0)
            return resp.status_code in (200, 204)
        except Exception as e:
            print(f"Error deleting coupon: {e}")
            return False


def main(page: ft.Page):
    page.title = "VodaCash SMS Monitor — لوحة تحكم المسؤول (Admin Dashboard)"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#080C14"
    page.window.width = 1100
    page.window.height = 750
    page.padding = 20

    backend = AdminBackend()

    # Input style
    input_style = {
        "border_radius": 10,
        "bgcolor": "#0B0F19",
        "border_color": ft.Colors.WHITE24,
        "focused_border_color": ft.Colors.BLUE_ACCENT,
        "filled": True
    }

    # Stats cards
    stat_total_lic = ft.Text("0", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400)
    stat_active_lic = ft.Text("0", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400)
    stat_expired_lic = ft.Text("0", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400)
    stat_total_coupons = ft.Text("0", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_400)

    # 1. Dashboard Tab View
    dashboard_tab = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Icon(ft.Icons.SHIELD, color=ft.Colors.BLUE_400, size=32),
                    ft.Text("إحصائيات نظام التفعيل والاشتراكات / Subscription Metrics", size=20, weight=ft.FontWeight.BOLD),
                ],
                spacing=10
            ),
            ft.Divider(height=15, color=ft.Colors.WHITE10),
            ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Column([
                            ft.Text("إجمالي الأكواد / Total Keys", size=12, color=ft.Colors.WHITE54),
                            stat_total_lic
                        ], tight=True),
                        bgcolor="#0F172A", border=ft.Border.all(1, ft.Colors.WHITE10), border_radius=12, padding=20, expand=True
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("اشتراكات نشطة / Active", size=12, color=ft.Colors.WHITE54),
                            stat_active_lic
                        ], tight=True),
                        bgcolor="#0F172A", border=ft.Border.all(1, ft.Colors.WHITE10), border_radius=12, padding=20, expand=True
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("اشتراكات منتهية / Expired", size=12, color=ft.Colors.WHITE54),
                            stat_expired_lic
                        ], tight=True),
                        bgcolor="#0F172A", border=ft.Border.all(1, ft.Colors.WHITE10), border_radius=12, padding=20, expand=True
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("كوبونات الخصم / Coupons", size=12, color=ft.Colors.WHITE54),
                            stat_total_coupons
                        ], tight=True),
                        bgcolor="#0F172A", border=ft.Border.all(1, ft.Colors.WHITE10), border_radius=12, padding=20, expand=True
                    ),
                ],
                spacing=15
            ),
            ft.Container(height=20),
            ft.Container(
                content=ft.Column([
                    ft.Text("حالة الاتصال بقاعدة البيانات (Database Connection Status):", size=14, weight=ft.FontWeight.BOLD),
                    ft.Row([
                        ft.Icon(ft.Icons.CLOUD_DONE_OUTLINED if not backend.is_mock else ft.Icons.WARNING_AMBER, 
                                color=ft.Colors.GREEN_400 if not backend.is_mock else ft.Colors.AMBER_400),
                        ft.Text("متصل بقاعدة البيانات السحابية (Supabase)" if not backend.is_mock 
                                else "يعمل بالنظام التجريبي المحلي (Local Mock Mode) - احفظ إعدادات السحابة في التطبيق للتحويل")
                    ], spacing=10)
                ], spacing=8),
                bgcolor="#151C2C", border_radius=12, padding=20, border=ft.Border.all(1, ft.Colors.BLUE_400)
            )
        ],
        spacing=15
    )

    # 2. Generator Tab View
    client_name_input = ft.TextField(label="اسم العميل (Client Name)", **input_style)
    client_phone_input = ft.TextField(label="رقم الهاتف (Phone Number)", **input_style)
    lic_type_dropdown = ft.Dropdown(
        label="نوع الاشتراك (Subscription Type)",
        options=[
            ft.dropdown.Option("TRIAL", "فترة تجريبية (Trial - 3 Days)"),
            ft.dropdown.Option("MONTHLY", "شهري (Monthly - 30 Days)"),
            ft.dropdown.Option("YEARLY", "سنوي (Yearly - 365 Days)"),
        ],
        value="MONTHLY",
        **input_style
    )
    custom_days_input = ft.TextField(label="عدد الأيام مخصص (Custom Days) - اختياري لزيادة المدة", hint_text="أو اتركه فارغاً للقيمة الافتراضية", **input_style)
    coupon_used_input = ft.TextField(label="كوبون مستخدم للتخفيض (Coupon Code) - اختياري", **input_style)

    generated_key_text = ft.TextField(label="كود التفعيل المولد (Generated License Key)", read_only=True, width=400, **input_style)

    def generate_license_click(e):
        name = client_name_input.value.strip()
        phone = client_phone_input.value.strip()
        l_type = lic_type_dropdown.value
        
        if not name:
            page.snack_bar = ft.SnackBar(content=ft.Text("يرجى إدخال اسم العميل أولاً!"), bgcolor=ft.Colors.RED_700)
            page.snack_bar.open = True
            page.update()
            return

        # Generate unique key
        key = f"VC-{l_type}-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"
        
        # Calculate duration
        days = 30
        if l_type == "TRIAL":
            days = 3
        elif l_type == "YEARLY":
            days = 365
            
        if custom_days_input.value.strip():
            try:
                days = int(custom_days_input.value.strip())
            except ValueError:
                pass
                
        expires = datetime.datetime.now() + datetime.timedelta(days=days)
        coupon = coupon_used_input.value.strip().upper() or None

        success = backend.create_license(key, name, phone, l_type, expires, coupon)
        if success:
            generated_key_text.value = key
            page.snack_bar = ft.SnackBar(content=ft.Text("✅ تم إنشاء وتخزين كود الاشتراك بنجاح!"), bgcolor=ft.Colors.GREEN_800)
            # Reset fields
            client_name_input.value = ""
            client_phone_input.value = ""
            custom_days_input.value = ""
            coupon_used_input.value = ""
            refresh_all_data()
        else:
            page.snack_bar = ft.SnackBar(content=ft.Text("❌ فشل تفعيل وإنشاء الكود سحابياً."), bgcolor=ft.Colors.RED_700)
            
        page.snack_bar.open = True
        page.update()

    generator_tab = ft.Column(
        controls=[
            ft.Row([
                ft.Icon(ft.Icons.VPN_KEY, color=ft.Colors.BLUE_400, size=32),
                ft.Text("توليد أكواد التفعيل الجديدة / Generate License Keys", size=20, weight=ft.FontWeight.BOLD),
            ], spacing=10),
            ft.Divider(height=15, color=ft.Colors.WHITE10),
            ft.Column(
                controls=[
                    client_name_input,
                    client_phone_input,
                    lic_type_dropdown,
                    custom_days_input,
                    coupon_used_input,
                    ft.Container(height=10),
                    ft.ElevatedButton(
                        "إنشاء وحفظ الكود / Generate Key",
                        icon=ft.Icons.ADD_BOX,
                        bgcolor=ft.Colors.BLUE_700,
                        color=ft.Colors.WHITE,
                        on_click=generate_license_click,
                        width=300,
                        height=45,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
                    ),
                    ft.Divider(height=20, color=ft.Colors.WHITE10),
                    ft.Row([
                        generated_key_text,
                        ft.IconButton(
                            icon=ft.Icons.CONTENT_COPY,
                            tooltip="نسخ الكود",
                            on_click=lambda e: page.set_clipboard(generated_key_text.value)
                        )
                    ])
                ],
                spacing=12
            )
        ],
        spacing=15,
        scroll=ft.ScrollMode.AUTO
    )

    # 3. Subscriptions Tab View
    clients_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("العميل / Client")),
            ft.DataColumn(ft.Text("كود التفعيل / Key")),
            ft.DataColumn(ft.Text("النوع / Type")),
            ft.DataColumn(ft.Text("تاريخ الانتهاء / Expiry")),
            ft.DataColumn(ft.Text("معرف الجهاز / MAC")),
            ft.DataColumn(ft.Text("الحالة / Status")),
            ft.DataColumn(ft.Text("إجراءات / Actions")),
        ],
        rows=[]
    )

    def refresh_licenses_table(licenses):
        clients_table.rows.clear()
        for lic in licenses:
            key = lic["key"]
            mac = lic.get("mac_address") or "—"
            status = lic.get("status", "ACTIVE")
            expires_str = lic["expires_at"][:19].replace("T", " ")
            
            # Action buttons
            clear_mac_btn = ft.IconButton(
                icon=ft.Icons.PHONELINK_ERASE,
                tooltip="إلغاء قفل الجهاز (Reset MAC)",
                on_click=lambda e, k=key: reset_mac_lock(k),
                icon_color=ft.Colors.BLUE_300,
                disabled=(mac == "—")
            )
            
            toggle_status_btn = ft.IconButton(
                icon=ft.Icons.PLAY_ARROW if status == "SUSPENDED" else ft.Icons.PAUSE,
                tooltip="تفعيل الاشتراك" if status == "SUSPENDED" else "تعطيل مؤقت",
                on_click=lambda e, k=key, s=status: toggle_license_status(k, s),
                icon_color=ft.Colors.GREEN_400 if status == "SUSPENDED" else ft.Colors.ORANGE_400
            )

            extend_expiry_btn = ft.IconButton(
                icon=ft.Icons.MORE_TIME,
                tooltip="تمديد الاشتراك (30 يوم)",
                on_click=lambda e, k=key, exp=lic["expires_at"]: extend_license_expiry(k, exp),
                icon_color=ft.Colors.AMBER_400
            )

            delete_btn = ft.IconButton(
                icon=ft.Icons.DELETE_FOREVER,
                tooltip="حذف الكود نهائياً",
                on_click=lambda e, k=key: delete_license_key(k),
                icon_color=ft.Colors.RED_400
            )

            actions_row = ft.Row([clear_mac_btn, toggle_status_btn, extend_expiry_btn, delete_btn], spacing=5, tight=True)

            # Colors for badge
            type_color = ft.Colors.AMBER_700 if lic["type"] == "TRIAL" else (ft.Colors.BLUE_700 if lic["type"] == "MONTHLY" else ft.Colors.GREEN_700)
            status_color = ft.Colors.GREEN_600 if status == "ACTIVE" else (ft.Colors.RED_600 if status == "EXPIRED" else ft.Colors.ORANGE_600)

            clients_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Column([
                            ft.Text(lic["client_name"], weight=ft.FontWeight.BOLD),
                            ft.Text(lic.get("client_phone") or "—", size=11, color=ft.Colors.WHITE54)
                        ], alignment=ft.MainAxisAlignment.CENTER)),
                        ft.DataCell(ft.Text(key, selectable=True, size=12)),
                        ft.DataCell(ft.Container(content=ft.Text(lic["type"], size=10, weight=ft.FontWeight.BOLD), bgcolor=type_color, padding=5, border_radius=5)),
                        ft.DataCell(ft.Text(expires_str, size=11)),
                        ft.DataCell(ft.Text(mac, size=10, selectable=True)),
                        ft.DataCell(ft.Container(content=ft.Text(status, size=10, weight=ft.FontWeight.BOLD), bgcolor=status_color, padding=5, border_radius=5)),
                        ft.DataCell(actions_row),
                    ]
                )
            )
        page.update()

    def reset_mac_lock(key):
        if backend.update_license(key, {"mac_address": None}):
            page.snack_bar = ft.SnackBar(content=ft.Text("✅ تم إلغاء قفل الجهاز بنجاح! يمكن للعميل تفعيله على كمبيوتر آخر."), bgcolor=ft.Colors.GREEN_800)
            refresh_all_data()
        else:
            page.snack_bar = ft.SnackBar(content=ft.Text("❌ فشل إلغاء قفل الجهاز."), bgcolor=ft.Colors.RED_700)
        page.snack_bar.open = True
        page.update()

    def toggle_license_status(key, current_status):
        new_status = "ACTIVE" if current_status == "SUSPENDED" else "SUSPENDED"
        if backend.update_license(key, {"status": new_status}):
            page.snack_bar = ft.SnackBar(content=ft.Text(f"✅ تم تغيير حالة الاشتراك إلى: {new_status}"), bgcolor=ft.Colors.GREEN_800)
            refresh_all_data()
        else:
            page.snack_bar = ft.SnackBar(content=ft.Text("❌ فشل تعديل الحالة."), bgcolor=ft.Colors.RED_700)
        page.snack_bar.open = True
        page.update()

    def extend_license_expiry(key, current_expiry_str):
        try:
            current_expiry = datetime.datetime.fromisoformat(current_expiry_str.replace("Z", "+00:00"))
            # If already expired, extend from today, else extend from current expiry
            base_date = max(current_expiry.replace(tzinfo=None), datetime.datetime.now())
            new_expiry = base_date + datetime.timedelta(days=30)
            
            if backend.update_license(key, {"expires_at": new_expiry, "status": "ACTIVE"}):
                page.snack_bar = ft.SnackBar(content=ft.Text("✅ تم تمديد الاشتراك بمقدار 30 يوماً بنجاح!"), bgcolor=ft.Colors.GREEN_800)
                refresh_all_data()
            else:
                page.snack_bar = ft.SnackBar(content=ft.Text("❌ فشل تمديد الاشتراك."), bgcolor=ft.Colors.RED_700)
        except Exception as ex:
            page.snack_bar = ft.SnackBar(content=ft.Text(f"خطأ: {ex}"), bgcolor=ft.Colors.RED_700)
            
        page.snack_bar.open = True
        page.update()

    def delete_license_key(key):
        if backend.delete_license(key):
            page.snack_bar = ft.SnackBar(content=ft.Text("🗑 تم حذف كود الاشتراك نهائياً."), bgcolor=ft.Colors.BLUE_GREY_800)
            refresh_all_data()
        else:
            page.snack_bar = ft.SnackBar(content=ft.Text("❌ فشل الحذف."), bgcolor=ft.Colors.RED_700)
        page.snack_bar.open = True
        page.update()

    subscriptions_tab = ft.Column(
        controls=[
            ft.Row([
                ft.Icon(ft.Icons.PEOPLE, color=ft.Colors.BLUE_400, size=32),
                ft.Text("إدارة المشتركين والعملاء / Client Subscriptions", size=20, weight=ft.FontWeight.BOLD),
                ft.IconButton(ft.Icons.REFRESH, on_click=lambda e: refresh_all_data(), tooltip="تحديث الجدول")
            ], spacing=10),
            ft.Divider(height=15, color=ft.Colors.WHITE10),
            ft.Column(
                controls=[clients_table],
                scroll=ft.ScrollMode.AUTO,
                expand=True
            )

        ],
        spacing=15,
        expand=True
    )

    # 4. Coupons Tab View
    coupon_code_input = ft.TextField(label="كود الكوبون (Coupon Code)", hint_text="مثال: SAVE50", **input_style)
    coupon_discount_input = ft.TextField(label="نسبة الخصم % (Discount Percent)", value="0", **input_style)
    coupon_trial_input = ft.TextField(label="أيام تجريبية إضافية (Trial Days)", value="0", **input_style)
    coupon_uses_input = ft.TextField(label="الحد الأقصى للاستخدام (Max Uses)", value="100", **input_style)

    coupons_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("الكود / Code")),
            ft.DataColumn(ft.Text("نسبة الخصم / Discount")),
            ft.DataColumn(ft.Text("أيام التجربة / Trial Days")),
            ft.DataColumn(ft.Text("الاستخدام / Uses (Current/Max)")),
            ft.DataColumn(ft.Text("الحالة / Active")),
            ft.DataColumn(ft.Text("إجراءات / Actions")),
        ],
        rows=[]
    )

    def create_coupon_click(e):
        code = coupon_code_input.value.strip().upper()
        try:
            discount = float(coupon_discount_input.value.strip())
            trial_days = int(coupon_trial_input.value.strip())
            max_uses = int(coupon_uses_input.value.strip())
        except ValueError:
            page.snack_bar = ft.SnackBar(content=ft.Text("يرجى إدخال قيم رقمية صالحة!"), bgcolor=ft.Colors.RED_700)
            page.snack_bar.open = True
            page.update()
            return

        if not code:
            page.snack_bar = ft.SnackBar(content=ft.Text("يرجى إدخال كود الكوبون!"), bgcolor=ft.Colors.RED_700)
            page.snack_bar.open = True
            page.update()
            return

        # Expire in 1 year
        expires = datetime.datetime.now() + datetime.timedelta(days=365)

        success = backend.create_coupon(code, discount, trial_days, max_uses, expires)
        if success:
            page.snack_bar = ft.SnackBar(content=ft.Text("✅ تم إنشاء كوبون الخصم بنجاح!"), bgcolor=ft.Colors.GREEN_800)
            coupon_code_input.value = ""
            coupon_discount_input.value = "0"
            coupon_trial_input.value = "0"
            coupon_uses_input.value = "100"
            refresh_all_data()
        else:
            page.snack_bar = ft.SnackBar(content=ft.Text("❌ فشل إنشاء الكوبون سحابياً."), bgcolor=ft.Colors.RED_700)
        page.snack_bar.open = True
        page.update()

    def refresh_coupons_table(coupons):
        coupons_table.rows.clear()
        for cp in coupons:
            code = cp["code"]
            active = cp.get("is_active", True)
            active_bool = (active == 1 or active is True)
            
            toggle_btn = ft.IconButton(
                icon=ft.Icons.CHECK_CIRCLE if active_bool else ft.Icons.REMOVE_CIRCLE_OUTLINED,
                tooltip="تعطيل الكوبون" if active_bool else "تفعيل الكوبون",
                on_click=lambda e, c=code, a=active_bool: toggle_coupon_status(c, a),
                icon_color=ft.Colors.GREEN_400 if active_bool else ft.Colors.RED_400
            )

            delete_btn = ft.IconButton(
                icon=ft.Icons.DELETE,
                tooltip="حذف الكوبون",
                on_click=lambda e, c=code: delete_coupon_code(c),
                icon_color=ft.Colors.RED_400
            )

            actions = ft.Row([toggle_btn, delete_btn], spacing=5, tight=True)

            coupons_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(code, weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(f"{cp['discount_percent']}%")),
                        ft.DataCell(ft.Text(f"{cp.get('trial_days', 0)} أيام")),
                        ft.DataCell(ft.Text(f"{cp.get('uses_count', 0)} / {cp['max_uses']}")),
                        ft.DataCell(ft.Container(
                            content=ft.Text("ACTIVE" if active_bool else "INACTIVE", size=10, weight=ft.FontWeight.BOLD),
                            bgcolor=ft.Colors.GREEN_800 if active_bool else ft.Colors.RED_800,
                            padding=5,
                            border_radius=5
                        )),
                        ft.DataCell(actions),
                    ]
                )
            )
        page.update()

    def toggle_coupon_status(code, is_active):
        if backend.update_coupon(code, {"is_active": not is_active}):
            page.snack_bar = ft.SnackBar(content=ft.Text("✅ تم تحديث حالة الكوبون بنجاح!"), bgcolor=ft.Colors.GREEN_800)
            refresh_all_data()
        else:
            page.snack_bar = ft.SnackBar(content=ft.Text("❌ فشل تحديث حالة الكوبون."), bgcolor=ft.Colors.RED_700)
        page.snack_bar.open = True
        page.update()

    def delete_coupon_code(code):
        if backend.delete_coupon(code):
            page.snack_bar = ft.SnackBar(content=ft.Text("🗑 تم حذف الكوبون بنجاح!"), bgcolor=ft.Colors.BLUE_GREY_800)
            refresh_all_data()
        else:
            page.snack_bar = ft.SnackBar(content=ft.Text("❌ فشل حذف الكوبون."), bgcolor=ft.Colors.RED_700)
        page.snack_bar.open = True
        page.update()

    coupons_tab = ft.Column(
        controls=[
            ft.Row([
                ft.Icon(ft.Icons.CARD_GIFTCARD, color=ft.Colors.BLUE_400, size=32),
                ft.Text("إدارة الكوبونات وصم الخصومات / Coupon Management", size=20, weight=ft.FontWeight.BOLD),
            ], spacing=10),
            ft.Divider(height=15, color=ft.Colors.WHITE10),
            ft.Row(
                controls=[
                    ft.Column([
                        ft.Text("إنشاء كوبون جديد (Create Coupon):", size=14, weight=ft.FontWeight.BOLD),
                        coupon_code_input,
                        coupon_discount_input,
                        coupon_trial_input,
                        coupon_uses_input,
                        ft.ElevatedButton(
                            "إنشاء الكوبون / Create Coupon",
                            icon=ft.Icons.ADD,
                            bgcolor=ft.Colors.GREEN_700,
                            color=ft.Colors.WHITE,
                            on_click=create_coupon_click,
                            width=220,
                            height=40,
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
                        )
                    ], spacing=10, width=280),
                    ft.VerticalDivider(width=20, color=ft.Colors.WHITE10),
                    ft.Column([
                        ft.Text("قائمة الكوبونات النشطة (Active Coupons List):", size=14, weight=ft.FontWeight.BOLD),
                        coupons_table
                    ], spacing=10, expand=True)
                ],
                spacing=20,
                expand=True
            )
        ],
        spacing=15,
        scroll=ft.ScrollMode.AUTO,
        expand=True
    )

    # Tab views container
    tab_content_container = ft.Container(
        content=dashboard_tab,
        expand=True,
        padding=15
    )

    tab_buttons = []
    tab_names = [
        "لوحة الإحصائيات / Dashboard",
        "توليد المفاتيح / Key Generator",
        "إدارة المشتركين / Subscriptions",
        "الكوبونات وصم / Coupons"
    ]
    tab_icons = [
        ft.Icons.SHIELD,
        ft.Icons.VPN_KEY,
        ft.Icons.PEOPLE,
        ft.Icons.CARD_GIFTCARD
    ]

    def set_tab(idx):
        if idx == 0:
            tab_content_container.content = dashboard_tab
        elif idx == 1:
            tab_content_container.content = generator_tab
        elif idx == 2:
            tab_content_container.content = subscriptions_tab
        elif idx == 3:
            tab_content_container.content = coupons_tab
            
        # Update tab buttons styling
        for i, btn in enumerate(tab_buttons):
            if i == idx:
                btn.bgcolor = "#1E293B"
                btn.border = ft.Border(bottom=ft.BorderSide(3, ft.Colors.BLUE_400))
                btn.content.controls[0].color = ft.Colors.BLUE_400
                btn.content.controls[1].color = ft.Colors.WHITE
                btn.content.controls[1].weight = ft.FontWeight.BOLD
            else:
                btn.bgcolor = ft.Colors.TRANSPARENT
                btn.border = None
                btn.content.controls[0].color = ft.Colors.WHITE54
                btn.content.controls[1].color = ft.Colors.WHITE54
                btn.content.controls[1].weight = ft.FontWeight.NORMAL
        page.update()

    # Build custom buttons
    for i in range(4):
        def make_click(idx):
            return lambda e: set_tab(idx)
            
        btn = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(tab_icons[i], size=18, color=ft.Colors.WHITE54),
                    ft.Text(tab_names[i], size=13, color=ft.Colors.WHITE54)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8
            ),
            padding=ft.Padding(15, 10, 15, 10),
            border_radius=ft.BorderRadius.only(top_left=8, top_right=8),
            on_click=make_click(i),
            alignment=ft.Alignment.CENTER
        )
        tab_buttons.append(btn)

    tab_header = ft.Container(
        content=ft.Row(tab_buttons, spacing=5, alignment=ft.MainAxisAlignment.START),
        border=ft.Border(bottom=ft.BorderSide(1, ft.Colors.WHITE10)),
        margin=ft.Margin(0, 0, 0, 15)
    )

    # Set initial active tab styling
    tab_buttons[0].bgcolor = "#1E293B"
    tab_buttons[0].border = ft.Border(bottom=ft.BorderSide(3, ft.Colors.BLUE_400))
    tab_buttons[0].content.controls[0].color = ft.Colors.BLUE_400
    tab_buttons[0].content.controls[1].color = ft.Colors.WHITE
    tab_buttons[0].content.controls[1].weight = ft.FontWeight.BOLD

    def refresh_all_data():
        # Load and refresh numbers
        licenses = backend.get_licenses()
        coupons = backend.get_coupons()
        
        total_keys = len(licenses)
        active = sum(1 for l in licenses if l.get("status") == "ACTIVE")
        expired = sum(1 for l in licenses if l.get("status") == "EXPIRED")
        
        # Update metrics
        stat_total_lic.value = str(total_keys)
        stat_active_lic.value = str(active)
        stat_expired_lic.value = str(expired)
        stat_total_coupons.value = str(len(coupons))
        
        # Update tables
        refresh_licenses_table(licenses)
        refresh_coupons_table(coupons)
        
        page.update()

    page.add(
        ft.Column(
            [
                tab_header,
                tab_content_container
            ],
            expand=True
        )
    )
    refresh_all_data()



if __name__ == "__main__":
    ft.app(target=main)
