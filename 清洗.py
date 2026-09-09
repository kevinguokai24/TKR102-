import json
import os
import re


def clean_title(title: str) -> str:
    """清理菜名，移除前後綴與編號括號"""
    title = re.sub(r"^【食譜】", "", title)
    title = re.sub(r":www\.ytower\.com\.tw$", "", title)
    # 移除標題末尾的序號如 (1)、(2) 或多餘空白
    title = re.sub(r"\(\d+\)$", "", title)
    return title.strip()


def parse_ingredients(text: str):
    """解析並分離主要食材與調味料"""
    # 依調味料標籤切分
    parts = re.split(r"【調\s*味\s*料】", text)

    # 移除食材區標籤（相容全形與半形空白）
    mat_part = re.sub(r"【材\s*料】", "", parts[0])
    season_part = parts[1] if len(parts) > 1 else ""

    def process_items(raw_str):
        items = []
        # 以頓號、逗號或換行切分
        tokens = re.split(r"[、，,\n]+", raw_str)
        for token in tokens:
            token = token.strip()
            if not token:
                continue
            # 移除英文字母/數字群組標籤 (如 A. B. C. 1. 2.)
            token = re.sub(r"^[A-Za-z0-9]\.\s*", "", token)
            # 移除多餘的括號分組提示 (如 內餡：、裝飾：、蛋汁：)
            token = re.sub(r"^.+?：\s*", "", token)
            # 將冒號替換為空格
            token = token.replace(":", " ").strip()

            # 處理楊桃食譜中常見的多項目黏在同一行 (空格隔開)
            sub_tokens = re.split(r"\s{2,}", token)
            for st in sub_tokens:
                st = st.strip()
                if st and st not in items:
                    items.append(st)
        return items

    main_ingredients = process_items(mat_part)
    seasonings = process_items(season_part)
    return main_ingredients, seasonings


def clean_steps(steps_text: str):
    """清理做法步驟，修復多餘序號"""
    if not steps_text:
        return []
    lines = steps_text.split("\n")
    cleaned_steps = []
    idx = 1
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 移除行首重複的序號標記 (如 "1. 1.", "1. ", "1 ")
        content = re.sub(r"^(\d+[\.\s]*)+", "", line).strip()
        if content:
            cleaned_steps.append(f"{idx}. {content}")
            idx += 1
    return cleaned_steps


def classify_cuisine(title: str, ingredients_text: str) -> str:
    """分類菜系：中式、韓式、西式、南洋、日式、其他"""
    # 韓式
    if any(k in title for k in ["韓式", "泡菜"]):
        return "韓式"

    # 日式
    if any(
        k in title
        for k in [
            "日式",
            "茶碗蒸",
            "玉子燒",
            "厚蛋燒",
            "味噌",
            "烏龍麵",
            "柴魚",
            "壽司",
            "照燒",
            "銅鑼燒",
            "鯛魚燒",
        ]
    ):
        return "日式"

    # 南洋
    if any(
        k in title
        for k in ["泰式", "南洋", "越式", "星洲", "咖哩", "冬蔭", "椰汁"]
    ) or any(k in ingredients_text for k in ["魚露", "香茅", "檸檬葉"]):
        return "南洋"

    # 西式 (烘焙、排餐、歐姆蛋、沙拉等)
    western_keywords = [
        "蛋糕",
        "布丁",
        "布蕾",
        "派",
        "馬芬",
        "餅乾",
        "舒芙蕾",
        "土司",
        "吐司",
        "三明治",
        "歐姆蛋",
        "美式",
        "法式",
        "義式",
        "烘蛋",
        "甜甜圈",
        "費南雪",
        "可頌",
        "德式",
        "年輪",
        "筆尖麵",
        "義大利麵",
        "焗烤",
        "牛粒",
        "蛋塔",
        "蛋捲",
        "捲心酥",
    ]
    if any(k in title for k in western_keywords):
        return "西式"

    # 中式 (家常炒蛋、菜脯蛋、皮蛋、蒸蛋、炒飯、滷蛋等)
    chinese_keywords = [
        "炒蛋",
        "菜脯蛋",
        "煎蛋",
        "蒸蛋",
        "皮蛋",
        "鹹蛋",
        "茶葉蛋",
        "滷蛋",
        "三色蛋",
        "炒飯",
        "蛋餅",
        "荷包蛋",
        "蛋花湯",
        "麻油蛋",
        "蛋炒",
        "糖心蛋",
        "鐵蛋",
        "溫泉蛋",
        "老燒蛋",
        "黑糖糕",
        "馬拉糕",
        "蒸糕",
        "雞絲麵",
        "煎餃",
        "水餃",
        "蒼蠅頭",
        "豆腐",
    ]
    if any(k in title for k in chinese_keywords):
        return "中式"

    return "其他"


