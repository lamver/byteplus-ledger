import billing, json, sys

month = sys.argv[1] if len(sys.argv) > 1 else "2026-08"
c, d = billing.request(
    "open.byteplusapi.com", "billing", "ap-southeast-1",
    "ListBillDetail", "2022-01-01",
    {"Limit": "100", "Offset": "0", "BillPeriod": month,
     "GroupPeriod": "2", "GroupTerm": "0", "IgnoreZero": "1"})
rows = (d.get("Result") or {}).get("List") or []
if c != 200:
    print(c, json.dumps(d)[:600]); sys.exit()
print(f"{month}: {len(rows)} строк")
for x in rows:
    print(f"  {x.get('BillingFunction',''):22s} {x.get('Product',''):26s} "
          f"{x.get('Element',''):28s} {x.get('Factor',''):14s} "
          f"use={x.get('Count','')}{x.get('Unit','')} "
          f"pretax={x.get('PayableAmount', x.get('PretaxAmount',''))}")
