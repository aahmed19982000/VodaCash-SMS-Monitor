package com.vodacash.smsmonitor;

import android.Manifest;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.google.android.material.button.MaterialButton;
import com.vodacash.smsmonitor.service.SmsMonitorService;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * النشاط الرئيسي — يطلب أذونات SMS عند بدء التطبيق
 * ثم يُشغّل الخدمة الأمامية ويقوم بتحديث الواجهة.
 */
public class MainActivity extends AppCompatActivity {

    private static final int SMS_PERMISSION_CODE = 100;
    private static final int NOTIFICATION_PERMISSION_CODE = 101;

    // الأذونات المطلوبة لعمل التطبيق
    private static final String[] REQUIRED_PERMISSIONS = {
        Manifest.permission.RECEIVE_SMS,
        Manifest.permission.READ_SMS,
    };

    // عناصر الواجهة
    private View connectionDot;
    private TextView tvConnectionStatus;
    private TextView tvUptime;
    private TextView tvTotalReceived;
    private TextView tvTotalSent;
    private TextView tvPending;
    private MaterialButton btnToggleService;
    private TextView tvBalance;
    private TextView tvLastUpdate;
    private RecyclerView rvTransactions;
    private TransactionAdapter transactionAdapter;
    private final List<JSONObject> transactionList = new ArrayList<>();

    private TextView tvWalletsTitle;
    private RecyclerView rvWallets;
    private WalletAdapter walletAdapter;
    private final List<WalletItem> walletList = new ArrayList<>();

    // مستقبل البث للحالة
    private final BroadcastReceiver statusReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            if (intent != null && SmsMonitorService.ACTION_STATUS_UPDATE.equals(intent.getAction())) {
                boolean isConnected = intent.getBooleanExtra("isConnected", false);
                String statusDetails = intent.getStringExtra("statusDetails");
                int processedCount = intent.getIntExtra("processedCount", 0);
                int sentCount = intent.getIntExtra("sentCount", 0);
                int queueSize = intent.getIntExtra("queueSize", 0);
                long startTimeMillis = intent.getLongExtra("startTimeMillis", System.currentTimeMillis());

                double balance = intent.getDoubleExtra("currentBalance", 0.0);
                String lastUpdate = intent.getStringExtra("lastBalanceUpdate");
                String txJson = intent.getStringExtra("recentTransactions");
                String walletBalancesJson = intent.getStringExtra("walletBalances");

                updateUI(isConnected, statusDetails, processedCount, sentCount, queueSize, startTimeMillis, balance, lastUpdate, txJson, walletBalancesJson);
            }
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        // ربط عناصر الواجهة
        connectionDot = findViewById(R.id.connectionDot);
        tvConnectionStatus = findViewById(R.id.tvConnectionStatus);
        tvUptime = findViewById(R.id.tvUptime);
        tvTotalReceived = findViewById(R.id.tvTotalReceived);
        tvTotalSent = findViewById(R.id.tvTotalSent);
        tvPending = findViewById(R.id.tvPending);
        btnToggleService = findViewById(R.id.btnToggleService);
        tvBalance = findViewById(R.id.tvBalance);
        tvLastUpdate = findViewById(R.id.tvLastUpdate);
        rvTransactions = findViewById(R.id.rvTransactions);
        tvWalletsTitle = findViewById(R.id.tvWalletsTitle);
        rvWallets = findViewById(R.id.rvWallets);
 
        // إعداد RecyclerView العمليات
        transactionAdapter = new TransactionAdapter(transactionList);
        rvTransactions.setLayoutManager(new LinearLayoutManager(this));
        rvTransactions.setAdapter(transactionAdapter);

        // إعداد RecyclerView المحافظ
        walletAdapter = new WalletAdapter(walletList);
        rvWallets.setLayoutManager(new LinearLayoutManager(this, LinearLayoutManager.HORIZONTAL, false));
        rvWallets.setAdapter(walletAdapter);

