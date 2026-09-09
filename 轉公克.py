# -*- coding: utf-8 -*-
"""
食譜食材公克換算腳本
====================
用途：讀取「清洗後食譜.json」，將所有主要食材與調味料的份量統一換算為公克(g)，
     輸出成一份 Excel 表（原始 JSON 完全不會被修改）。

用法：
    python 食譜食材公克換算.py

可自行調整下方「參數設定」區塊的路徑，或修改換算係數/預設重量表。

換算規則總覽：
 1. 重量單位（公克/克/g/公斤/斤/兩/錢）－ 直接換算。
 2. 容積單位（大匙/小匙/杯/CC/ml/碗…）－ 假設密度≈1 g/ml 換算。
 3. 計數單位（顆/個/片/根/包…）－ 先比對常見食材專屬重量表，查無則用「每單位概略重量」估計。
 4. 模糊份量（少許/適量/些許…）－ 依慣用估計值換算成固定公克數（見 VAGUE_GRAMS），
    這類數字僅為方便計算所抓的「概略值」，實際用量請依個人口味調整。
"""

import json
import re
from openpyxl import Workbook

# ========== 參數設定 ==========
INPUT_JSON = "清洗後食譜.json"          # 來源檔案（不會被修改）
OUTPUT_XLSX = "食譜食材公克換算表.xlsx"  # 輸出檔案

# ========== 中文數字對照 ==========
CN_NUM = {
    "半": 0.5, "一": 1, "二": 2, "兩": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12,
    "廿": 20, "數": 3,
}

# ========== 模糊份量 -> 固定公克估計值 ==========
# 這些字詞在食譜裡沒有明確重量，以下為料理上常見的概略估計，供換算使用。
VAGUE_GRAMS = {
    "少許": 1,
    "些許": 1,
    "少量": 3,
    "少些": 3,
    "些量": 3,
    "適量": 5,
    "酌量": 5,
    "隨意": 5,
    "隨量": 5,
    "微量": 0.5,
    "一些": 3,
    "數滴": 0.15,
}

# ========== 單位清單（由長到短排序，避免子字串誤判） ==========
UNITS = [
    "公克", "公斤", "公升", "毫升", "㏄", "cc", "CC", "Cc", "ml", "ML",
    "盎司", "oz", "OZ", "磅", "lb", "LB",
    "大匙", "湯匙", "小匙", "茶匙", "中匙", "匙",
    "量杯", "大杯", "小杯", "杯",
    "小塊", "大塊", "小段", "大片", "小片", "小朵", "小包", "人份",
    "顆", "個", "支", "根", "條", "片", "粒", "朵", "塊", "隻", "尾",
    "包", "張", "盒", "罐", "瓣", "把", "份", "枝", "棵", "株", "瓶",
    "球", "段", "副", "滴", "組", "葉", "公分", "付", "鍋", "碗",
    "克", "g", "G", "兩", "斤", "錢",
]
UNITS_SORTED = sorted(set(UNITS), key=len, reverse=True)
UNIT_ALT = "|".join(re.escape(u) for u in UNITS_SORTED)

NUM = r"\d+(?:\.\d+)?"
FRAC = rf"{NUM}\s*[/\\]\s*{NUM}"
CN_NUM_ALT = "|".join(sorted(CN_NUM.keys(), key=len, reverse=True))
VAGUE_ALT = "|".join(VAGUE_GRAMS.keys())

QTY = rf"(?:{FRAC}|{NUM}|{CN_NUM_ALT}|{VAGUE_ALT})"
FULL_TOKEN_RE = re.compile(rf"^({QTY})({UNIT_ALT})?$")
BARE_QTY_RE = re.compile(rf"^({QTY})$")
BARE_UNIT_RE = re.compile(rf"^({UNIT_ALT})$")

