"""BytePlus/Volcengine billing query: account balance + Ark spend.

Usage:
  python billing.py balance
  python billing.py bill 2026-08
"""
import sys, os, json, hmac, hashlib, datetime
import urllib.request, urllib.parse

def _load_env():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_env()
AK = os.environ.get("BP_AK", "")
SK = os.environ.get("BP_SK", "")
if not AK or not SK:
    raise SystemExit("Set BP_AK / BP_SK in projects/byteplus/.env")


def _sign(key, msg):
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def request(host, service, region, action, version, query=None, body=None, method="GET"):
    query = dict(query or {})
    query.update({"Action": action, "Version": version})
    qs = urllib.parse.urlencode(sorted(query.items()))
    payload = json.dumps(body) if body else ""
    now = datetime.datetime.now(datetime.timezone.utc)
    xdate = now.strftime("%Y%m%dT%H%M%SZ")
    datestamp = xdate[:8]
    hashed_payload = hashlib.sha256(payload.encode()).hexdigest()

    headers = {
        "Host": host,
        "X-Date": xdate,
        "X-Content-Sha256": hashed_payload,
        "Content-Type": "application/json",
    }
    signed_headers = "content-type;host;x-content-sha256;x-date"
    canonical_headers = (
        f"content-type:application/json\nhost:{host}\n"
        f"x-content-sha256:{hashed_payload}\nx-date:{xdate}\n"
    )
    canonical_request = "\n".join(
        [method, "/", qs, canonical_headers, signed_headers, hashed_payload]
    )
    scope = f"{datestamp}/{region}/{service}/request"
    string_to_sign = "\n".join(
        ["HMAC-SHA256", xdate, scope,
         hashlib.sha256(canonical_request.encode()).hexdigest()]
    )
    k = _sign(SK.encode(), datestamp)
    k = _sign(k, region)
    k = _sign(k, service)
    k = _sign(k, "request")
    signature = hmac.new(k, string_to_sign.encode(), hashlib.sha256).hexdigest()
    headers["Authorization"] = (
        f"HMAC-SHA256 Credential={AK}/{scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    url = f"https://{host}/?{qs}"
    req = urllib.request.Request(
        url, data=payload.encode() if payload else None, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


HOSTS = [
    ("open.byteplusapi.com", "billing", "ap-southeast-1"),
    ("billing.byteplusapi.com", "billing", "ap-southeast-1"),
    ("open.volcengineapi.com", "billing", "cn-beijing"),
]


def try_all(action, version, query=None):
    for host, svc, region in HOSTS:
        code, data = request(host, svc, region, action, version, query)
        print(f"--- {host} [{region}] {action} -> HTTP {code}")
        print(json.dumps(data, ensure_ascii=False, indent=2)[:3000])
        if code == 200:
            return data
    return None


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "balance"
    if cmd == "balance":
        try_all("QueryBalanceAcct", "2022-01-01")
    elif cmd == "bill":
        month = sys.argv[2] if len(sys.argv) > 2 else datetime.date.today().strftime("%Y-%m")
        try_all("ListBillDetail", "2022-01-01",
                {"BillPeriod": month, "Limit": "100", "Offset": "0",
                 "GroupPeriod": "2", "IgnoreZero": "1"})
    elif cmd == "overview":
        month = sys.argv[2] if len(sys.argv) > 2 else datetime.date.today().strftime("%Y-%m")
        try_all("ListBillOverviewByProd", "2022-01-01",
                {"BillPeriod": month, "Limit": "100", "Offset": "0"})
