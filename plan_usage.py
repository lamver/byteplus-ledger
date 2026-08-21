"""Сколько израсходовано в рамках подписки (пакета) vs сверх неё."""
import billing, json, sys
from collections import defaultdict

month = sys.argv[1] if len(sys.argv) > 1 else "2026-08"
rows, off = [], 0
while True:
    c, d = billing.request(
        "open.byteplusapi.com", "billing", "ap-southeast-1",
        "ListBillDetail", "2022-01-01",
        {"Limit": "100", "Offset": str(off), "BillPeriod": month,
         "GroupPeriod": "2", "GroupTerm": "0", "IgnoreZero": "0"})
    if c != 200:
        print(c, json.dumps(d)[:400]); sys.exit(1)
    part = (d.get("Result") or {}).get("List") or []
    rows += part
    off += len(part)
    if len(part) < 100:
        break


def f(x, k):
    try:
        return float(x.get(k) or 0)
    except ValueError:
        return 0.0


agg = defaultdict(lambda: {"count": 0.0, "ded": 0.0, "vou": 0.0,
                           "paid": 0.0, "unit": "", "price": ""})
plan_cost = 0.0
first, last = None, None
for x in rows:
    if x.get("BillingMode") == "Yearly/monthly":
        plan_cost += f(x, "PretaxAmount")
        continue
    k = x.get("Element", "?")
    a = agg[k]
    a["count"] += f(x, "Count")
    a["ded"] += f(x, "DeductionCount")
    a["vou"] += f(x, "PickupVoucherDeductCount")
    a["paid"] += f(x, "PretaxAmount")
    a["unit"] = x.get("Unit", "")
    a["price"] = x.get("Price", "")
    t = x.get("ExpenseEndTime") or x.get("ExpenseDate")
    if t:
        first = min(first or t, t)
        last = max(last or t, t)

print(f"=== BytePlus {month} ===")
print(f"Подписка (Yearly/monthly): {plan_cost:.2f} USD")
print(f"Период трат: {first}  ..  {last}\n")

tot_paid = tot_ded = 0.0
print(f"{'Элемент':34s}{'использовано':>16s}{'из пакета':>12s}{'ваучер':>10s}{'к оплате':>10s}")
for k, a in sorted(agg.items()):
    tot_paid += a["paid"]
    tot_ded += a["ded"]
    print(f"{k:34s}{a['count']:>12.3f} {a['unit']:<3s}{a['ded']:>12.3f}"
          f"{a['vou']:>10.3f}{a['paid']:>10.2f}")

print(f"\nПокрыто пакетом/подпиской: {tot_ded:.3f} ед.")
print(f"Оплачено сверх подписки (pay-as-you-go): {tot_paid:.2f} USD")
print(f"ИТОГО за {month}: {plan_cost + tot_paid:.2f} USD")
