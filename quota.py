"""Остаток бесплатных пакетов и квот BytePlus.

Пакеты видны в биллинге как Consumption-purchase (Product=*resource_packages*),
а расход по ним как DeductionCount в строках Consumption-usage.

  python quota.py
"""
import billing, sys, datetime
from collections import defaultdict


def f(x, k):
    try:
        return float(x.get(k) or 0)
    except (ValueError, TypeError):
        return 0.0


def fetch(months=16):
    rows = []
    d = datetime.date.today().replace(day=1)
    for _ in range(months):
        m, off = d.strftime("%Y-%m"), 0
        while True:
            c, r = billing.request(
                "open.byteplusapi.com", "billing", "ap-southeast-1",
                "ListBillDetail", "2022-01-01",
                {"Limit": "100", "Offset": str(off), "BillPeriod": m,
                 "GroupPeriod": "2", "GroupTerm": "0", "IgnoreZero": "0"})
            if c != 200:
                break
            p = (r.get("Result") or {}).get("List") or []
            rows += p
            off += len(p)
            if len(p) < 100:
                break
        d = (d - datetime.timedelta(days=1)).replace(day=1)
    return rows


rows = fetch()

# 1. купленные/выданные пакеты
packs = {}
for x in rows:
    if x.get("BillCategory") != "Consumption-purchase":
        continue
    cfg = x.get("ConfigName") or "?"
    if "Unit" == x.get("Unit"):      # подписка, не пакет
        continue
    base = (cfg.replace("-free-inference-res-pack", "")
               .replace("-Pack-Free-Infer", "")
               .replace("-inference-res-pack", "").strip())
    qty = f(x, "Count")
    if x.get("Unit") == "tokens":
        qty /= 1000.0                # приводим к K tokens
    p = packs.setdefault(base, {"qty": 0.0, "unit": "K tokens", "exp": ""})
    p["qty"] += qty
    p["unit"] = "K tokens" if x.get("Unit") == "tokens" else x.get("Unit", "")
    p["exp"] = max(p["exp"], x.get("ExpenseEndTime", "") or "")

# 2. фактический расход
use = defaultdict(lambda: defaultdict(float))
for x in rows:
    if x.get("BillCategory") != "Consumption-usage":
        continue
    a = use[x.get("ConfigName") or "?"]
    a["used"] += f(x, "Count")
    a["ded"] += f(x, "DeductionCount")
    a["paid"] += f(x, "PretaxAmount")
    a["unit"] = 0
    a.setdefault("u", 0)

units = {x.get("ConfigName"): x.get("Unit") for x in rows
         if x.get("BillCategory") == "Consumption-usage"}

print("=== БЕСПЛАТНЫЕ ПАКЕТЫ И ОСТАТКИ ===")
names = sorted(set(list(packs) + list(use)))
for n in names:
    p = packs.get(n)
    a = use.get(n, defaultdict(float))
    unit = (p or {}).get("unit") or units.get(n, "")
    if p:
        left = max(0.0, p["qty"] - a["ded"])
        bar = int(20 * min(1.0, a["ded"] / p["qty"])) if p["qty"] else 0
        flag = "  ИСЧЕРПАН" if left <= 0 else ""
        print(f"{n:26s} [{'#' * bar}{'.' * (20 - bar)}] "
              f"{a['ded']:>9.1f}/{p['qty']:<9.1f}{unit:9s} "
              f"осталось {left:>9.1f}{flag}")
        if p["exp"]:
            print(f"{'':26s}  действует до {p['exp'][:10]}, "
                  f"переплата {a['paid']:.2f} USD")
    elif a["used"]:
        print(f"{n:26s} без пакета: использовано {a['used']:.1f} {unit}, "
              f"оплачено {a['paid']:.2f} USD")

tot = sum(v["paid"] for v in use.values())
print(f"\nВсего оплачено сверх пакетов: {tot:.2f} USD")
