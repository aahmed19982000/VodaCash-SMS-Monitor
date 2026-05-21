package com.vodacash.smsmonitor.util;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

/**
 * فلترة المرسلين — قبول الأرقام والجهات الرسمية للمحافظ والبنوك وحظر الأرقام الشخصية.
 */
public final class SenderFilter {

    private SenderFilter() {} // لا يمكن إنشاء كائن منه

    private static final Set<String> KNOWN_SENDERS = new HashSet<>(Arrays.asList(
        // Vodafone Cash
        "vodafonecash", "vodacash", "vodafone", "vf cash", "vfcash", "vf-cash", "vf_cash", "858", "01010", "2000",
        // Orange Cash
        "orange cash", "orangecash", "orange", "orange-cash", "orange_cash", "7770",
        // Etisalat Cash
        "etisalatcash", "etisalat cash", "etisalat", "etisalat-cash", "etisalat_cash",
        // WE Pay
        "wepay", "we pay", "we_pay", "we", "we_cash",
        // InstaPay
        "instapay", "instapay egypt", "ipn",
        // Banks
        "cib", "cib egypt", "nbe", "nbe_eg", "bm", "banque misr", "qnb", "qnb egypt", "alexbank", "hsbc", "aaib"
    ));

    private static final String[] TRANSACTION_KEYWORDS = {
        "تحويل", "رصيد", "استلام", "خصم", "كاش", "سحب", "شحن", "فودافون", "اورنج", "اورنچ", "اتصالات", "وي باي", 
        "instapay", "transfer", "balance", "received", "paid", "egp", "le", "جنيه", "جنية", "شراء", "دفعت", "تم استلام"
    };

    /**
     * التحقق مما إذا كان الرقم رقماً شخصياً مصرياً لحماية خصوصية المستخدم.
     */
    public static boolean isPersonalPhone(String sender) {
        if (sender == null) return false;
        String clean = sender.trim().replace(" ", "").replace("-", "");
        return clean.matches("^(?:\\+?20|0)?1[0125]\\d{8}$");
    }

    /**
     * التحقق مما إذا كانت الرسالة واردة من جهة رسمية أو مرسل يحتوي على كلمات مفتاحية مالية.
     */
    public static boolean isPotentialTransactionSMS(String sender, String body) {
        if (sender == null || sender.trim().isEmpty()) {
            return false;
        }

        String cleanedSender = sender.trim().toLowerCase();

        // 1. مطابقة مباشرة مع الجهات المعروفة
        if (KNOWN_SENDERS.contains(cleanedSender)) {
            return true;
        }

        // 2. مطابقة جزئية مع الجهات المعروفة
        for (String official : KNOWN_SENDERS) {
            if (official.length() > 2 && cleanedSender.contains(official)) {
                return true;
            }
        }

        // 3. فلترة وحظر الأرقام الشخصية تماماً لحماية الخصوصية
        if (isPersonalPhone(cleanedSender)) {
            return false;
        }

        // 4. للمرسلين الآخرين (Alphanumeric أو Short Code)، نقبلهم لو كانت الرسالة مالية/تحويل
        boolean isAlpha = cleanedSender.matches(".*[a-zA-Z].*");
        boolean isShortCode = cleanedSender.matches("\\d+") && cleanedSender.length() <= 5;

        if (isAlpha || isShortCode) {
            if (body == null) return false;
            String lowerBody = body.toLowerCase();
            for (String kw : TRANSACTION_KEYWORDS) {
                if (lowerBody.contains(kw)) {
                    return true;
                }
            }
        }

        return false;
    }

    /**
     * متوافق مع الكود القديم للتحقق من فودافون كاش تحديداً.
     */
    public static boolean isOfficialVodafoneCash(String sender) {
        if (sender == null) return false;
        String cleaned = sender.trim().toLowerCase();
        return cleaned.contains("vodafone") || cleaned.contains("voda") || cleaned.contains("858") || cleaned.contains("vf");
    }
}
