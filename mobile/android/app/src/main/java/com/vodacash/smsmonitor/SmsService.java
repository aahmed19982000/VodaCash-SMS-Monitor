package com.vodacash.smsmonitor;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;
import android.util.Log;

import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;

/**
 * خدمة في الخلفية لاستقبال الـ SMS والاتصال ببايثون (Flet MethodChannel)
 */
public class SmsService extends Service {
    private static final String TAG = "SmsService";
    private static final String CHANNEL_ID = "SmsMonitorChannel";

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
        Notification notification = new NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle("VodaCash Monitor")
                .setContentText("المراقبة تعمل في الخلفية...")
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .build();
        
        startForeground(1, notification);
        Log.i(TAG, "SmsService started in foreground");
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && intent.hasExtra("sms_body")) {
            String smsBody = intent.getStringExtra("sms_body");
            String sender = intent.getStringExtra("sender");
            Log.i(TAG, "Received SMS from " + sender + " in Service");
            
            // هنا سيتم التواصل مع الـ MethodChannel الخاص بـ Flet (FlutterEngine)
            // لإرسال الرسالة إلى الـ Python
            sendToFletChannel(sender, smsBody);
        }
        return START_STICKY;
    }

    private void sendToFletChannel(String sender, String body) {
        // إذا كان التطبيق مبنياً بـ flet build apk فإنه يستخدم Flutter
        // يتم عادة تفعيل MethodChannel في MainActivity
        // أو إذا كان يعمل في الخلفية يتم تشغيل Headless Flutter Engine
        Log.i(TAG, "Sending to Flet: " + body);
        
        // إرسال Broadcast لاستقباله في الـ Activity الأساسية التي تمتلك الـ MethodChannel
        Intent broadcastIntent = new Intent("com.vodacash.smsmonitor.SMS_FORWARD");
        broadcastIntent.putExtra("sender", sender);
        broadcastIntent.putExtra("body", body);
        sendBroadcast(broadcastIntent);
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel serviceChannel = new NotificationChannel(
                    CHANNEL_ID,
                    "VodaCash Service Channel",
                    NotificationManager.IMPORTANCE_LOW
            );
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(serviceChannel);
            }
        }
    }
}
