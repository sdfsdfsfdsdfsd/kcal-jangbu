"""식약처 전국통합식품영양성분정보(음식 + 원재료성식품) 표준데이터를 받아 foods.json으로 압축.

foods.json 형식: {"v": 기준일, "n": 개수, "d": [[이름, 업체, 기준량당kcal, 단위(g|ml), 1회제공량(0=없음), 대분류, 출처]]}
출처: F=외식 프랜차이즈(업체 제공), D=음식(가정식·외식·급식), R=원재료
"""
import json, sys, time, datetime, urllib.parse
import requests

BASE = "https://www.data.go.kr"
SETS = [
    ("15100070", "tn_pubr_public_nutri_food_info_svc"),      # 음식
    ("15100065", "tn_pubr_public_nutri_material_info_svc"),  # 원재료성식품
]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"

def fetch_set(s, pk, table):
    page_url = f"{BASE}/data/{pk}/standard.do"
    s.get(page_url, timeout=60)
    hdr = {"Referer": page_url, "X-Requested-With": "XMLHttpRequest", "Accept": "application/json, text/javascript, */*; q=0.01"}
    cols = s.get(f"{BASE}/download/columList.json", params={"pk": pk, "ext": "JSON"}, headers=hdr, timeout=60).json()
    codes = [c["columCode"] for c in cols["columList"]]
    rows, page, per = [], 1, 10000
    while True:
        params = [("publicDataPk", pk), ("totalCount", "1000000"), ("svcTableNm", table), ("perPage", str(per)), ("page", str(page))]
        params += [("colNmList", c) for c in codes]
        r = s.get(f"{BASE}/download/standard.json?" + urllib.parse.urlencode(params), headers=hdr, timeout=300)
        r.raise_for_status()
        part = r.json()
        if not isinstance(part, list):
            raise RuntimeError(f"unexpected response for {pk} page {page}: {str(part)[:200]}")
        rows += part
        print(f"{pk} page {page}: {len(part)} rows", flush=True)
        if len(part) < per:
            break
        page += 1
        time.sleep(1)
    return rows

def num(v):
    try:
        return float(str(v).replace(",", ""))
    except Exception:
        return None

PRI = {"가정식(분석 함량)": 1, "외식(분석함량)": 2, "외식(재료량 기반 산출함량)": 3}

def main():
    s = requests.Session()
    s.headers["User-Agent"] = UA
    dish = fetch_set(s, *SETS[0])
    raw = fetch_set(s, *SETS[1])
    out, gen, seen = [], {}, set()
    for r in dish:
        if r.get("FOOD_CD") in seen:
            continue
        seen.add(r.get("FOOD_CD"))
        k = num(r.get("ENERC"))
        if k is None:
            continue
        unit = "ml" if "ml" in str(r.get("NUT_CON_SRTR_QUA", "")).lower() else "g"
        name = str(r.get("FOOD_NM", "")).strip()
        origin = str(r.get("FOOD_ORIGIN_NM", ""))
        if "프랜차이즈" in origin:
            brand = r.get("REST_NM") or ""
            brand = "" if brand == "해당없음" else brand.strip()
            disp = name.split("_", 1)[1].strip() if "_" in name else name
            sz = num(str(r.get("FOOD_SIZE", "")).lower().replace("ml", "").replace("g", "")) or 0
            out.append([disp, brand, round(k, 1), unit, 0 if sz == 100 else round(sz), r.get("FOOD_LV3_NM", ""), "F"])
        else:
            pri = PRI.get(origin, 9)
            row = [name.replace("_", " "), "", round(k, 1), unit, 0, r.get("FOOD_LV3_NM", ""), "D", pri]
            if name not in gen or gen[name][7] > pri:
                gen[name] = row
    out += [r[:7] for r in gen.values()]
    rseen = set()
    for r in raw:
        if r.get("FOOD_CD") in rseen:
            continue
        rseen.add(r.get("FOOD_CD"))
        k = num(r.get("ENERC"))
        if k is None:
            continue
        unit = "ml" if "ml" in str(r.get("NUT_CON_SRTR_QUA", "")).lower() else "g"
        out.append([str(r.get("FOOD_NM", "")).replace("_", " ").strip(), "", round(k, 1), unit, 0, r.get("FOOD_LV3_NM", ""), "R"])
    for row in out:
        if isinstance(row[2], float) and row[2].is_integer():
            row[2] = int(row[2])
    data = {"v": datetime.date.today().isoformat(), "n": len(out), "d": out}
    with open("foods.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print("foods.json:", len(out), "items")
    if len(out) < 5000:
        sys.exit("too few items, refusing to overwrite")

if __name__ == "__main__":
    main()