# ========== 直接換算係數（假設密度≈1 g/ml 的容積單位也含在內） ==========
DIRECT_FACTOR = {
    "公克": 1, "克": 1, "g": 1, "G": 1,
    "公斤": 1000, "斤": 600, "兩": 37.5, "錢": 3.75,
    "cc": 1, "CC": 1, "Cc": 1, "㏄": 1, "ml": 1, "ML": 1, "毫升": 1, "公升": 1000,
    "大匙": 15, "湯匙": 15, "中匙": 10, "小匙": 5, "茶匙": 5, "匙": 15,
    "杯": 200, "量杯": 200, "大杯": 300, "小杯": 100,
    "碗": 200,
    "盎司": 28.35, "oz": 28.35, "OZ": 28.35, "磅": 453.6, "lb": 453.6, "LB": 453.6,
    "滴": 0.05,
}
VOLUME_UNITS = {
    "cc", "CC", "Cc", "㏄", "ml", "ML", "毫升", "公升",
    "大匙", "湯匙", "中匙", "小匙", "茶匙", "匙",
    "杯", "量杯", "大杯", "小杯", "碗", "滴",
}

# ========== 常見食材「每單位」估計重量表（關鍵字比對食材名稱） ==========
INGREDIENT_UNIT_WEIGHT = [
    (("雞蛋", "全蛋", "土雞蛋", "鴨蛋", "鹹蛋", "皮蛋"), {"顆", "個"}, 55),
    (("蛋",), {"顆", "個"}, 55),
    (("蛋黃",), {"顆", "個"}, 20),
    (("蛋白",), {"顆", "個"}, 35),
    (("蒜頭", "大蒜", "蒜仁", "蒜瓣"), {"瓣", "顆", "粒"}, 5),
    (("蔥", "青蔥", "蔥白"), {"根", "支"}, 15),
    (("薑",), {"片"}, 3),
    (("薑",), {"塊"}, 20),
    (("檸檬",), {"顆", "個", "粒"}, 100),
    (("柳橙", "柳丁", "柑橘"), {"顆", "個", "粒"}, 150),
    (("小蕃茄", "小番茄", "聖女番茄", "聖女蕃茄"), {"顆", "個", "粒"}, 15),
    (("番茄", "蕃茄"), {"顆", "個", "粒"}, 150),
    (("洋蔥",), {"顆", "個"}, 200),
    (("馬鈴薯", "洋芋"), {"顆", "個"}, 150),
    (("紅蘿蔔", "胡蘿蔔"), {"條", "根"}, 150),
    (("小黃瓜", "大黃瓜", "黃瓜"), {"條", "根"}, 100),
    (("豆腐",), {"塊", "盒"}, 300),
    (("吐司", "土司"), {"片"}, 30),
    (("培根",), {"片"}, 20),
    (("火腿",), {"片"}, 20),
    (("起司", "乳酪", "起士"), {"片"}, 20),
    (("乾香菇", "香菇"), {"朵", "粒"}, 5),
    (("干貝",), {"粒", "顆"}, 10),
    (("蝦仁", "蝦子", "蝦"), {"尾", "隻"}, 10),
    (("花枝", "透抽", "小卷", "中卷"), {"尾", "隻"}, 200),
    (("魚",), {"尾", "條"}, 300),
    (("雞腿",), {"隻", "支"}, 250),
    (("雞翅",), {"支", "隻"}, 60),
    (("玉米筍",), {"支", "根", "條"}, 15),
    (("蘆筍",), {"支", "根", "條"}, 20),
    (("秋葵",), {"條", "根"}, 10),
    (("四季豆",), {"條", "根"}, 8),
    (("茄子",), {"條", "根"}, 150),
    (("海苔",), {"片", "張"}, 3),
    (("豆干", "豆乾"), {"片", "塊"}, 30),
    (("油豆腐",), {"塊", "個"}, 15),
    (("米血", "鴨血"), {"塊"}, 100),
    (("玉米",), {"根", "條"}, 200),
    (("地瓜", "番薯"), {"條", "個", "顆"}, 200),
    (("青椒", "甜椒", "彩椒"), {"顆", "個"}, 120),
    (("高麗菜", "包心菜"), {"顆", "個"}, 1000),
    (("花椰菜", "青花菜", "綠花椰"), {"朵", "小朵"}, 15),
]

