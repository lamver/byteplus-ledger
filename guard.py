"""Сторож перерасхода сверх подписки BytePlus.

  python guard.py               # текущий месяц, порог 0.00 USD
  python guard.py 2026-08 0.50  # конкретный месяц и порог
  python guard.py "" 1.20       # текущий месяц, порог 1.20

Порог удобен, когда часть расхода уже накоплена и разбираться с ней
отдельно: сторож тогда молчит про старое и реагирует только на новое.

Exit code 1, если pay-as-you-go расход превысил порог.
"""
import billing, sys, datetime
from collections import defaultdict

# Пустая строка допустима: guard_run.cmd передаёт её как «месяц по умолчанию»,
# чтобы позиционно добраться до второго аргумента.
month = sys.argv[1].strip() if len(sys.argv) > 1 and sys.argv[1].strip() else \
    datetime.date.today().strftime("%Y-%m")
limit = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0

rows, off = [], 0
while True:
    c, d = billing.request(
        "open.byteplusapi.com", "billing", "ap-southeast-1",
        "ListBillDetail", "2022-01-01",
        {"Limit": "100", "Offset": str(off), "BillPeriod": month,
         "GroupPeriod": "2", "GroupTerm": "0", "IgnoreZero": "0"})
    if c != 200:
        print("API error", c, d); sys.exit(2)
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


plan = sum(f(x, "PretaxAmount") for x in rows if x.get("BillingMode") == "Yearly/monthly")
payg = [x for x in rows if x.get("BillingMode") != "Yearly/monthly"]
over = sum(f(x, "PretaxAmount") for x in payg)
unpaid = sum(f(x, "UnpaidAmount") for x in payg)

by_model = defaultdict(float)
for x in payg:
    by_model[x.get("ConfigName") or x.get("Element", "?")] += f(x, "PretaxAmount")

c, bal = billing.request("open.byteplusapi.com", "billing", "ap-southeast-1",
                         "QueryBalanceAcct", "2022-01-01")
b = bal.get("Result", {})

print(f"[{month}] подписка {plan:.2f} | сверх подписки {over:.2f} USD "
      f"(не оплачено {unpaid:.2f})")
print(f"баланс {b.get('AvailableBalance')} USD, кредит {b.get('CreditLimit')}, "
      f"долг {b.get('ArrearsBalance')}")
for k, v in sorted(by_model.items(), key=lambda i: -i[1]):
    if v > 0:
        print(f"   перерасход: {k:24s} {v:.2f} USD")

if over > limit:
    print(f"!! ПРЕВЫШЕН ПОРОГ {limit:.2f} USD")
    sys.exit(1)
print("OK: в рамках подписки")
