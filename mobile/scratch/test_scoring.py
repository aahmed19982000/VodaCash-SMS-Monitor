import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

msg = 'تم تنفيذ تحويل لحظي من حسابكم رقم 0140 بمبلغ 10.00 جم إلى احمد ا** ا** ا**** رقم مرجعي 235424765447 يوم 05-21 الساعة 14:27 للمزيد اتصل بـ 19623'
balance_kws = ["رصيدك", "رصيد", "الحالي", "الرصيد", "balance", "bal", "رصيد حسابك"]

amount_prefix_kws = ["بمبلغ", "مبلغ", "قيمة", "شحن", "خصم", "سحب", "تحويل", "received", "sent", "amount"]
amount_postfix_kws = ["جنيه", "جنية", "جم", "egp", "le"]

numbers_with_context = []
for match in re.finditer(r'(\d+(?:\.\d+)?)', msg):
    num_val = float(match.group(1))
    start_idx = match.start()
    context_before = msg[max(0, start_idx-35):start_idx].lower()
    context_after = msg[start_idx+len(match.group(1)):start_idx+len(match.group(1))+35].lower()
    numbers_with_context.append({
        "value": num_val,
        "str": match.group(1),
        "before": context_before,
        "after": context_after,
        "start": start_idx
    })

scored = []
for num in numbers_with_context:
    if len(num["str"]) >= 10:
        continue
    
    # Amount Score
    amt_score = 0
    # 1. Prefix keywords (only in before context)
    for kw in amount_prefix_kws:
        if kw in num["before"]:
            dist = len(num["before"]) - num["before"].rfind(kw)
            if dist <= 25:
                amt_score += 25 - dist
                print(f"Num {num['str']}: prefix '{kw}' in before dist {dist} -> amt +{25-dist}")
                
    # 2. Postfix keywords (only in after context)
    for kw in amount_postfix_kws:
        if kw in num["after"]:
            dist = num["after"].find(kw)
            if dist <= 25:
                amt_score += 25 - dist
                print(f"Num {num['str']}: postfix '{kw}' in after dist {dist} -> amt +{25-dist}")

    # Balance Score (only in before context)
    bal_score = 0
    for kw in balance_kws:
        if kw in num["before"]:
            dist = len(num["before"]) - num["before"].rfind(kw)
            if dist <= 35:
                bal_score += 35 - dist
                print(f"Num {num['str']}: '{kw}' in before dist {dist} -> bal +{35-dist}")

    scored.append({
        "num": num,
        "amt_score": amt_score,
        "bal_score": bal_score
    })

print("\n--- RESULTS ---")
for s in scored:
    print(f"Val: {s['num']['str']} | Amt: {s['amt_score']} | Bal: {s['bal_score']}")
