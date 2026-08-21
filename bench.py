"""Быстрый тест качества deepseek-v4-pro-ga на задачах по коду + учёт токенов."""
import urllib.request, json, os, sys, time, subprocess, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import billing  # подхватывает .env

KEY = os.environ["ARK_API_KEY"]
URL = "https://ark.ap-southeast.bytepluses.com/api/v3/chat/completions"
MODEL = os.environ.get("BP_TEST_MODEL", "deepseek-v4-pro-ga-260813")

TASKS = [
    ("roman", "Напиши функцию Python `to_roman(n: int) -> str` для 1..3999. "
              "Только код, без объяснений и без markdown-ограждений.",
     "assert to_roman(1)=='I'; assert to_roman(4)=='IV'; assert to_roman(9)=='IX';"
     "assert to_roman(14)=='XIV'; assert to_roman(40)=='XL'; assert to_roman(1994)=='MCMXCIV';"
     "assert to_roman(3999)=='MMMCMXCIX'; assert to_roman(2026)=='MMXXVI'"),
    ("bugfix", "В этой функции есть баг, верни исправленную версию. "
               "Только код, без объяснений и без markdown-ограждений.\n\n"
               "def median(xs):\n    xs = sorted(xs)\n    return xs[len(xs)//2]\n",
     "assert median([1,2,3])==2; assert median([1,2,3,4])==2.5;"
     "assert median([5])==5; assert median([3,1,4,1,5,9,2,6])==3.5"),
    ("algo", "Напиши функцию `longest_common_prefix(strs: list[str]) -> str`. "
             "Только код, без объяснений и без markdown-ограждений.",
     "assert longest_common_prefix(['flower','flow','flight'])=='fl';"
     "assert longest_common_prefix(['dog','racecar','car'])=='';"
     "assert longest_common_prefix([])=='';"
     "assert longest_common_prefix(['abc'])=='abc';"
     "assert longest_common_prefix(['','a'])==''"),
]


def ask(prompt):
    body = json.dumps({"model": MODEL, "max_tokens": 2000, "temperature": 0,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read().decode())
    return d["choices"][0]["message"]["content"], d.get("usage", {}), time.time() - t0


def strip_fence(code):
    if "```" in code:
        parts = code.split("```")
        for p in parts[1:]:
            body = p.split("\n", 1)
            if len(body) == 2:
                return body[1] if not body[0].strip().startswith("`") else body[1]
    return code


def run(code, checks):
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     encoding="utf-8") as f:
        f.write(code + "\n" + checks + "\nprint('PASS')\n")
        p = f.name
    try:
        r = subprocess.run([sys.executable, p], capture_output=True,
                           text=True, timeout=30)
        return ("PASS" in r.stdout), (r.stderr.strip().splitlines() or [""])[-1]
    finally:
        os.unlink(p)


tot_in = tot_out = 0
passed = 0
print(f"model: {MODEL}\n")
for name, prompt, checks in TASKS:
    code, usage, dt = ask(prompt)
    tot_in += usage.get("prompt_tokens", 0)
    tot_out += usage.get("completion_tokens", 0)
    ok, err = run(strip_fence(code), checks)
    passed += ok
    print(f"[{'PASS' if ok else 'FAIL'}] {name:8s} {dt:5.1f}s  "
          f"in={usage.get('prompt_tokens')} out={usage.get('completion_tokens')}"
          + ("" if ok else f"  -> {err[:90]}"))

print(f"\nитого: {passed}/{len(TASKS)} задач")
print(f"токены: prompt {tot_in}, completion {tot_out}, всего {tot_in + tot_out}")
