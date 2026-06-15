package com.vodacash.smsmonitor;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.widget.Button;
import android.widget.RadioButton;
import android.widget.RadioGroup;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.google.android.material.textfield.TextInputEditText;
import com.vodacash.smsmonitor.service.SmsMonitorService;
import com.vodacash.smsmonitor.websocket.WebSocketManager;

public class SettingsActivity extends AppCompatActivity {

    public static final String PREFS_NAME = "VodaCashPrefs";
    public static final String KEY_HOST = "ws_host";
    public static final String KEY_PORT = "ws_port";
    public static final String KEY_GATEWAY_MODE = "gateway_mode";
    public static final String KEY_GATEWAY_URL = "gateway_url";
    public static final String KEY_GATEWAY_KEY = "gateway_key";
    
    private RadioGroup rgMode;
    private RadioButton rbWifi, rbUsb;
    private TextInputEditText etHost, etPort;
    private android.widget.CheckBox cbGatewayMode;
    private TextInputEditText etGatewayUrl, etGatewayKey;
    private Button btnSave;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_settings);

        rgMode = findViewById(R.id.rgMode);
        rbWifi = findViewById(R.id.rbWifi);
        rbUsb = findViewById(R.id.rbUsb);
        etHost = findViewById(R.id.etHost);
        etPort = findViewById(R.id.etPort);
        cbGatewayMode = findViewById(R.id.cbGatewayMode);
        etGatewayUrl = findViewById(R.id.etGatewayUrl);
        etGatewayKey = findViewById(R.id.etGatewayKey);
        btnSave = findViewById(R.id.btnSave);

        loadCurrentSettings();

        // التبديل بين الأوضاع
        rgMode.setOnCheckedChangeListener((group, checkedId) -> {
            if (checkedId == R.id.rbUsb) {
                etHost.setText("127.0.0.1"); // localhost عبر adb reverse
                etHost.setEnabled(false);
            } else {
                etHost.setEnabled(true);
                // لو كان 127.0.0.1، امسحه ليضع المستخدم الـ IP الخاص به
                if ("127.0.0.1".equals(etHost.getText().toString())) {
                    etHost.setText("");
                }
            }
        });

        btnSave.setOnClickListener(v -> saveSettings());
    }

    private void loadCurrentSettings() {
        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        String host = prefs.getString(KEY_HOST, "192.168.1.100");
        String port = prefs.getString(KEY_PORT, "8765");
        boolean gatewayMode = prefs.getBoolean(KEY_GATEWAY_MODE, false);
        String gatewayUrl = prefs.getString(KEY_GATEWAY_URL, "");
        String gatewayKey = prefs.getString(KEY_GATEWAY_KEY, "");

        etHost.setText(host);
        etPort.setText(port);
        cbGatewayMode.setChecked(gatewayMode);
        etGatewayUrl.setText(gatewayUrl);
        etGatewayKey.setText(gatewayKey);

        if ("127.0.0.1".equals(host)) {
            rbUsb.setChecked(true);
            etHost.setEnabled(false);
        } else {
            rbWifi.setChecked(true);
            etHost.setEnabled(true);
        }
    }

    private void saveSettings() {
        String host = etHost.getText().toString().trim();
        String portStr = etPort.getText().toString().trim();
        boolean gatewayMode = cbGatewayMode.isChecked();
        String gatewayUrl = etGatewayUrl.getText().toString().trim();
        String gatewayKey = etGatewayKey.getText().toString().trim();

        if (host.isEmpty() || portStr.isEmpty()) {
            Toast.makeText(this, "يرجى ملء جميع الحقول الخاصة باتصال الديسكتوب", Toast.LENGTH_SHORT).show();
            return;
        }

        if (gatewayMode && (gatewayUrl.isEmpty() || gatewayKey.isEmpty())) {
            Toast.makeText(this, "يرجى ملء حقول بوابة الدفع (الرابط والمفتاح) عند تفعيلها", Toast.LENGTH_SHORT).show();
            return;
        }

        // حفظ في SharedPreferences
        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        prefs.edit()
             .putString(KEY_HOST, host)
             .putString(KEY_PORT, portStr)
             .putBoolean(KEY_GATEWAY_MODE, gatewayMode)
             .putString(KEY_GATEWAY_URL, gatewayUrl)
             .putString(KEY_GATEWAY_KEY, gatewayKey)
             .apply();

        Toast.makeText(this, "تم الحفظ بنجاح", Toast.LENGTH_SHORT).show();

        // تحديث اتصال الـ WebSocket أو خدمات الخلفية إذا كانت الخدمة تعمل حالياً
        if (SmsMonitorService.isRunning()) {
            Intent serviceIntent = new Intent(this, SmsMonitorService.class);
            serviceIntent.setAction(SmsMonitorService.ACTION_RESTART_WS);
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                startForegroundService(serviceIntent);
            } else {
                startService(serviceIntent);
            }
        }
        finish(); // العودة للشاشة السابقة
    }
}
