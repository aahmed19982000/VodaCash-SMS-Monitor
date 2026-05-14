package com.vodacash.smsmonitor;

import android.Manifest;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.vodacash.smsmonitor.service.SmsMonitorService;

/**
 * النشاط الرئيسي — يطلب أذونات SMS عند بدء التطبيق
 * ثم يُشغّل الخدمة الأمامية.
 */
public class MainActivity extends AppCompatActivity {

    private static final int SMS_PERMISSION_CODE = 100;
    private static final int NOTIFICATION_PERMISSION_CODE = 101;

    // الأذونات المطلوبة لعمل التطبيق
    private static final String[] REQUIRED_PERMISSIONS = {
        Manifest.permission.RECEIVE_SMS,
        Manifest.permission.READ_SMS,
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        // زر الإعدادات
        findViewById(R.id.btnSettings).setOnClickListener(v -> {
            android.content.Intent intent = new android.content.Intent(this, SettingsActivity.class);
            startActivity(intent);
        });

        checkAndRequestPermissions();
    }

    // ═════════════════════════════════════════════════════════════════════
    // طلب الأذونات (Runtime Permissions)
    // ═════════════════════════════════════════════════════════════════════

    private void checkAndRequestPermissions() {
        // 1. التحقق من أذونات SMS
        if (!hasAllPermissions(REQUIRED_PERMISSIONS)) {
            ActivityCompat.requestPermissions(this, REQUIRED_PERMISSIONS, SMS_PERMISSION_CODE);
            return;
        }

        // 2. التحقق من إذن الإشعارات (Android 13+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this,
                    Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this,
                    new String[]{Manifest.permission.POST_NOTIFICATIONS},
                    NOTIFICATION_PERMISSION_CODE);
                return;
            }
        }

        // 3. كل الأذونات ممنوحة → تشغيل الخدمة
        onAllPermissionsGranted();
    }

    private boolean hasAllPermissions(String[] permissions) {
        for (String perm : permissions) {
            if (ContextCompat.checkSelfPermission(this, perm) != PackageManager.PERMISSION_GRANTED) {
                return false;
            }
        }
        return true;
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions,
                                           @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);

        switch (requestCode) {
            case SMS_PERMISSION_CODE:
                if (allGranted(grantResults)) {
                    // SMS أذونات ممنوحة، نتحقق من الإشعارات
                    checkAndRequestPermissions();
                } else {
                    Toast.makeText(this,
                        "⚠️ التطبيق يحتاج إذن قراءة الرسائل ليعمل",
                        Toast.LENGTH_LONG).show();
                }
                break;

            case NOTIFICATION_PERMISSION_CODE:
                // حتى لو رُفض إذن الإشعارات، الخدمة تعمل
                onAllPermissionsGranted();
                break;
        }
    }

    private boolean allGranted(int[] results) {
        for (int r : results) {
            if (r != PackageManager.PERMISSION_GRANTED) return false;
        }
        return results.length > 0;
    }

    // ═════════════════════════════════════════════════════════════════════
    // بعد منح الأذونات
    // ═════════════════════════════════════════════════════════════════════

    private void onAllPermissionsGranted() {
        requestBatteryOptimizationWhitelist();
        Toast.makeText(this, "✅ تم تفعيل مراقبة فودافون كاش", Toast.LENGTH_SHORT).show();
        SmsMonitorService.start(this);
    }

    /**
     * طلب استثناء التطبيق من تحسين البطارية (Doze Mode)
     * حتى لا يتم إيقاف الخدمة أثناء نوم الجهاز.
     */
    private void requestBatteryOptimizationWhitelist() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            android.os.PowerManager pm = (android.os.PowerManager)
                getSystemService(Context.POWER_SERVICE);
            if (pm != null && !pm.isIgnoringBatteryOptimizations(getPackageName())) {
                Intent intent = new Intent(
                    android.provider.Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS
                );
                intent.setData(android.net.Uri.parse("package:" + getPackageName()));
                startActivity(intent);
            }
        }
    }
}
