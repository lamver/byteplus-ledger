"""Проверка моделей на endpoint подписки Coding Plan."""
import urllib.request, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import billing  # noqa: подхватывает .env

KEY = os.environ["ARK_API_KEY"]
URL = "https://ark.ap-southeast.bytepluses.com/api/coding/v3/chat/completions"

models = ["ark-code-latest", "auto", "seed-2-0-pro-260328",
          "seed-2-0-lite-260228", "seed-2-0-code-preview-260328",
          "seed-1-6-code-preview", "glm-5.2", "glm-5-1-260408",
          "deepseek-v4-flash-260425", "deepseek-v4-pro-260425",
          "kimi-k2-5-260127", "gpt-oss-120b-250805"]

for m in models:
    body = json.dumps({"model": m, "max_tokens": 8,
                       "messages": [{"role": "user", "content": "say ok"}]}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            d = json.loads(r.read().decode())
            u = d.get("usage", {})
            print(f"OK     {m:32s} -> {d.get('model'):24s} "
                  f"tok={u.get('total_tokens')}")
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode())["error"]
            print(f"{e.code:<7}{m:32s} {err.get('code')}: "
                  f"{str(err.get('message'))[:60]}")
        except Exception:
            print(f"{e.code:<7}{m:32s}")
    except Exception as e:
        print(f"ERR    {m:32s} {e}")
