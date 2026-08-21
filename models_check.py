"""Какие модели реально отвечают по ключу подписки."""
import urllib.request, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import billing  # noqa: подхватит .env

KEY = os.environ.get("ARK_API_KEY", "")
URL = "https://ark.ap-southeast.bytepluses.com/api/v3/chat/completions"

models = [
    "seed-2-0-code-preview-260328",
    "seed-2-0-pro-260328",
    "seed-2-0-lite-260428",
    "seed-2-0-mini-260428",
    "deepseek-v4-pro-ga-260813",
    "deepseek-v4-flash-ga-260731",
    "deepseek-v4-pro-260425",
    "glm-5-2-260617",
    "glm-4-7-251222",
    "seed-1-8-251228",
    "dola-seed-2-1-turbo-260628",
]

for m in models:
    body = json.dumps({"model": m, "max_tokens": 4,
                       "messages": [{"role": "user", "content": "hi"}]}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            d = json.loads(r.read().decode())
            u = d.get("usage", {})
            print(f"OK    {m:32s} tokens={u.get('total_tokens')}")
    except urllib.error.HTTPError as e:
        err = json.loads(e.read().decode()).get("error", {})
        print(f"{e.code:<6}{m:32s} {err.get('code')}")
    except Exception as e:
        print(f"ERR   {m:32s} {e}")
