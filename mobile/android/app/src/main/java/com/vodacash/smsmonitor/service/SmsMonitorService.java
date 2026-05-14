package com.vodacash.smsmonitor.service;

import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.IBinder;
import android.os.Looper;
import android.os.PowerManager;
import android.os.SystemClock;
import android.util.Log;

import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;

import com.vodacash.smsmonitor.MainActivity;
import com.vodacash.smsmonitor.websocket.WebSocketManager;

import org.json.JSONObject;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.LinkedList;
import java.util.Locale;
import java.util.Queue;

/**
 * الخدمة الأمامية الرئيسية (Foreground Service) لمراقبة فودافون كاش.
 *
 * المسؤوليات:
 * ─────────────────────────────────────────────────────────────
 * 1. البقاء نشطة في الخلفية مع إشعار دائم
 * 2. إدارة اتصال WebSocket مع سطح المكتب
 * 3. معالجة الرسائل الواردة عبر Python Parser (Chaquopy)
 * 4. تخزين الرسائل مؤقتاً عند انقطاع الاتصال (Offline Queue)
 * 5. إعادة التشغيل التلقائي عند التوقف (START_STICKY + AlarmManager)
 * 6. إدارة WakeLock لمنع نوم المعالج
 * 7. إرسال Heartbeat دوري للتأكد من سلامة الاتصال
 */
public class SmsMonitorService extends Service {

    private static final String TAG = "VodaCash_Service";

    // ── الثوابت ──────────────────────────────────────────────────────────
    private static final String CHANNEL_ID          = "vodacash_monitor";
    private static final String CHANNEL_ALERT_ID    = "vodacash_alerts";
    private static final int    NOTIFICATION_ID      = 1001;
    private static final int    RESTART_ALARM_ID     = 2001;
    private static final long   HEARTBEAT_INTERVAL   = 10_000L;  // 10 ثوانٍ
    private static final long   RECONNECT_DELAY      = 5_000L;   // 5 ثوانٍ
    private static final int    MAX_QUEUE_SIZE        = 200;
    private static final String PREFS_NAME           = "vodacash_service";

    // ── الإجراءات (Actions) ──────────────────────────────────────────────
    public static final String ACTION_NEW_SMS    = "com.vodacash.ACTION_NEW_SMS";
    public static final String ACTION_START      = "com.vodacash.ACTION_START";
    public static final String ACTION_STOP       = "com.vodacash.ACTION_STOP";
    public static final String ACTION_RESTART_WS = "com.vodacash.ACTION_RESTART_WS";

    // ── الحالة ───────────────────────────────────────────────────────────
    private enum ServiceState { STARTING, RUNNING, STOPPING }
    private ServiceState currentState = ServiceState.STARTING;

    // ── المكونات ─────────────────────────────────────────────────────────
    private PowerManager.WakeLock wakeLock;
    private HandlerThread workerThread;
    private Handler workerHandler;
    private Handler mainHandler;
    private WebSocketManager wsManager;
    private NotificationManager notificationManager;
    private SharedPreferences prefs;

    // ── Offline Queue (تخزين مؤقت عند انقطاع الاتصال) ────────────────────
    private final Queue<String> offlineQueue = new LinkedList<>();

    // ── الإحصائيات ───────────────────────────────────────────────────────
    private int processedCount  = 0;
    private int sentCount       = 0;
    private int queuedCount     = 0;
    private long startTimeMillis;

    // ── Heartbeat ────────────────────────────────────────────────────────
    private final Runnable heartbeatRunnable = new Runnable() {
        @Override
        public void run() {
            if (currentState != ServiceState.RUNNING) return;

            if (wsManager != null && wsManager.isConnected()) {
                wsManager.sendHeartbeat();
            } else if (wsManager != null) {
                Log.w(TAG, "💔 WebSocket disconnected — attempting reconnect");
                wsManager.reconnect();
            }

            workerHandler.postDelayed(this, HEARTBEAT_INTERVAL);
        }
    };

    // ═════════════════════════════════════════════════════════════════════
    // دورة حياة الخدمة (Service Lifecycle)
    // ═════════════════════════════════════════════════════════════════════

