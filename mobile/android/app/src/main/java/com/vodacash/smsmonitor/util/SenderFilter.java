package com.vodacash.smsmonitor.util;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

/**
 * فلترة المرسلين — قبول فقط الأرقام الرسمية لفودافون كاش مصر.
 *
 * الأرقام الرسمية المعروفة:
 * - VodafoneCash / VodaCash  → الاسم النصي الذي يظهر كمرسل
 * - Vodafone                → إشعارات عامة من فودافون
 * - 858                      → الرقم القصير لخدمة فودافون كاش
 * - 01010                    → رقم خدمة فودافون
 * - 2000                     → رقم خدمة فودافون
 */
public final class SenderFilter {

    private SenderFilter() {} // لا يمكن إنشاء كائن منه

    /**
     * قائمة الأسماء النصية (Alphanumeric Sender IDs) الرسمية.
     * تتم المقارنة بدون حساسية لحالة الأحرف.
     */
    private static final Set<String> OFFICIAL_ALPHA_SENDERS = new HashSet<>(Arrays.asList(
        "vodafonecash",
        "vodacash",
        "vodafone"
    ));

    /**
     * قائمة الأرقام القصيرة (Short Codes) الرسمية.
     */
    private static final Set<String> OFFICIAL_SHORT_CODES = new HashSet<>(Arrays.asList(
        "858",
        "01010",
        "2000"
    ));

    /**
     * التحقق مما إذا كان المرسل رقم/اسم رسمي لفودافون كاش.
     *
     * @param sender عنوان المرسل كما يأتي من SmsMessage.getOriginatingAddress()
     * @return true إذا كان المرسل رسمي
     */
    public static boolean isOfficialVodafoneCash(String sender) {
        if (sender == null || sender.trim().isEmpty()) {
            return false;
        }

        String cleaned = sender.trim();

        // 1. مطابقة تامة مع الأرقام القصيرة
        if (OFFICIAL_SHORT_CODES.contains(cleaned)) {
            return true;
        }

        // 2. مطابقة مع الأسماء النصية (بدون حساسية)
        if (OFFICIAL_ALPHA_SENDERS.contains(cleaned.toLowerCase())) {
            return true;
        }

        // 3. مطابقة جزئية (بعض الأجهزة تضيف بادئة دولية)
        String lowerSender = cleaned.toLowerCase();
        for (String alpha : OFFICIAL_ALPHA_SENDERS) {
            if (lowerSender.contains(alpha)) {
                return true;
            }
        }

        return false;
    }
}
