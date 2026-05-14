package com.vodacash.smsmonitor.receiver;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.util.Log;

import com.vodacash.smsmonitor.service.SmsMonitorService;

/**
 * يتم تفعيله بعد إعادة تشغيل الجهاز لإعادة تشغيل خدمة المراقبة تلقائياً.
 */
public class BootReceiver extends BroadcastReceiver {

    private static final String TAG = "VodaCash_Boot";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) {
            Log.i(TAG, "📱 Device booted — restarting SmsMonitorService");

            Intent serviceIntent = new Intent(context, SmsMonitorService.class);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(serviceIntent);
            } else {
                context.startService(serviceIntent);
            }
        }
    }
}
