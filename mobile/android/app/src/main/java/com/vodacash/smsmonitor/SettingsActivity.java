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
    
    private RadioGroup rgMode;
    private RadioButton rbWifi, rbUsb;
    private TextInputEditText etHost, etPort;
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

        etHost.setText(host);
        etPort.setText(port);

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

        if (host.isEmpty() || portStr.isEmpty()) {
            Toast.makeText(this, "يرجى ملء جميع الحقول", Toast.LENGTH_SHORT).show();
            return;
        }

        // حفظ في SharedPreferences
        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        prefs.edit()
             .putString(KEY_HOST, host)
             .putString(KEY_PORT, portStr)
             .apply();

        Toast.makeText(this, "تم الحفظ بنجاح", Toast.LENGTH_SHORT).show();

        // تحديث اتصال الـ WebSocket إذا كانت الخدمة تعمل حالياً
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
