"""Общая сводка по BytePlus API: доступ к моделям + расход за всю историю.

  python report.py           # сводка из биллинга и каталога
  python report.py --probe   # + реальная проверка доступа к каждой LLM/VLM
"""
import billing, json, sys, os, datetime, urllib.request
from collections import defaultdict

KEY = os.environ.get("ARK_API_KEY", "")
ARK = "https://ark.ap-southeast.bytepluses.com/api/v3/"
PROBE = "--probe" in sys.argv


def f(x, k):
    try:
        return float(x.get(k) or 0)
    except (ValueError, TypeError):
        return 0.0


def ark_get(path):
    req = urllib.request.Request(ARK + path,
                                 headers={"Authorization": "Bearer " + KEY})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def probe(mid):
    body = json.dumps({"model": mid, "max_tokens": 1,
                       "messages": [{"role": "user", "content": "hi"}]}).encode()
    req = urllib.request.Request(ARK + "chat/completions", data=body, headers={
        "Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            r.read()
            return "OPEN"
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())["error"]["code"]
        except Exception:
            return f"HTTP{e.code}"
    except Exception:
        return "TIMEOUT"


def months_back(n=14):
    d = datetime.date.today().replace(day=1)
    out = []
    for _ in range(n):
        out.append(d.strftime("%Y-%m"))
        d = (d - datetime.timedelta(days=1)).replace(day=1)
    return list(reversed(out))


def bill_rows(month):
    rows, off = [], 0
    while True:
        c, d = billing.request(
            "open.byteplusapi.com", "billing", "ap-southeast-1",
            "ListBillDetail", "2022-01-01",
            {"Limit": "100", "Offset": str(off), "BillPeriod": month,
             "GroupPeriod": "2", "GroupTerm": "0", "IgnoreZero": "0"})
        if c != 200:
            return rows
        part = (d.get("Result") or {}).get("List") or []
        rows += part
        off += len(part)
        if len(part) < 100:
            return rows


# ---------- 1. аккаунт ----------
c, bal = billing.request("open.byteplusapi.com", "billing", "ap-southeast-1",
                         "QueryBalanceAcct", "2022-01-01")
b = bal.get("Result", {})
print("=" * 74)
print(f"АККАУНТ {b.get('AccountID')}   валюта {b.get('Currency')}")
print(f"  баланс {b.get('AvailableBalance')} | кредитный лимит {b.get('CreditLimit')} "
      f"| долг {b.get('ArrearsBalance')} | заморожено {b.get('FreezeAmount')}")
print("  overage невозможен: нет ни баланса, ни кредита"
      if b.get("AvailableBalance") == "0" and b.get("CreditLimit") == "0"
      else "  ВНИМАНИЕ: есть средства/кредит, overage спишется автоматически")

# ---------- 2. расход по месяцам ----------
print("\n" + "=" * 74)
print("РАСХОД ПО МЕСЯЦАМ")
all_rows = {}
grand_plan = grand_payg = grand_unpaid = 0.0
for m in months_back():
    rows = bill_rows(m)
    if not rows:
        continue
    all_rows[m] = rows
    plan = sum(f(x, "PretaxAmount") for x in rows
               if x.get("BillingMode") == "Yearly/monthly")
    payg = sum(f(x, "PretaxAmount") for x in rows
               if x.get("BillingMode") != "Yearly/monthly")
    unpaid = sum(f(x, "UnpaidAmount") for x in rows)
    grand_plan += plan
    grand_payg += payg
    grand_unpaid += unpaid
    print(f"  {m}   подписка {plan:6.2f} | сверх плана {payg:6.2f} | "
          f"не оплачено {unpaid:5.2f}  = {plan + payg:6.2f} USD")
print(f"  {'ИТОГО':7s} подписка {grand_plan:6.2f} | сверх плана {grand_payg:6.2f} | "
      f"не оплачено {grand_unpaid:5.2f}  = {grand_plan + grand_payg:6.2f} USD")

# ---------- 3. по моделям за всю историю ----------
print("\n" + "=" * 74)
print("РАСХОД ПО МОДЕЛЯМ (за всю историю)")
agg = defaultdict(lambda: defaultdict(float))
for m, rows in all_rows.items():
    for x in rows:
        if x.get("BillingMode") == "Yearly/monthly":
            agg[x.get("ConfigName") or x.get("Product") or "?"]["plan"] += f(x, "PretaxAmount")
            continue
        a = agg[x.get("ConfigName") or "?"]
        a["used"] += f(x, "Count")
        a["ded"] += f(x, "DeductionCount")
        a["paid"] += f(x, "PretaxAmount")

print(f"  {'модель':26s}{'K токенов':>11s}{'из плана':>10s}{'покрытие':>10s}{'$ сверх':>9s}")
for m, a in sorted(agg.items(), key=lambda i: -(i[1]["paid"] + i[1]["plan"])):
    if a["plan"] and not a["used"]:
        print(f"  {m:26s}{'-':>11s}{'-':>10s}{'подписка':>10s}{a['plan']:>9.2f}")
        continue
    cov = 100 * a["ded"] / a["used"] if a["used"] else 0
    print(f"  {m:26s}{a['used']:>11.1f}{a['ded']:>10.1f}{cov:>9.0f}%{a['paid']:>9.2f}")

# ---------- 4. каталог моделей ----------
print("\n" + "=" * 74)
print("КАТАЛОГ МОДЕЛЕЙ ARK (живые, без Shutdown)")
cat = ark_get("models")["data"]
live = [m for m in cat if m.get("status") not in ("Shutdown",)]
text = [m for m in live if m.get("domain") in ("LLM", "VLM")]
other = [m for m in live if m.get("domain") not in ("LLM", "VLM")]
print(f"  всего в каталоге {len(cat)}, живых {len(live)}, "
      f"текстовых/мультимодальных {len(text)}")

if PROBE:
    print("\n  проверка доступа (реальный запрос):")
    for m in sorted(text, key=lambda x: x["id"]):
        st = probe(m["id"])
        mark = "ОТКРЫТА " if st == "OPEN" else "закрыта "
        print(f"    {mark}{m['id']:34s}{'' if st == 'OPEN' else st}")
else:
    print("  (запусти с --probe, чтобы проверить доступ по каждой)")
    for m in sorted(text, key=lambda x: x["id"]):
        print(f"    {m['id']:34s}{m.get('domain',''):5s}"
              f"ctx={m.get('token_limits', {}).get('context_window', '?')}")

print("\n  не-текстовые (видео/картинки/эмбеддинги/3D):")
for m in sorted(other, key=lambda x: x["id"]):
    print(f"    {m['id']:34s}{m.get('domain','')}")