def classify_diet(title: str, all_ingredients: list) -> str:
    """分類葷素：葷食、素食 (包含蛋素/蛋奶素料理判定為素食)"""
    # 葷食關鍵字（肉類、禽類、海鮮、動物性副產物）
    meat_keywords = [
        "肉",
        "牛",
        "豬",
        "雞",
        "鴨",
        "鵝",
        "羊",
        "魚",
        "蝦",
        "蟹",
        "海鮮",
        "透抽",
        "中卷",
        "花枝",
        "蚵",
        "培根",
        "火腿",
        "熱狗",
        "香腸",
        "絞肉",
        "肉燥",
        "肉絲",
        "肉末",
        "貢丸",
        "叉燒",
        "干貝",
        "吻仔魚",
        "魩仔魚",
        "柴魚",
        "柴魚素",
        "雞粉",
        "雞高湯",
        "高湯",
        "豬高湯",
        "鰹魚",
        "魚露",
        "蝦米",
        "蝦卵",
        "蜆",
        "吉利丁",
        "明膠",
        "蠔油",
    ]

    combined_text = title + " " + " ".join(all_ingredients)

    # 若含有任何葷食食材/高湯/肉品，判定為葷食
    for kw in meat_keywords:
        if kw in combined_text:
            return "葷食"

    return "素食"


def transform_data(raw_data):
    cleaned_data = []

    for item in raw_data:
        title = item.get("title", "")

        # 1. 過濾無效或編碼錯誤資料
        if not title or any(
            char in title for char in ["Ą", "Ć", "Ё", "Ã", "Â", "¤", "§", "»"]
        ):
            continue
        if not item.get("steps_text") or not item.get("ingredients_text"):
            continue

        clean_name = clean_title(title)
        ing_text = item.get("ingredients_text", "")
        ingredients, seasonings = parse_ingredients(ing_text)
        steps = clean_steps(item.get("steps_text", ""))

        if not steps or not ingredients:
            continue

        # 2. 分類菜系與葷素
        cuisine = classify_cuisine(clean_name, ing_text)
        diet_type = classify_diet(clean_name, ingredients + seasonings)

        recipe = {
            "菜名": clean_name,
            "菜系": cuisine,
            "葷素": diet_type,
            "主要食材": ingredients,
            "調味料": seasonings,
            "耗時": "20-30 分鐘",
            "特色": f"美味好上手的{clean_name}，口感豐富且作法清楚明瞭。",
            "做法": steps,
            "圖片": item.get("image_url", ""),
        }
        cleaned_data.append(recipe)

    return cleaned_data


def main():
    input_filename = "全部食譜.json"
    output_filename = "清洗後食譜.json"

    if not os.path.exists(input_filename):
        print(f"錯誤：找不到檔案 {input_filename}，請確認檔案路徑。")
        return

    with open(input_filename, "r", encoding="utf-8-sig") as f:
        raw_data = json.load(f)

    cleaned_data = transform_data(raw_data)

    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=4)

    print(
        f"清洗完成！共處理 {len(cleaned_data)} 筆有效食譜，已儲存至 {output_filename}。"
    )


if __name__ == "__main__":
    main()