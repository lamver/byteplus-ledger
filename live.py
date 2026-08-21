"""Расход в реальном времени: последний час по 5-минутным окнам.

  python live.py            # последний час
  python live.py 3          # последние 3 часа
  python live.py 1 --watch  # обновлять каждые 60 секунд

Биллинг BytePlus отстаёт примерно на 5-15 минут, это нормально.
"""
import billing, sys, time, datetime
from collections import defaultdict

hours = 1.0
for a in sys.argv[1:]:
    try:
        hours = float(a)
    except ValueError:
        pass
WATCH = "--watch" in sys.argv


def f(x, k):
    try:
        return float(x.get(k) or 0)
    except (ValueError, TypeError):
        return 0.0


def fetch_rows():
    """Тянем текущий и предыдущий месяц, чтобы не терять смену месяца."""
    rows = []
    d = datetime.date.today().replace(day=1)
    for m in [datetime.date.today().strftime("%Y-%m"),
              (d - datetime.timedelta(days=1)).strftime("%Y-%m")]:
        off = 0
        while True:
            c, r = billing.request(
                "open.byteplusapi.com", "billing", "ap-southeast-1",
                "ListBillDetail", "2022-01-01",
                {"Limit": "100", "Offset": str(off), "BillPeriod": m,
                 "GroupPeriod": "2", "GroupTerm": "0", "IgnoreZero": "1"})
            if c != 200:
                break
            p = (r.get("Result") or {}).get("List") or []
            rows += p
            off += len(p)
            if len(p) < 100:
                break
    return rows


def parse(t):
    try:
        return datetime.datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def render():
    rows = fetch_rows()
    # Только строки расхода: у выданных пакетов ExpenseEndTime лежит
    # на два года вперёд и сбивает опорную точку.
    usage = [x for x in rows if x.get("BillCategory") == "Consumption-usage"]
    stamps = [parse(x.get("ExpenseEndTime")) for x in usage]
    stamps = [s for s in stamps if s]
    if not stamps:
        print("нет данных о расходе")
        return
    # Опорная точка это самая свежая запись биллинга, а не локальные часы:
    # у аккаунта свой часовой пояс, и локальное время может не совпадать.
    latest = max(stamps)
    since = latest - datetime.timedelta(hours=hours)

    win = defaultdict(lambda: defaultdict(float))
    per_model = defaultdict(lambda: defaultdict(float))
    for x in usage:
        t = parse(x.get("ExpenseEndTime"))
        if not t or t <= since:
            continue
        slot = t.replace(minute=(t.minute // 5) * 5, second=0)
        el = (x.get("Element") or "")
        kind = ("cache" if "KVcache" in el else
                "out" if "completion" in el else
                "in" if "prompt" in el else "other")
        w = win[slot]
        w[kind] += f(x, "Count")
        w["paid"] += f(x, "PretaxAmount")
        w["ded"] += f(x, "DeductionCount")
        m = per_model[x.get("ConfigName") or "?"]
        m["used"] += f(x, "Count")
        m["ded"] += f(x, "DeductionCount")
        m["paid"] += f(x, "PretaxAmount")

    print(f"=== Расход за последние {hours:g} ч "
          f"(до {latest:%Y-%m-%d %H:%M} по данным биллинга) ===")
    if not win:
        print("  за период трат нет")
        return
    print(f"  {'окно':7s}{'in K':>9s}{'out K':>9s}{'cache K':>10s}"
          f"{'бесплатно':>11s}{'$':>8s}")
    for slot in sorted(win):
        w = win[slot]
        print(f"  {slot:%H:%M}  {w['in']:>9.1f}{w['out']:>9.1f}{w['cache']:>10.1f}"
              f"{w['ded']:>11.1f}{w['paid']:>8.2f}")

    tin = sum(w["in"] for w in win.values())
    tout = sum(w["out"] for w in win.values())
    tcache = sum(w["cache"] for w in win.values())
    tded = sum(w["ded"] for w in win.values())
    tpaid = sum(w["paid"] for w in win.values())
    total = tin + tout + tcache
    print(f"  {'ИТОГО':7s}{tin:>9.1f}{tout:>9.1f}{tcache:>10.1f}"
          f"{tded:>11.1f}{tpaid:>8.2f}")

    span = max(0.1, (max(win) - min(win)).total_seconds() / 60 + 5)
    print(f"\n  всего {total:.1f}K токенов за {span:.0f} мин "
          f"= {total / span:.1f}K/мин = {total / span * 60:.0f}K/час")
    if tpaid:
        print(f"  темп трат: {tpaid / span * 60:.2f} USD/час")
    else:
        print("  пока всё покрыто бесплатными пакетами")

    print("\n  по моделям:")
    for m, a in sorted(per_model.items(), key=lambda i: -i[1]["used"]):
        cov = 100 * a["ded"] / a["used"] if a["used"] else 0
        print(f"    {m:24s}{a['used']:>10.1f}K  покрыто {cov:>3.0f}%  "
              f"${a['paid']:.2f}")


if WATCH:
    while True:
        print("\033[2J\033[H", end="")
        render()
        print(f"\n  обновление каждые 60 с, Ctrl+C для выхода "
              f"({datetime.datetime.now():%H:%M:%S})")
        time.sleep(60)
else:
    render()