        // زر الإعدادات
        findViewById(R.id.btnSettings).setOnClickListener(v -> {
            android.content.Intent intent = new android.content.Intent(this, SettingsActivity.class);
            startActivity(intent);
        });

        // زر تشغيل/إيقاف الخدمة
        btnToggleService.setOnClickListener(v -> {
            if (SmsMonitorService.isRunning()) {
                // إيقاف الخدمة ومنع إعادة تشغيلها تلقائياً
                getSharedPreferences("vodacash_service", MODE_PRIVATE)
                    .edit()
                    .putBoolean("was_running", false)
                    .apply();
                SmsMonitorService.stop(this);
                updateUI(false, "الخدمة متوقفة", 0, 0, 0, System.currentTimeMillis());
            } else {
                // تشغيل الخدمة
                getSharedPreferences("vodacash_service", MODE_PRIVATE)
                    .edit()
                    .putBoolean("was_running", true)
                    .apply();
                SmsMonitorService.start(this);
            }
        });

        checkAndRequestPermissions();
    }

    @Override
    protected void onResume() {
        super.onResume();
        
        // تسجيل مستقبل البث المتوافق مع إصدارات أندرويد المختلفة
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(statusReceiver, new IntentFilter(SmsMonitorService.ACTION_STATUS_UPDATE), Context.RECEIVER_NOT_EXPORTED);
        } else {
            registerReceiver(statusReceiver, new IntentFilter(SmsMonitorService.ACTION_STATUS_UPDATE));
        }

        // تحديث الواجهة بشكل مبدئي
        if (SmsMonitorService.isRunning()) {
            SmsMonitorService service = SmsMonitorService.getInstance();
            if (service != null) {
                service.refreshStatus();
            }
        } else {
            updateUI(false, "الخدمة متوقفة", 0, 0, 0, System.currentTimeMillis());
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        try {
            unregisterReceiver(statusReceiver);
        } catch (IllegalArgumentException ignored) {}
    }

    // تحديث الواجهة الرسومية بناءً على حالة الخدمة والـ WebSocket
    private void updateUI(boolean isConnected, String statusDetails, int processed, int sent, int pending, long startTimeMillis) {
        updateUI(isConnected, statusDetails, processed, sent, pending, startTimeMillis, 0.0, "—", null, null);
    }

    private void updateUI(boolean isConnected, String statusDetails, int processed, int sent, int pending, long startTimeMillis, double balance, String lastUpdate, String transactionsJson, String walletBalancesJson) {
        if (isConnected) {
            connectionDot.setBackgroundResource(R.drawable.circle_green);
            tvConnectionStatus.setText("متصل");
            tvConnectionStatus.setTextColor(ContextCompat.getColor(this, android.R.color.holo_green_light));
        } else {
            connectionDot.setBackgroundResource(R.drawable.circle_red);
            String statusText = "غير متصل";
            if (statusDetails != null && !statusDetails.isEmpty()) {
                statusText += " (" + statusDetails + ")";
            }
            tvConnectionStatus.setText(statusText);
            tvConnectionStatus.setTextColor(ContextCompat.getColor(this, android.R.color.darker_gray));
        }

        // حساب وقت التشغيل (Uptime)
        long diff = System.currentTimeMillis() - startTimeMillis;
        long seconds = (diff / 1000) % 60;
        long minutes = (diff / (1000 * 60)) % 60;
        long hours = (diff / (1000 * 60 * 60)) % 24;
        tvUptime.setText(String.format(Locale.getDefault(), "%02d:%02d", hours * 60 + minutes, seconds)); // إظهار الدقائق والثواني لتسهيل الملاحظة

        // تحديث الإحصائيات
        tvTotalReceived.setText(String.valueOf(processed));
        tvTotalSent.setText(String.valueOf(sent));
        tvPending.setText(String.valueOf(pending));

        // زر التحكم بالخدمة
        if (SmsMonitorService.isRunning()) {
            btnToggleService.setText("إيقاف المراقبة");
            btnToggleService.setBackgroundTintList(ContextCompat.getColorStateList(this, android.R.color.holo_red_dark));
        } else {
            btnToggleService.setText("تشغيل المراقبة");
            btnToggleService.setBackgroundTintList(ContextCompat.getColorStateList(this, android.R.color.holo_green_dark));
        }

        // تحديث الرصيد ووقت التحديث
        if (tvBalance != null) {
            tvBalance.setText(String.format(Locale.US, "%.2f", balance));
        }
        if (tvLastUpdate != null) {
            tvLastUpdate.setText("آخر تحديث: " + (lastUpdate != null ? lastUpdate : "—"));
        }

        // تحديث قائمة المحافظ
        walletList.clear();
        if (walletBalancesJson != null && !walletBalancesJson.isEmpty() && !walletBalancesJson.equals("{}")) {
            try {
                JSONObject walletObj = new JSONObject(walletBalancesJson);
                java.util.Iterator<String> keys = walletObj.keys();
                while (keys.hasNext()) {
                    String wId = keys.next();
                    double wBal = walletObj.optDouble(wId, 0.0);
                    
                    // استبعاد undefined أو unspecified لو كان رصيدها 0 لتنظيف الواجهة
                    if ("unspecified".equals(wId) && wBal == 0.0) {
                        continue;
                    }

                    // الحصول على إعدادات المظهر للمحفظة
                    String nameEn = "Unspecified";
                    String nameAr = "غير محدد";
                    String startColor = "#4E6E5D";
                    String endColor = "#2E4E3D";
                    String icon = "❓";

                    switch (wId) {
                        case "vodafone_cash":
                            nameEn = "Vodafone Cash";
                            nameAr = "فودافون كاش";
                            startColor = "#E60000";
                            endColor = "#990000";
                            icon = "📱";
                            break;
                        case "orange_cash":
                            nameEn = "Orange Cash";
                            nameAr = "أورنج كاش";
                            startColor = "#FF6600";
                            endColor = "#CC5200";
                            icon = "🍊";
                            break;
                        case "etisalat_cash":
                            nameEn = "Etisalat Cash";
                            nameAr = "اتصالات كاش";
                            startColor = "#78BE20";
                            endColor = "#5A8F18";
                            icon = "💚";
                            break;
                        case "we_pay":
                            nameEn = "WE Pay";
                            nameAr = "وي باي";
                            startColor = "#512D6D";
                            endColor = "#351C49";
                            icon = "🟣";
                            break;
                        case "instapay":
                            nameEn = "InstaPay";
                            nameAr = "انستاباي";
                            startColor = "#EC008C";
                            endColor = "#00ADEF";
                            icon = "⚡";
                            break;
                        case "bank":
                            nameEn = "Bank Account";
                            nameAr = "حساب بنكي";
                            startColor = "#005A70";
                            endColor = "#003A48";
                            icon = "🏦";
                            break;
                    }

                    walletList.add(new WalletItem(wId, nameEn, nameAr, wBal, startColor, endColor, icon));
                }
            } catch (Exception e) {
                Log.e("VodaCash_UI", "Error parsing wallet balances: " + e.getMessage());
            }
        }

        if (walletList.isEmpty()) {
            if (tvWalletsTitle != null) tvWalletsTitle.setVisibility(View.GONE);
            if (rvWallets != null) rvWallets.setVisibility(View.GONE);
        } else {
            if (tvWalletsTitle != null) tvWalletsTitle.setVisibility(View.VISIBLE);
            if (rvWallets != null) rvWallets.setVisibility(View.VISIBLE);
            if (walletAdapter != null) {
                walletAdapter.notifyDataSetChanged();
            }
        }

        // تحديث قائمة العمليات
        if (transactionsJson != null) {
            try {
                JSONArray array = new JSONArray(transactionsJson);
                transactionList.clear();
                for (int i = 0; i < array.length(); i++) {
                    Object item = array.get(i);
                    if (item instanceof String) {
                        transactionList.add(new JSONObject((String) item));
                    } else if (item instanceof JSONObject) {
                        transactionList.add((JSONObject) item);
                    }
                }
                if (transactionAdapter != null) {
                    transactionAdapter.notifyDataSetChanged();
                }
            } catch (Exception e) {
                Log.e("VodaCash_UI", "Error parsing recent transactions: " + e.getMessage());
            }
        } else {
            transactionList.clear();
            if (transactionAdapter != null) {
                transactionAdapter.notifyDataSetChanged();
            }
        }
    }

    private String formatTimestamp(String isoStr) {
        if (isoStr == null || isoStr.isEmpty()) return "—";
        try {
            int tIndex = isoStr.indexOf('T');
            if (tIndex != -1 && isoStr.length() >= tIndex + 6) {
                String timePart = isoStr.substring(tIndex + 1, tIndex + 6); // HH:mm
                String datePart = isoStr.substring(5, tIndex); // MM-dd
                return datePart.replace('-', '/') + " " + timePart;
            }
        } catch (Exception e) {
            // ignore and fallback
        }
        return isoStr;
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
        if (!SmsMonitorService.isRunning()) {
            Toast.makeText(this, "✅ تم تفعيل مراقبة فودافون كاش", Toast.LENGTH_SHORT).show();
            SmsMonitorService.start(this);
        }
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

    // ═════════════════════════════════════════════════════════════════════
    // محول قائمة العمليات (Transaction Adapter)
    // ═════════════════════════════════════════════════════════════════════
    private class TransactionAdapter extends RecyclerView.Adapter<TransactionAdapter.ViewHolder> {
        private final List<JSONObject> items;

        public TransactionAdapter(List<JSONObject> items) {
            this.items = items;
        }

        @NonNull
        @Override
        public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            View view = LayoutInflater.from(parent.getContext())
                    .inflate(R.layout.item_transaction, parent, false);
            return new ViewHolder(view);
        }

        @Override
        public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
            JSONObject tx = items.get(position);
            if (tx == null) return;

            String type = tx.optString("type", "UNKNOWN");
            double amount = tx.optDouble("amount", 0.0);
            String counterpart = tx.optString("counterpart", "");
            String timestamp = tx.optString("sms_timestamp", tx.optString("parsed_at", ""));

            holder.tvTimestamp.setText(formatTimestamp(timestamp));

            if (counterpart == null || counterpart.isEmpty()) {
                holder.tvCounterpart.setText("—");
            } else {
                holder.tvCounterpart.setText(counterpart);
            }

            String typeText;
            String iconText = "⚙️";
            int iconBg = R.drawable.circle_red;
            int amountColor = 0xFFF44336;
            String amountPrefix = "-";

            switch (type) {
                case "RECEIVED":
                    typeText = "استلام تحويل";
                    iconText = "↓";
                    iconBg = R.drawable.circle_green;
                    amountColor = 0xFF4CAF50;
                    amountPrefix = "+";
                    break;
                case "SENT":
                    typeText = "تحويل صادر";
                    iconText = "↑";
                    iconBg = R.drawable.circle_red;
                    amountColor = 0xFFF44336;
                    amountPrefix = "-";
                    break;
                case "BILL":
                    typeText = "دفع فاتورة";
                    iconText = "🧾";
                    iconBg = R.drawable.circle_red;
                    amountColor = 0xFFF44336;
                    amountPrefix = "-";
                    break;
                case "PURCHASE":
                    typeText = "شراء";
                    iconText = "🛍️";
                    iconBg = R.drawable.circle_red;
                    amountColor = 0xFFF44336;
                    amountPrefix = "-";
                    break;
                case "TOPUP":
                    typeText = "شحن رصيد";
                    iconText = "📱";
                    iconBg = R.drawable.circle_red;
                    amountColor = 0xFFF44336;
                    amountPrefix = "-";
                    break;
                case "BALANCE":
                    typeText = "استعلام رصيد";
                    iconText = "💳";
                    iconBg = R.drawable.circle_green;
                    amountColor = 0xFF4CAF50;
                    amountPrefix = "";
                    break;
                case "UNKNOWN":
                default:
                    typeText = "عملية غير معروفة";
                    iconText = "❓";
                    iconBg = R.drawable.circle_red;
                    amountColor = 0xFF888888;
                    amountPrefix = "";
                    break;
            }

            holder.tvTxType.setText(typeText);
            holder.tvIcon.setText(iconText);
            holder.tvIcon.setBackgroundResource(iconBg);
            holder.tvAmount.setTextColor(amountColor);
            holder.tvAmount.setText(String.format(Locale.US, "%s%.2f", amountPrefix, amount));
        }

        @Override
        public int getItemCount() {
            return items.size();
        }

        class ViewHolder extends RecyclerView.ViewHolder {
            final TextView tvIcon;
            final TextView tvTxType;
            final TextView tvCounterpart;
            final TextView tvAmount;
            final TextView tvTimestamp;

            ViewHolder(@NonNull View itemView) {
                super(itemView);
                tvIcon = itemView.findViewById(R.id.tvIcon);
                tvTxType = itemView.findViewById(R.id.tvTxType);
                tvCounterpart = itemView.findViewById(R.id.tvCounterpart);
                tvAmount = itemView.findViewById(R.id.tvAmount);
                tvTimestamp = itemView.findViewById(R.id.tvTimestamp);
            }
        }
    }

    private static class WalletItem {
        String id;
        String nameEn;
        String nameAr;
        double balance;
        String startColor;
        String endColor;
        String icon;

        WalletItem(String id, String nameEn, String nameAr, double balance, String startColor, String endColor, String icon) {
            this.id = id;
            this.nameEn = nameEn;
            this.nameAr = nameAr;
            this.balance = balance;
            this.startColor = startColor;
            this.endColor = endColor;
            this.icon = icon;
        }
    }

    private class WalletAdapter extends RecyclerView.Adapter<WalletAdapter.ViewHolder> {
        private final List<WalletItem> items;

        public WalletAdapter(List<WalletItem> items) {
            this.items = items;
        }

        @NonNull
        @Override
        public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            View view = LayoutInflater.from(parent.getContext())
                    .inflate(R.layout.item_wallet, parent, false);
            return new ViewHolder(view);
        }

        @Override
        public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
            WalletItem wallet = items.get(position);
            holder.tvWalletNameEn.setText(wallet.nameEn);
            holder.tvWalletNameAr.setText(wallet.nameAr);
            holder.tvWalletIcon.setText(wallet.icon);
            holder.tvWalletBalance.setText(String.format(Locale.US, "%.2f EGP", wallet.balance));

            try {
                android.graphics.drawable.GradientDrawable gd = new android.graphics.drawable.GradientDrawable(
                    android.graphics.drawable.GradientDrawable.Orientation.TL_BR,
                    new int[] {
                        android.graphics.Color.parseColor(wallet.startColor),
                        android.graphics.Color.parseColor(wallet.endColor)
                    }
                );
                gd.setCornerRadius(dpToPx(12));
                holder.itemView.setBackground(gd);
            } catch (Exception e) {
                holder.itemView.setBackgroundResource(R.drawable.card_dark);
            }
        }

        @Override
        public int getItemCount() {
            return items.size();
        }

        private int dpToPx(int dp) {
            float density = getResources().getDisplayMetrics().density;
            return Math.round((float) dp * density);
        }

        class ViewHolder extends RecyclerView.ViewHolder {
            final TextView tvWalletIcon;
            final TextView tvWalletNameEn;
            final TextView tvWalletNameAr;
            final TextView tvWalletBalance;

            ViewHolder(@NonNull View itemView) {
                super(itemView);
                tvWalletIcon = itemView.findViewById(R.id.tvWalletIcon);
                tvWalletNameEn = itemView.findViewById(R.id.tvWalletNameEn);
                tvWalletNameAr = itemView.findViewById(R.id.tvWalletNameAr);
                tvWalletBalance = itemView.findViewById(R.id.tvWalletBalance);
            }
        }
    }
}