    @Override
    public void onCreate() {
        super.onCreate();
        Log.i(TAG, "🚀 ════════════════════════════════════════");
        Log.i(TAG, "🚀 SmsMonitorService — onCreate");
        Log.i(TAG, "🚀 ════════════════════════════════════════");

        startTimeMillis = System.currentTimeMillis();
        prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        notificationManager = getSystemService(NotificationManager.class);

        // 1. إنشاء قنوات الإشعارات
        createNotificationChannels();

        // 2. بدء الخدمة الأمامية فوراً (مطلوب خلال 5 ثوانٍ)
        startForeground(NOTIFICATION_ID, buildStatusNotification("جارٍ التهيئة..."));

        // 3. إعداد Worker Thread للمعالجة في الخلفية
        workerThread = new HandlerThread("VodaCash-Worker", android.os.Process.THREAD_PRIORITY_BACKGROUND);
        workerThread.start();
        workerHandler = new Handler(workerThread.getLooper());
        mainHandler = new Handler(Looper.getMainLooper());

        // 4. WakeLock
        acquireWakeLock();

        // 5. تهيئة WebSocket
        workerHandler.post(this::initializeWebSocket);

        // 6. بدء Heartbeat
        workerHandler.postDelayed(heartbeatRunnable, HEARTBEAT_INTERVAL);

        // 7. تفريغ الرسائل المعلقة من الجلسة السابقة
        workerHandler.post(this::drainOfflineQueue);

        currentState = ServiceState.RUNNING;
        updateStatusNotification();

        // حفظ حالة التشغيل
        prefs.edit().putBoolean("was_running", true).apply();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent == null) {
            Log.w(TAG, "⚠️ Null intent — service restarted by system");
            return START_STICKY;
        }

        String action = intent.getAction();
        if (action == null) action = ACTION_START;

        switch (action) {
            case ACTION_NEW_SMS:
                String sender    = intent.getStringExtra("sender");
                String body      = intent.getStringExtra("body");
                long   timestamp = intent.getLongExtra("timestamp", System.currentTimeMillis());
                workerHandler.post(() -> processSms(sender, body, timestamp));
                break;

            case ACTION_RESTART_WS:
                workerHandler.post(() -> {
                    if (wsManager != null) wsManager.reconnect();
                });
                break;

            case ACTION_STOP:
                stopSelf();
                break;

            case ACTION_START:
            default:
                Log.i(TAG, "▶️ Service started/restarted");
                break;
        }

        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        Log.w(TAG, "⚠️ ════════════════════════════════════════");
        Log.w(TAG, "⚠️ SmsMonitorService — onDestroy");
        Log.w(TAG, "⚠️ ════════════════════════════════════════");

        currentState = ServiceState.STOPPING;

        // إيقاف Heartbeat
        if (workerHandler != null) {
            workerHandler.removeCallbacks(heartbeatRunnable);
        }

        // إغلاق WebSocket
        if (wsManager != null) {
            wsManager.disconnect();
        }

        // تحرير WakeLock
        releaseWakeLock();

        // إيقاف Worker Thread
        if (workerThread != null) {
            workerThread.quitSafely();
        }

        // جدولة إعادة تشغيل تلقائية كخط دفاع أخير
        if (prefs.getBoolean("was_running", false)) {
            scheduleRestart();
        }

