"""Покрытие подпиской по моделям: сколько токенов вычтено из плана vs оплачено."""
import billing, sys
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
        print(c, d); sys.exit(1)
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


agg = defaultdict(lambda: defaultdict(float))
for x in rows:
    if x.get("BillingMode") == "Yearly/monthly":
        continue
    m = x.get("ConfigName") or "?"
    a = agg[m]
    a["used"] += f(x, "Count")
    a["ded"] += f(x, "DeductionCount")
    a["paid"] += f(x, "PretaxAmount")

print(f"{'модель':22s}{'токенов':>12s}{'из плана':>12s}{'покрытие':>10s}{'$ сверх':>9s}")
for m, a in sorted(agg.items(), key=lambda i: -i[1]["paid"]):
    cov = 100 * a["ded"] / a["used"] if a["used"] else 0
    print(f"{m:22s}{a['used']:>12.1f}{a['ded']:>12.1f}{cov:>9.0f}%{a['paid']:>9.2f}")
