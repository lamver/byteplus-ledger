import sys, billing

months = sys.argv[1:] or ["2026-05", "2026-06", "2026-07", "2026-08"]
for m in months:
    code, d = billing.request(
        "open.byteplusapi.com", "billing", "ap-southeast-1",
        "ListBillOverviewByProd", "2022-01-01",
        {"BillPeriod": m, "Limit": "100", "Offset": "0"})
    rows = (d.get("Result") or {}).get("List") or []
    tot = sum(float(x["PretaxAmount"]) for x in rows)
    unp = sum(float(x["UnpaidAmount"]) for x in rows)
    print(f"{m}  total={tot:.4f} USD  unpaid={unp:.4f} USD")
    for x in rows:
        print(f"    {x['Product']:32s} {x['BillingMode']:16s} "
              f"orig={x['OriginalBillAmount']:>12s} pretax={x['PretaxAmount']:>8s} "
              f"unpaid={x['UnpaidAmount']:>8s}")
