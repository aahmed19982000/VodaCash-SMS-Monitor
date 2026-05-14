package com.vodacash.smsmonitor.receiver;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.telephony.SmsMessage;
import android.util.Log;

import com.vodacash.smsmonitor.service.SmsMonitorService;
import com.vodacash.smsmonitor.util.SenderFilter;

import java.util.HashMap;
import java.util.Map;

/**
 * BroadcastReceiver الرئيسي لاستقبال رسائل SMS.
 *
 * يعمل على:
 * 1. استقبال كل رسالة SMS واردة للجهاز.
 * 2. تجميع أجزاء الرسالة الطويلة (Multi-part SMS) في رسالة واحدة.
 * 3. فلترة الرسائل وقبول فقط الأرقام الرسمية لفودافون كاش.
 * 4. تمرير الرسائل المقبولة إلى SmsMonitorService للمعالجة.
 */
public class SmsBroadcastReceiver extends BroadcastReceiver {

    private static final String TAG = "VodaCash_SMS";
    private static final String SMS_RECEIVED_ACTION = "android.provider.Telephony.SMS_RECEIVED";

    @Override
    public void onReceive(Context context, Intent intent) {
        // ── التحقق من نوع الإجراء ────────────────────────────────────────
        if (intent == null || !SMS_RECEIVED_ACTION.equals(intent.getAction())) {
            return;
        }

        Bundle bundle = intent.getExtras();
        if (bundle == null) return;

        Object[] pdus = (Object[]) bundle.get("pdus");
        if (pdus == null || pdus.length == 0) return;

        // ── تحديد التنسيق (3GPP vs 3GPP2) ───────────────────────────────
        String format = bundle.getString("format");

        // ── تجميع الرسائل متعددة الأجزاء ─────────────────────────────────
        // بعض رسائل فودافون كاش طويلة جداً وتأتي مقسمة لعدة أجزاء
        Map<String, StringBuilder> messageMap = new HashMap<>();
        Map<String, Long> timestampMap = new HashMap<>();

        for (Object pdu : pdus) {
            SmsMessage sms;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                sms = SmsMessage.createFromPdu((byte[]) pdu, format);
            } else {
                sms = SmsMessage.createFromPdu((byte[]) pdu);
            }

            if (sms == null) continue;

            String sender = sms.getOriginatingAddress();
            String body = sms.getMessageBody();
            long timestamp = sms.getTimestampMillis();

            if (sender == null || body == null) continue;

            // تجميع أجزاء الرسالة من نفس المرسل
            if (!messageMap.containsKey(sender)) {
                messageMap.put(sender, new StringBuilder());
                timestampMap.put(sender, timestamp);
            }
            messageMap.get(sender).append(body);
        }

        // ── معالجة كل رسالة مجمّعة ───────────────────────────────────────
        for (Map.Entry<String, StringBuilder> entry : messageMap.entrySet()) {
            String sender = entry.getKey();
            String fullBody = entry.getValue().toString();
            long timestamp = timestampMap.getOrDefault(sender, System.currentTimeMillis());

            Log.d(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
            Log.d(TAG, "📩 SMS from: " + sender);
            Log.d(TAG, "📄 Body length: " + fullBody.length() + " chars");

            // ── فلترة: قبول فقط أرقام فودافون كاش الرسمية ─────────────
            if (SenderFilter.isOfficialVodafoneCash(sender)) {
                Log.i(TAG, "✅ VodafoneCash SMS accepted!");
                forwardToService(context, sender, fullBody, timestamp);
            } else {
                Log.d(TAG, "⛔ Rejected — not an official VodafoneCash sender");
            }
        }
    }

    /**
     * تمرير الرسالة المقبولة إلى الخدمة الأمامية (Foreground Service)
     * لمعالجتها وإرسالها عبر WebSocket.
     */
    private void forwardToService(Context context, String sender, String body, long timestamp) {
        Intent serviceIntent = new Intent(context, SmsMonitorService.class);
        serviceIntent.setAction("com.vodacash.ACTION_NEW_SMS");
        serviceIntent.putExtra("sender", sender);
        serviceIntent.putExtra("body", body);
        serviceIntent.putExtra("timestamp", timestamp);

        // في Android 8+ يجب بدء الخدمة كـ Foreground
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            context.startForegroundService(serviceIntent);
        } else {
            context.startService(serviceIntent);
        }
    }
}
