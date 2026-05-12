package com.vodacash;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.telephony.SmsMessage;
import android.util.Log;

public class SmsReceiver extends BroadcastReceiver {

    private static final String TAG = "VodaCash_SMS";

    // أرقام فودافون كاش الرسمية
    private static final String[] VODAFONE_SENDERS = {
        "VodafoneCash", "VodaCash", "Vodafone"
    };

    @Override
    public void onReceive(Context context, Intent intent) {
        if (!intent.getAction().equals("android.provider.Telephony.SMS_RECEIVED")) {
            return;
        }

        Bundle bundle = intent.getExtras();
        if (bundle == null) return;

        Object[] pdus = (Object[]) bundle.get("pdus");
        if (pdus == null) return;

        for (Object pdu : pdus) {
            SmsMessage sms = SmsMessage.createFromPdu((byte[]) pdu);
            String sender  = sms.getOriginatingAddress();
            String body    = sms.getMessageBody();

            Log.d(TAG, "SMS from: " + sender);
            Log.d(TAG, "Body: " + body);

            // فلترة — قبول رسائل فودافون كاش فقط
            if (isVodafoneCash(sender)) {
                Log.d(TAG, "✅ VodafoneCash SMS detected!");
                // إرسال الرسالة لـ Python عبر Intent
                sendToPython(context, sender, body);
            }
        }
    }

    private boolean isVodafoneCash(String sender) {
        if (sender == null) return false;
        for (String vs : VODAFONE_SENDERS) {
            if (sender.toLowerCase().contains(vs.toLowerCase())) {
                return true;
            }
        }
        return false;
    }

    private void sendToPython(Context context, String sender, String body) {
        Intent intent = new Intent("com.vodacash.SMS_RECEIVED");
        intent.putExtra("sender", sender);
        intent.putExtra("body", body);
        intent.putExtra("timestamp", System.currentTimeMillis());
        context.sendBroadcast(intent);
    }
}