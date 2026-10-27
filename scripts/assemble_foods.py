"""브라우저에서 받아 Firestore(kcal_foods_upload)에 잠시 올려둔 식약처 DB 조각을 합쳐 foods.json으로 저장."""
import json, sys, requests
KEY = "AIzaSyB-89z89yrJb8dDB36_3Sqc51504AywvWk"
BASE = "https://firestore.googleapis.com/v1/projects/project-1389660754781189097/databases/(default)/documents/kcal_foods_upload/"
meta = requests.get(BASE + "meta", params={"key": KEY}, timeout=60).json()["fields"]
n, chars = int(meta["parts"]["integerValue"]), int(meta["chars"]["integerValue"])
s = "".join(requests.get(BASE + f"part{i}", params={"key": KEY}, timeout=60).json()["fields"]["s"]["stringValue"] for i in range(n))
if len(s) != chars:
    sys.exit(f"length mismatch {len(s)} != {chars}")
data = json.loads(s)
if data["n"] < 5000:
    sys.exit("too few items")
with open("foods.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
print("foods.json", data["n"], "items, 기준일", data["v"])