# 找不到食材專屬對照時，各類計數單位的「概略估計」預設值（克）
DEFAULT_PIECE_WEIGHT = {
    "顆": 50, "個": 50, "粒": 10, "片": 10, "大片": 20, "小片": 5,
    "支": 20, "根": 20, "條": 20, "枝": 20,
    "塊": 100, "大塊": 150, "小塊": 30,
    "朵": 10, "小朵": 5,
    "隻": 100, "尾": 100,
    "包": 100, "小包": 30,
    "盒": 250, "罐": 300, "瓶": 500,
    "瓣": 5, "把": 30, "份": 150, "人份": 150,
    "張": 10, "段": 20, "小段": 10,
    "棵": 100, "株": 100, "球": 50, "副": 100, "組": 50,
    "葉": 2, "付": 150,
}

# 真的無法換算成重量的單位（長度、容器…）
NO_WEIGHT_UNITS = {"公分", "鍋"}


def parse_qty(q):
    """將數量字串解析成數值。回傳 (數值, 是否為模糊詞)。"""
    if q in VAGUE_GRAMS:
        return None, True
    if q in CN_NUM:
        return CN_NUM[q], False
    m = re.match(rf"^({NUM})\s*[/\\]\s*({NUM})$", q)
    if m:
        return float(m.group(1)) / float(m.group(2)), False
    try:
        return float(q), False
    except ValueError:
        return None, True


def tokenize_merge(line):
    """把字串依空白切開，並把「數字」與「單位」分開兩個 token 的狀況合併回同一個 token。"""
    raw_tokens = line.split()
    tokens = []
    i = 0
    while i < len(raw_tokens):
        t = raw_tokens[i]
        if BARE_QTY_RE.match(t) and i + 1 < len(raw_tokens) and BARE_UNIT_RE.match(raw_tokens[i + 1]):
            tokens.append(t + raw_tokens[i + 1])
            i += 2
        else:
            tokens.append(t)
            i += 1
    return tokens


def split_items(line):
    """把一行食材文字拆解成 [(食材名稱, 數量, 單位), ...]，可處理一行內含多個食材的情況。"""
    line = line.strip()
    if not line:
        return []
    if re.search(r"[【】\[\]]", line) and not re.search(QTY, line):
        return []  # 純段落標記（如【醃料】），不是食材
    tokens = tokenize_merge(line)
    results = []
    name_parts = []
    for tok in tokens:
        m = FULL_TOKEN_RE.match(tok)
        if m:
            name = "".join(name_parts).strip(" -、,，()（）")
            qty_raw, unit = m.group(1), m.group(2)
            results.append((name, qty_raw, unit))
            name_parts = []
        else:
            name_parts.append(tok)
    if name_parts:
        leftover = "".join(name_parts).strip(" -、,，()（）")
        if leftover:
            results.append((leftover, "", ""))
    return [r for r in results if r[0] or r[1]]


def lookup_piece_weight(name, unit):
    for keys, units, w in INGREDIENT_UNIT_WEIGHT:
        if unit in units and any(k in name for k in keys):
            return w, f"依常見食材估計（{keys[0]}類，每{unit}約{w}公克）"
    return None, None


