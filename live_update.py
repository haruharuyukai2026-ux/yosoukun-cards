"""5分おき(GitHub Actions)に公式サイトから、このあと30分の展示と、終わったレースの結果を取って live.json に書く。
allraces.json(朝に予想くんが作る今日の全レース)の締切時刻を見て、取りにいくレースを決める。"""
import json, re, os, time, datetime as dt, urllib.request
from bs4 import BeautifulSoup
JST = dt.timezone(dt.timedelta(hours=9)); now = dt.datetime.now(JST)
A = json.load(open("allraces.json"))
L = json.load(open("live.json")) if os.path.exists("live.json") else {}
if L.get("date") != A["date"]: L = {"date": A["date"], "ex": {}, "res": {}}
hm = lambda m: (now + dt.timedelta(minutes=m)).strftime("%H:%M")
today = now.strftime("%Y-%m-%d") == A["date"]
def get(page, code):
    u = f"https://www.boatrace.jp/owpc/pc/race/{page}?rno={int(code[10:12])}&jcd={code[8:10]}&hd={code[:8]}"
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (yosoukun personal)"})
    try:
        return BeautifulSoup(urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore"), "html.parser")
    except Exception as e:
        print("err", code, page, e); return None
tx = lambda e: re.sub(r"\s+", " ", e.get_text()) if e else ""
def ex(code):
    b = get("beforeinfo", code)
    if not b: return None
    boats = []
    for t in b.select(".table1 tbody")[1:7]:
        m = re.match(r"\s*(\d)\s+.*?([\d.]+)kg\s+([\d.]+)\s+(-?[\d.]+)", tx(t)[:60])
        if m: boats.append(dict(w=int(m.group(1)), ex=float(m.group(3)), tilt=float(m.group(4))))
    st = {}
    for i, e in enumerate(b.select(".table1_boatImage1")):
        m = re.match(r"\s*(\d)\s*(F|L)?\s*\.?(\d+)", re.sub(r"\s+", "", e.get_text()))
        if m: st[int(m.group(1))] = dict(course=i + 1, exst=float("0." + m.group(3)) * (-1 if m.group(2) == "F" else 1))
    for x in boats: x.update(st.get(x["w"], {}))
    w = tx(b.select_one(".weather1")); wind = re.search(r"風速\s*(\d+)m", w); wave = re.search(r"波高\s*(\d+)cm", w)
    return dict(boats=boats, wind=float(wind.group(1)) if wind else None, wave=float(wave.group(1)) if wave else None, at=now.strftime("%H:%M"))
def res(code):
    s = get("raceresult", code)
    if not s: return None
    for t in s.select("table"):
        m = re.search(r"3連単 (\d-\d-\d) ¥([\d,]+)", tx(t))
        if m: return [m.group(1), int(m.group(2).replace(",", ""))]
    return None
n = 0
if today:
    A["races"].sort(key=lambda r: 0 if (hm(-60) <= (r.get("deadline") or "") <= hm(-3)) else 1)
    for r in A["races"]:
        c, d = r["code"], r.get("deadline") or ""
        if n >= 30: break
        if hm(0) <= d <= hm(30) and len((L["ex"].get(c) or {}).get("boats", [])) < 6:
            x = ex(c); n += 1; time.sleep(1)
            if x and x["boats"]: L["ex"][c] = x
        elif hm(-60) <= d <= hm(-3) and c not in L["res"] and not r.get("result"):
            x = res(c); n += 1; time.sleep(1)
            if x: L["res"][c] = x
L["updated"] = now.strftime("%Y-%m-%d %H:%M")
json.dump(L, open("live.json", "w"), ensure_ascii=False)
print("fetched", n, "ex", len(L["ex"]), "res", len(L["res"]))