        super.onDestroy();
    }

    @Override
    public void onTaskRemoved(Intent rootIntent) {
        // المستخدم أزال التطبيق من Recent Apps
        Log.w(TAG, "🗑️ Task removed — scheduling restart");
        scheduleRestart();
        super.onTaskRemoved(rootIntent);
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    // ═════════════════════════════════════════════════════════════════════
    // معالجة الرسائل (SMS Processing)
    // ═════════════════════════════════════════════════════════════════════

    private void processSms(String sender, String body, long timestamp) {
        Log.i(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
        Log.i(TAG, "📨 New SMS | Sender: " + sender);
        Log.i(TAG, "📄 Length: " + body.length() + " chars");

        processedCount++;

        try {
            // ── بناء JSON للإرسال ─────────────────────────────────────
            JSONObject payload = new JSONObject();
            payload.put("type", "NEW_SMS");
            payload.put("sender", sender);
            payload.put("body", body);
            payload.put("timestamp", timestamp);
            payload.put("received_at", System.currentTimeMillis());

            String message = payload.toString();

            // ── إرسال عبر WebSocket أو تخزين مؤقت ────────────────────
            if (wsManager != null && wsManager.isConnected()) {
                wsManager.send(message);
                sentCount++;
                Log.i(TAG, "📤 Sent via WebSocket");
            } else {
                enqueueMessage(message);
                Log.w(TAG, "📦 Queued (offline) — queue size: " + offlineQueue.size());
            }

            // ── تحديث الإشعار ────────────────────────────────────────
            mainHandler.post(this::updateStatusNotification);

            // ── إشعار تنبيهي للرسائل المهمة ─────────────────────────
            if (body.contains("تم استلام") || body.toLowerCase().contains("received")) {
                showAlertNotification("💰 تم استلام تحويل جديد", body);
            }

        } catch (Exception e) {
            Log.e(TAG, "❌ Error processing SMS: " + e.getMessage(), e);
        }
    }

    // ═════════════════════════════════════════════════════════════════════
    // Offline Queue
    // ═════════════════════════════════════════════════════════════════════

    private void enqueueMessage(String message) {
        synchronized (offlineQueue) {
            if (offlineQueue.size() >= MAX_QUEUE_SIZE) {
                offlineQueue.poll(); // إزالة الأقدم
                Log.w(TAG, "⚠️ Queue full — dropped oldest message");
            }
            offlineQueue.add(message);
            queuedCount++;
        }
    }

    private void drainOfflineQueue() {
        if (wsManager == null || !wsManager.isConnected()) return;

        synchronized (offlineQueue) {
            int drained = 0;
            while (!offlineQueue.isEmpty() && wsManager.isConnected()) {
                String msg = offlineQueue.poll();
                if (msg != null) {
                    wsManager.send(msg);
                    drained++;
                    sentCount++;
                }
            }
            if (drained > 0) {
                Log.i(TAG, "📤 Drained " + drained + " queued messages");
                mainHandler.post(this::updateStatusNotification);
            }
        }
    }

    // ═════════════════════════════════════════════════════════════════════
    // WebSocket
    // ═════════════════════════════════════════════════════════════════════

    private void initializeWebSocket() {
        wsManager = new WebSocketManager(
            this, // Context
            // onConnected
            () -> {
                Log.i(TAG, "🟢 WebSocket connected");
                mainHandler.post(this::updateStatusNotification);
                workerHandler.post(this::drainOfflineQueue);
            },
            // onDisconnected
            (reason) -> {
                Log.w(TAG, "🔴 WebSocket disconnected: " + reason);
                mainHandler.post(this::updateStatusNotification);
                // إعادة الاتصال بعد تأخير
                workerHandler.postDelayed(() -> {
                    if (currentState == ServiceState.RUNNING && wsManager != null) {
                        wsManager.reconnect();
                    }
                }, RECONNECT_DELAY);
            },
            // onMessage
            (message) -> {
                Log.d(TAG, "📥 WS message: " + message);
            }
        );

        wsManager.connect();
    }

    // ═════════════════════════════════════════════════════════════════════
    // الإشعارات (Notifications)
    // ═════════════════════════════════════════════════════════════════════

    private void createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            // قناة الحالة الدائمة (صامتة)
            NotificationChannel statusChannel = new NotificationChannel(
                CHANNEL_ID, "مراقبة فودافون كاش", NotificationManager.IMPORTANCE_LOW
            );
            statusChannel.setDescription("إشعار دائم يوضح حالة المراقبة");
            statusChannel.setShowBadge(false);

            // قناة التنبيهات (صوتية)
            NotificationChannel alertChannel = new NotificationChannel(
                CHANNEL_ALERT_ID, "تنبيهات فودافون كاش", NotificationManager.IMPORTANCE_HIGH
            );
            alertChannel.setDescription("إشعارات عند استلام تحويلات");

            if (notificationManager != null) {
                notificationManager.createNotificationChannel(statusChannel);
                notificationManager.createNotificationChannel(alertChannel);
            }
        }
    }

    private Notification buildStatusNotification(String text) {
        Intent tapIntent = new Intent(this, MainActivity.class);
        tapIntent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent pendingTap = PendingIntent.getActivity(
            this, 0, tapIntent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        // زر إيقاف الخدمة
        Intent stopIntent = new Intent(this, SmsMonitorService.class);
        stopIntent.setAction(ACTION_STOP);
        PendingIntent pendingStop = PendingIntent.getService(
            this, 1, stopIntent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        String wsStatus = (wsManager != null && wsManager.isConnected()) ? "🟢" : "🔴";

        return new NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(wsStatus + " VodaCash Monitor")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentIntent(pendingTap)
            .addAction(android.R.drawable.ic_delete, "إيقاف", pendingStop)
            .setOngoing(true)
            .setSilent(true)
            .setShowWhen(false)
            .build();
    }

    private void updateStatusNotification() {
        long uptime = (System.currentTimeMillis() - startTimeMillis) / 60_000;
        int queueSize;
        synchronized (offlineQueue) { queueSize = offlineQueue.size(); }

        String status = String.format(Locale.getDefault(),
            "معالجة: %d | مرسل: %d | انتظار: %d | تشغيل: %d د",
            processedCount, sentCount, queueSize, uptime
        );

        if (notificationManager != null) {
            notificationManager.notify(NOTIFICATION_ID, buildStatusNotification(status));
        }
    }

    private void showAlertNotification(String title, String body) {
        String preview = body.length() > 100 ? body.substring(0, 100) + "..." : body;

        Notification alert = new NotificationCompat.Builder(this, CHANNEL_ALERT_ID)
            .setContentTitle(title)
            .setContentText(preview)
            .setStyle(new NotificationCompat.BigTextStyle().bigText(preview))
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setAutoCancel(true)
            .build();

        if (notificationManager != null) {
            notificationManager.notify((int) System.currentTimeMillis(), alert);
        }
    }

    // ═════════════════════════════════════════════════════════════════════
    // WakeLock
    // ═════════════════════════════════════════════════════════════════════

    private void acquireWakeLock() {
        PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
        if (pm != null) {
            wakeLock = pm.newWakeLock(
                PowerManager.PARTIAL_WAKE_LOCK,
                "VodaCash::MonitorWakeLock"
            );
            wakeLock.acquire(24 * 60 * 60 * 1000L); // 24 ساعة
            Log.d(TAG, "🔒 WakeLock acquired (24h)");
        }
    }

    private void releaseWakeLock() {
        if (wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release();
            Log.d(TAG, "🔓 WakeLock released");
        }
    }

    // ═════════════════════════════════════════════════════════════════════
    // إعادة التشغيل التلقائي (Auto-Restart)
    // ═════════════════════════════════════════════════════════════════════

    private void scheduleRestart() {
        Log.i(TAG, "⏰ Scheduling service restart in 3 seconds...");
        Intent restartIntent = new Intent(this, SmsMonitorService.class);
        restartIntent.setAction(ACTION_START);

        PendingIntent pendingRestart = PendingIntent.getService(
            this, RESTART_ALARM_ID, restartIntent,
            PendingIntent.FLAG_ONE_SHOT | PendingIntent.FLAG_IMMUTABLE
        );

        AlarmManager alarm = (AlarmManager) getSystemService(Context.ALARM_SERVICE);
        if (alarm != null) {
            alarm.setExactAndAllowWhileIdle(
                AlarmManager.ELAPSED_REALTIME_WAKEUP,
                SystemClock.elapsedRealtime() + 3_000,
                pendingRestart
            );
        }
    }

    // ═════════════════════════════════════════════════════════════════════
    // Static Helpers
    // ═════════════════════════════════════════════════════════════════════

    /** بدء الخدمة من أي مكان */
    public static void start(Context context) {
        Intent intent = new Intent(context, SmsMonitorService.class);
        intent.setAction(ACTION_START);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            context.startForegroundService(intent);
        } else {
            context.startService(intent);
        }
    }

    /** إيقاف الخدمة */
    public static void stop(Context context) {
        Intent intent = new Intent(context, SmsMonitorService.class);
        intent.setAction(ACTION_STOP);
        context.startService(intent);
    }
}