def convert(name, qty_raw, unit):
    """回傳 (換算後公克數 or None, 換算依據說明)。"""
    if qty_raw == "" and not unit:
        return None, "缺少數量/單位資訊，無法換算"

    # 模糊份量：直接用固定估計值換算成公克
    if qty_raw in VAGUE_GRAMS:
        base = VAGUE_GRAMS[qty_raw]
        return round(base, 2), f"「{qty_raw}」無固定份量，以慣用估計值 {base} 公克 換算（僅供參考，請依實際使用量調整）"

    qty_val, is_vague = parse_qty(qty_raw)
    if is_vague or qty_val is None:
        return None, f"無法辨識的數量「{qty_raw}」"

    if not unit:
        return None, "缺少單位，無法換算"

    if unit in NO_WEIGHT_UNITS:
        return None, f"「{unit}」非重量單位，無法換算"

    if unit in DIRECT_FACTOR:
        grams = qty_val * DIRECT_FACTOR[unit]
        if unit in VOLUME_UNITS:
            note = "容積換算（假設密度≈1 g/ml，實際依食材密度略有差異）"
        elif unit in ("兩", "斤", "錢"):
            note = "傳統重量單位換算"
        else:
            note = "標準換算"
        return round(grams, 2), note

    # 計數單位：先查食材專屬重量表，查無則用預設概略值
    piece_w, note = lookup_piece_weight(name, unit)
    if piece_w is None:
        piece_w = DEFAULT_PIECE_WEIGHT.get(unit)
        note = f"查無食材專屬重量，以「每{unit}約{piece_w}公克」概略估計" if piece_w else None
    if piece_w is None:
        return None, f"未知單位「{unit}」，無法換算"

    return round(qty_val * piece_w, 2), note


def main():
    with open(INPUT_JSON, encoding="utf-8") as f:
        recipes = json.load(f)

    rows = []
    for r in recipes:
        dish = r.get("菜名", "")
        for cat_key in ("主要食材", "調味料"):
            for raw_item in r.get(cat_key, []):
                for name, qty_raw, unit in split_items(raw_item):
                    grams, note = convert(name, qty_raw, unit)
                    rows.append({
                        "菜名": dish,
                        "分類": cat_key,
                        "原始食材文字": raw_item,
                        "食材名稱": name,
                        "數量": qty_raw,
                        "單位": unit or "",
                        "換算公克": grams,
                        "換算依據/備註": note or "",
                    })

    total = len(rows)
    have = sum(1 for x in rows if x["換算公克"] is not None)
    print(f"共解析 {total} 筆食材資料，成功換算 {have} 筆，無法換算 {total - have} 筆。")

    wb = Workbook(write_only=True)

    ws0 = wb.create_sheet("說明")
    for line in [
        "食譜食材公克換算表 - 說明",
        "",
        "本表依「清洗後食譜.json」的 主要食材 / 調味料 欄位逐一解析並換算為公克，原始 JSON 檔案未被修改。",
        "",
        "換算方式：",
        "1. 已為公克/克/g/公斤/斤/兩/錢者：直接換算為公克。",
        "2. 容積單位（大匙、小匙、杯、CC/ml、碗等）：假設密度≈1 g/ml 換算，",
        "   1大匙=15g、1小匙=5g、1中匙=10g、1杯=200g、1大杯=300g、1小杯=100g、1碗=200g。",
        "   實際重量會因食材密度不同而略有落差，僅供估算參考。",
        "3. 計數單位（顆、個、片、根、包等）：優先用常見食材專屬重量估計，查無則用概略預設值（如1顆≈50g）。",
        "4. 少許/適量/些許/酌量等模糊份量：依下列慣用估計值換算為固定公克數（僅供參考）：",
        "   " + "、".join(f"{k}={v}g" for k, v in VAGUE_GRAMS.items()),
        "5. 公分、鍋等非重量單位：仍無法換算為公克。",
    ]:
        ws0.append([line])

    ws1 = wb.create_sheet("換算明細")
    ws1.append(["菜名", "分類", "原始食材文字", "食材名稱", "數量", "單位", "換算公克", "換算依據/備註"])
    for r in rows:
        ws1.append([
            r["菜名"], r["分類"], r["原始食材文字"], r["食材名稱"],
            r["數量"], r["單位"], r["換算公克"], r["換算依據/備註"],
        ])

    wb.save(OUTPUT_XLSX)
    print(f"已輸出：{OUTPUT_XLSX}")


if __name__ == "__main__":
    main()