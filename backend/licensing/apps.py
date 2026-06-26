from django.apps import AppConfig


class LicensingConfig(AppConfig):
    name = 'licensing'

    def ready(self):
        import sys
        import os
        # Avoid seeding during migrations
        if 'migrate' not in sys.argv and 'makemigrations' not in sys.argv:
            try:
                # Add root directory to python path
                current_dir = os.path.dirname(os.path.abspath(__file__)) # licensing/
                backend_dir = os.path.dirname(current_dir) # backend/
                root_dir = os.path.dirname(backend_dir) # root/
                if root_dir not in sys.path:
                    sys.path.insert(0, root_dir)
                
                from .models import SMSPattern
                if not SMSPattern.objects.exists():
                    from mobile.parser.patterns import PATTERNS
                    import json
                    for p in PATTERNS:
                        regex_str = p["regex"].pattern
                        SMSPattern.objects.get_or_create(
                            pattern_id=p["id"],
                            defaults={
                                "type": p["type"].value,
                                "regex_pattern": regex_str,
                                "groups_json": json.dumps(p["groups"]),
                                "is_active": True
                            }
                        )
            except Exception:
                pass

