import streamlit as st
import pandas as pd
import re
import json
import os
import random
import time
import math
from collections import defaultdict


# 頁面基本配置
st.set_page_config(page_title="今天吃啥咪！", layout="wide", page_icon="🍳")

# -------------------------------------------------------------
# 0. 全域樣式：固定卡片圖片尺寸（改用 st.container(key=...) 產生的真實
#    CSS class 來套用樣式，不再用「開標籤不關閉」的 HTML 技巧，避免破版）
# -------------------------------------------------------------
st.markdown(
    """
    <style>
    /* 凡是 key 結尾為 _imgbox 的容器，裡面的圖片一律固定大小、等比裁切置中 */
    div[class*="_imgbox"] img {
        width: 100% !important;
        height: 180px !important;
        object-fit: cover !important;
        border-radius: 10px !important;
        display: block !important;
    }

    /* 「查看完整食譜內容」按鈕外觀微調，看起來像可點擊的一列文字 */
    div[class*="_detailbtn"] button {
        width: 100% !important;
        text-align: left !important;
        justify-content: flex-start !important;
        color: #666 !important;
        font-weight: 400 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------------------
# 1. 食材熱量對照表 (每 100g 估算大卡 kcal) - 標準資料
#    註：以下為常見食材的概略營養資料，非官方精確數值，僅供參考。
# -------------------------------------------------------------
CALORIE_KCAL_PER_100G = {
    # ---- 原始表格 ----
    "牛腱肉": 125, "番茄": 19, "洋蔥": 40, "紅蘿蔔": 41, "雞腿肉": 180,
    "老薑": 80, "大蒜": 149, "九層塔": 28, "大蔥": 32, "白蝦": 99,
    "熟酪梨": 160, "羅曼生菜": 17, "小番茄": 18, "義大利麵": 150,
    "新鮮蛤蜊": 50, "嫩豆腐": 65, "豬五花肉片": 518, "金針菇": 37, "老泡菜": 20,
    # ---- 烘焙 / 常見基底食材 ----
    "奶油": 720, "牛奶": 60, "鮮奶": 60, "低筋麵粉": 364, "高筋麵粉": 364,
    "中筋麵粉": 364, "澄粉": 350, "泡打粉": 0, "小蘇打粉": 0, "塔塔粉": 0,
    "蛋黃": 322, "蛋白": 52, "全蛋": 143, "蛋": 143,
    "細砂糖": 387, "糖粉": 387, "砂糖": 387, "黑糖": 375, "冰糖": 387,
    "香草精": 12, "檸檬汁": 22, "玉米粉": 381, "地瓜粉": 340, "太白粉": 340,
    "奶油乳酪": 342, "動物性鮮奶油": 340, "植物性鮮奶油": 300, "煉乳": 321,
    "沙拉油": 884, "橄欖油": 884, "香油": 884, "麻油": 884, "黑麻油": 884,
    # ---- 米麵主食 ----
    "白飯": 130, "米飯": 130, "白米": 349, "糙米": 349, "糯米": 130,
    "吐司": 264, "麵包": 264, "冬粉": 90, "麵條": 138, "拉麵": 138,
    "義大利麵條": 150, "米粉": 109, "水餃皮": 275, "餛飩皮": 275,
    # ---- 常見肉類 / 海鮮 ----
    "豬肉": 242, "豬里肌肉": 143, "豬絞肉": 263, "雞肉": 167, "雞胸肉": 104,
    "雞翅": 197, "牛肉": 250, "牛絞肉": 254, "鴨肉": 240, "鵝肉": 258, "羊肉": 203,
    "鮭魚": 208, "鮪魚": 132, "虱目魚": 158, "鱸魚": 105, "吳郭魚": 96,
    "蝦仁": 90, "蝦子": 99, "蟹肉": 87, "花枝": 92, "透抽": 92, "小卷": 92,
    "魷魚": 92, "章魚": 82, "牡蠣": 65, "蛤蜊": 50, "淡菜": 172,
    # ---- 蔬菜 / 菇蕈 / 海菜 ----
    "青蔥": 32, "蔥": 32, "馬鈴薯": 77, "地瓜": 86, "芋頭": 128, "山藥": 108,
    "高麗菜": 25, "白菜": 16, "菠菜": 23, "空心菜": 20, "青江菜": 13,
    "小黃瓜": 15, "大黃瓜": 12, "冬瓜": 11, "苦瓜": 19, "南瓜": 66, "茄子": 25,
    "香菇": 34, "杏鮑菇": 33, "木耳": 21, "海帶": 12, "紫菜": 35, "海苔": 35,
    # ---- 水果 ----
    "蘋果": 52, "香蕉": 89, "鳳梨": 50, "芒果": 60, "葡萄": 69, "草莓": 32,
    "酪梨": 160, "檸檬": 29,
    # ---- 豆製品 / 蒟蒻 ----
    "豆腐": 65, "板豆腐": 88, "豆干": 192, "豆皮": 411, "腐皮": 411, "蒟蒻": 7,
    # ---- 堅果 / 種子 ----
    "花生": 567, "芝麻": 573, "腰果": 553, "杏仁": 579, "核桃": 654, "松子": 673,
    # ---- 其他常見加工品 ----
    "起司": 350, "乳酪": 350, "優格": 61, "蜂蜜": 304, "巧克力": 546,
    "可可粉": 228, "培根": 541, "火腿": 145, "香腸": 315, "豆瓣醬": 108,
}

# -------------------------------------------------------------
# 2. 三大篩選分類定義（菜系風格 / 食材分類 / 耗時區間）
# -------------------------------------------------------------

# 2-1 菜系風格選項與比對關鍵字（優先直接讀取資料的「菜系」「葷素」欄位，
#      查無精確欄位時才使用關鍵字猜測，以相容示範資料）
CUISINE_STYLE_OPTIONS = ["中式", "韓式", "西式", "南洋", "日式", "葷食", "素食"]

CUISINE_KEYWORDS = {
    "中式": ["中式", "中菜", "中餐", "台式"],
    "韓式": ["韓式", "韓"],
    "日式": ["日式", "日本", "和食", "日韓"],
    "西式": ["西式", "義式", "義大利", "法式", "歐式", "異國"],
    "南洋": ["南洋", "泰式", "越式", "馬來", "印尼", "星馬"],
}

# 判斷「葷食」的食材關鍵字（僅在資料沒有「葷素」欄位時作為備援判斷）
MEAT_KEYWORDS = ["牛", "豬", "雞", "鴨", "鵝", "羊", "魚", "蝦", "蟹",
                  "蛤", "蜊", "魷", "花枝", "蚵", "培根", "火腿", "肉"]

# 2-2 食材分類選項與比對關鍵字（依使用者指定順序）
INGREDIENT_CATEGORY_OPTIONS = [
    "蛋", "牛肉", "豬肉", "雞肉", "羊肉", "鴨肉", "鵝肉",
    "魚肉", "貝類", "魷魚/花枝", "蝦/蟹",
    "豆腐", "蒟蒻", "根莖類", "葉菜類", "瓜果類", "水果類", "海菜/菇蕈", "種子/核果",
    "中式點心", "西式點心",
    "米飯/米食", "豆干/腐皮", "麵食/麵粉"
]

INGREDIENT_CATEGORY_KEYWORDS = {
    "蛋": ["蛋"],
    "牛肉": ["牛"],
    "豬肉": ["豬"],
    "雞肉": ["雞"],
    "羊肉": ["羊"],
    "鴨肉": ["鴨"],
    "鵝肉": ["鵝"],
    "魚肉": ["魚"],
    "貝類": ["蛤", "蜊", "蚵", "淡菜", "干貝", "貝"],
    "魷魚/花枝": ["魷魚", "花枝", "透抽", "小卷"],
    "蝦/蟹": ["蝦", "蟹"],
    "豆腐": ["豆腐"],
    "蒟蒻": ["蒟蒻"],
    "根莖類": ["蘿蔔", "馬鈴薯", "地瓜", "芋頭", "薑", "山藥", "牛蒡"],
    "葉菜類": ["生菜", "菠菜", "高麗菜", "白菜", "地瓜葉", "空心菜", "青江菜", "萵苣"],
    "瓜果類": ["番茄", "南瓜", "小黃瓜", "大黃瓜", "冬瓜", "苦瓜", "茄子"],
    "水果類": ["蘋果", "香蕉", "檸檬", "酪梨", "鳳梨", "芒果", "葡萄", "草莓"],
    "海菜/菇蕈": ["海帶", "紫菜", "金針菇", "香菇", "杏鮑菇", "木耳", "海苔", "菇"],
    "種子/核果": ["核桃", "杏仁", "腰果", "花生", "芝麻", "松子"],
    "中式點心": ["水餃", "包子", "饅頭", "湯圓", "燒賣", "蘿蔔糕"],
    "西式點心": ["蛋糕", "餅乾", "麵包", "塔", "馬芬", "可頌"],
    "米飯/米食": ["米飯", "白飯", "米粉", "粥", "米糠", "糯米"],
    "豆干/腐皮": ["豆干", "腐皮", "豆皮"],
    "麵食/麵粉": ["麵", "麵粉", "水餃皮", "餃子皮", "餛飩皮"],
}

# 食材分類 -> 每 100g 概略估算熱量（查無精確資料時的備援估值）
CATEGORY_DEFAULT_KCAL = {
    "蛋": 150, "牛肉": 250, "豬肉": 270, "雞肉": 200, "羊肉": 220,
    "鴨肉": 230, "鵝肉": 240, "魚肉": 120, "貝類": 80, "魷魚/花枝": 90,
    "蝦/蟹": 95, "豆腐": 65, "蒟蒻": 10, "根莖類": 80, "葉菜類": 20,
    "瓜果類": 25, "水果類": 55, "海菜/菇蕈": 30, "種子/核果": 580,
    "中式點心": 250, "西式點心": 350, "米飯/米食": 130, "豆干/腐皮": 200,
    "麵食/麵粉": 300,
}
GENERIC_FALLBACK_KCAL = 100  # 完全無法歸類時的粗略預設值

# 2-3 耗時區間選項
TIME_BUCKET_OPTIONS = ["全部時段", "10分鐘內 (1-9分)", "20-30分鐘", "30分鐘以上"]

# -------------------------------------------------------------
# 3. 資料載入：清洗後食譜 + 食材公克換算對照
# -------------------------------------------------------------
@st.cache_data
def load_food_data(file_path="清洗後食譜.json"):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return pd.DataFrame(data)

    # 若無清洗後的 JSON 檔案，使用預設示範資料
    fallback_data = [
        {
            "菜名": "番茄牛肉燉湯", "菜系": "異國料理",
            "主要食材": ["牛腱肉 250g", "番茄 200g", "洋蔥 100g", "紅蘿蔔 100g"],
            "調味料": ["月桂葉 2片", "黑胡椒 少許", "海鹽 1茶匙", "橄欖油 10ml"],
            "耗時": "60 分鐘", "特色": "濃郁酸甜，富含茄紅素，暖胃滋補首選。",
            "做法": [
                "1. 牛腱肉切大塊，汆燙去除血水後備用。",
                "2. 洋蔥、紅蘿蔔切塊，番茄切丁備用。",
                "3. 熱鍋加橄欖油炒香洋蔥，加入番茄炒至出汁。",
                "4. 放入牛腱、紅蘿蔔、月桂葉與清水，大火煮滾後轉小火燉煮50分鐘。",
                "5. 起鍋前加入鹽與黑胡椒調味即可享用。"
            ],
            "圖片": "https://images.unsplash.com/photo-1547592166-23ac45744acd?w=600&q=80"
        },
        {
            "菜名": "台式經典三杯雞", "菜系": "中式料理",
            "主要食材": ["雞腿肉 300g", "老薑 50g", "大蒜 40g", "九層塔 20g"],
            "調味料": ["黑麻油 20ml", "米酒 30ml", "醬油 30ml", "冰糖 15g"],
            "耗時": "25 分鐘", "特色": "香氣四溢、下飯神器，台菜經典代表作。",
            "做法": [
                "1. 雞腿肉剁塊洗淨擦乾；老薑切薄片，大蒜去皮整顆備用。",
                "2. 鍋中倒入黑麻油，小火將老薑片煸至邊緣微捲。",
                "3. 放入蒜粒與雞腿肉，大火翻炒至雞肉表面微焦黃。",
                "4. 淋入米酒、醬油及冰糖，煮滾後蓋鍋悶煮約 10 分鐘至醬汁濃稠收乾。",
                "5. 關火加入大把九層塔，翻炒數秒拌勻後即可盛盤。"
            ],
            "圖片": "https://images.unsplash.com/photo-1598515214211-89d3c73ae83b?w=600&q=80"
        },
        {
            "菜名": "日式照燒雞肉串", "菜系": "日韓料理",
            "主要食材": ["雞腿肉 250g", "大蔥 80g"],
            "調味料": ["日式醬油 20ml", "味醂 20ml", "清酒 15ml", "砂糖 10g"],
            "耗時": "20 分鐘", "特色": "鹹甜濃郁，居酒屋必備下酒菜。",
            "做法": [
                "1. 雞腿肉切一口大小，大蔥切成約3公分長段。",
                "2. 使用竹籤依序串入雞肉與蔥段。",
                "3. 將醬油、味醂、清酒、砂糖調勻為照燒醬汁。",
                "4. 熱平底鍋少油，將串燒兩面煎至熟透微焦。",
                "5. 刷上照燒醬汁，小火煎至醬汁冒泡並均勻包裹肉串即可。"
            ],
            "圖片": "https://images.unsplash.com/photo-1532550907401-a500c9a57435?w=600&q=80"
        },
        {
            "菜名": "酪梨鮮蝦低卡沙拉", "菜系": "健康輕食",
            "主要食材": ["白蝦 150g", "熟酪梨 100g", "羅曼生菜 100g", "小番茄 80g"],
            "調味料": ["初榨橄欖油 10ml", "檸檬汁 15ml", "海鹽 少許", "黑胡椒 少許"],
            "耗時": "15 分鐘", "特色": "高蛋白、優質好油脂，減脂健身族群首選。",
            "做法": [
                "1. 白蝦去殼去腸泥，川燙熟後泡冰水冰鎮瀝乾。",
                "2. 羅曼生菜洗淨瀝乾撕成片狀，小番茄對半切，酪梨切丁。",
                "3. 橄欖油、檸檬汁、鹽巴、黑胡椒調勻成沙拉油醋醬汁。",
                "4. 將所有食材盛入沙拉碗中，淋上醬汁輕輕拌勻即可食用。"
            ],
            "圖片": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=600&q=80"
        },
        {
            "菜名": "義式蒜香白酒蛤蜊麵", "菜系": "異國料理",
            "主要食材": ["義大利麵 100g", "新鮮蛤蜊 250g", "大蒜 30g"],
            "調味料": ["白酒 50ml", "初榨橄欖油 15ml", "海鹽 少許", "巴西里碎葉 少許"],
            "耗時": "25 分鐘", "特色": "鮮甜海味搭配蒜香與清爽白酒香氣。",
            "做法": [
                "1. 滾水加鹽，放入義大利麵煮至八分熟撈起備用。",
                "2. 平底鍋倒入橄欖油，小火爆香蒜片。",
                "3. 轉大火加入吐沙洗淨的蛤蜊與白酒，蓋上鍋蓋燜至蛤蜊全開口後先撈出。",
                "4. 放入煮好的義大利麵與少許煮麵水拌炒乳化收汁。",
                "5. 放回蛤蜊，撒上新鮮巴西里碎末拌勻即可盛盤。"
            ],
            "圖片": "https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=600&q=80"
        },
        {
            "菜名": "韓式泡菜豆腐鍋", "菜系": "日韓料理",
            "主要食材": ["老泡菜 150g", "嫩豆腐 150g", "豬五花肉片 100g", "金針菇 100g"],
            "調味料": ["韓式辣醬 15g", "韓式辣粉 5g", "醬油 10ml", "蒜泥 10g", "香油 5ml"],
            "耗時": "20 分鐘", "特色": "酸辣過癮，暖身開胃，一鍋搞定豐富一餐。",
            "做法": [
                "1. 陶鍋中倒入香油，炒香五花肉片至表面出油變色。",
                "2. 加入老泡菜炒出酸香氣味，加入蒜泥、韓式辣醬炒勻。",
                "3. 倒入高湯或清水煮滾，轉中火加入金針菇與嫩豆腐切塊。",
                "4. 蓋鍋慢滾 8 分鐘入味，撒上辣粉與醬油調味後即可上桌。"
            ],
            "圖片": "https://images.unsplash.com/photo-1583032015879-c5c56c2e8b01?w=600&q=80"
        }
    ]
    return pd.DataFrame(fallback_data)


@st.cache_data
def build_gram_normalized_lookup(_recipe_names, conv_path="食譜食材公克換算.json"):
    """
    讀取「食譜食材公克換算.json」，並依「菜名 + 同名出現順序」與清洗後食譜對齊，
    回傳一個 list（長度與食譜資料相同），每個元素是該道菜已換算為公克的
    「主要食材」清單；若無法對齊則回傳 None，計算熱量時會退回原始文字解析。
    """
    n = len(_recipe_names)
    aligned = [None] * n
    if not os.path.exists(conv_path):
        return aligned

    with open(conv_path, "r", encoding="utf-8-sig") as f:
        conv = json.load(f)

    rec_groups = defaultdict(list)
    for i, name in enumerate(_recipe_names):
        rec_groups[name].append(i)

    conv_groups = defaultdict(list)
    for i, d in enumerate(conv):
        conv_groups[d.get("菜名")].append(i)

    for name, idxs_r in rec_groups.items():
        idxs_c = conv_groups.get(name, [])
        if len(idxs_r) == len(idxs_c):
            for a, b in zip(idxs_r, idxs_c):
                aligned[a] = conv[b].get("主要食材")

    return aligned


df = load_food_data()
df["_calc_ingredients"] = build_gram_normalized_lookup(tuple(df["菜名"].tolist()))

HAS_CUISINE_FIELD = "菜系" in df.columns
HAS_VEG_FIELD = "葷素" in df.columns


# -------------------------------------------------------------
# 4. 篩選判斷函式
# -------------------------------------------------------------
def get_cuisine_tags(row):
    """判斷該道菜符合哪些「菜系風格」標籤，優先使用資料本身的精確欄位"""
    tags = set()

    cuisine_val = str(row.get("菜系", "")).strip()
    if cuisine_val in CUISINE_STYLE_OPTIONS:
        # 資料本身的「菜系」欄位就是我們要的分類（例如：中式/韓式/西式/南洋/日式）
        tags.add(cuisine_val)
    else:
        for tag, keywords in CUISINE_KEYWORDS.items():
            if any(kw in cuisine_val for kw in keywords):
                tags.add(tag)

    veg_val = str(row.get("葷素", "")).strip()
    if veg_val in ("葷食", "素食"):
        tags.add(veg_val)
    else:
        ingredients_text = " ".join(row.get("主要食材", []))
        if any(kw in ingredients_text for kw in MEAT_KEYWORDS):
            tags.add("葷食")
        else:
            tags.add("素食")
    return tags


def get_ingredient_category_tags(row):
    """依 主要食材 欄位比對關鍵字，找出符合哪些食材分類"""
    tags = set()
    ingredients_text = " ".join(row.get("主要食材", []))
    for category, keywords in INGREDIENT_CATEGORY_KEYWORDS.items():
        if any(kw in ingredients_text for kw in keywords):
            tags.add(category)
    return tags


def get_time_minutes_range(duration_str):
    nums = [int(n) for n in re.findall(r"\d+", str(duration_str))]
    if not nums:
        return None
    return (min(nums), max(nums))


def matches_time_bucket(duration_str, bucket_label):
    if bucket_label == "全部時段":
        return True
    rng = get_time_minutes_range(duration_str)
    if rng is None:
        return False
    lo, hi = rng
    if bucket_label.startswith("10分鐘內"):
        return hi <= 9
    if bucket_label.startswith("20-30"):
        return lo >= 20 and hi <= 30
    if bucket_label.startswith("30分鐘以上"):
        return hi > 30 or lo > 30
    return True


# -------------------------------------------------------------
# 5. 卡路里計算：從「食譜食材公克換算」取得精準公克數，
#    再比對熱量對照表 / 食材分類推估值換算卡路里
# -------------------------------------------------------------
def extract_grams(ingredient_text):
    """從已換算過的食材文字（例如「奶油 50公克」）取出公克數"""
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(公斤|kg|公克|克|g|cc|ml|毫升)",
        ingredient_text, re.IGNORECASE
    )
    if not match:
        return None
    weight = float(match.group(1))
    unit = match.group(2).lower()
    if unit in ("公斤", "kg"):
        weight *= 1000
    return weight


def extract_ingredient_name(ingredient_text):
    """取出食材名稱（去除後面的數量與單位）"""
    name = re.split(r"\d", ingredient_text)[0].strip()
    return name if name else ingredient_text.strip()


def estimate_kcal_per_100g(name):
    """回傳 (每100g熱量, 估算依據說明)"""
    if name in CALORIE_KCAL_PER_100G:
        return CALORIE_KCAL_PER_100G[name], "標準資料"

    for category, keywords in INGREDIENT_CATEGORY_KEYWORDS.items():
        if any(kw in name for kw in keywords):
            return CATEGORY_DEFAULT_KCAL.get(category, GENERIC_FALLBACK_KCAL), f"類別推估（{category}）"

    return GENERIC_FALLBACK_KCAL, "粗略推估"


def calculate_calories(display_ingredients, calc_ingredients=None):
    """
    display_ingredients: 畫面上顯示用的原始食材文字清單
    calc_ingredients: 若有「食譜食材公克換算」對齊到的公克化清單，優先使用它來計算
                       （較準確，涵蓋「少許/適量/大匙/顆」等模糊單位）
    """
    source_list = calc_ingredients if calc_ingredients else display_ingredients

    results = []
    total_kcal = 0

    for item in source_list:
        grams = extract_grams(item)
        name = extract_ingredient_name(item)

        if grams is None or not name:
            results.append({
                "食材": item, "用量": "無法解析",
                "每100g熱量": "-", "估算依據": "-", "估算卡路里": "-"
            })
            continue

        kcal_per_100g, basis = estimate_kcal_per_100g(name)
        cal = round((grams / 100.0) * kcal_per_100g, 1)
        total_kcal += cal

        results.append({
            "食材": name,
            "用量": f"{grams:g}g",
            "每100g熱量": f"{kcal_per_100g} kcal",
            "估算依據": basis,
            "估算卡路里": f"{cal} kcal"
        })

    return results, round(total_kcal, 1)


def render_full_recipe_details(row, key_prefix):
    """顯示完整食譜內容：食材/調味料、做法、卡路里分析（點開才會看到）"""
    with st.expander("🛒 查看食材與調味料清單"):
        st.markdown("**【主要食材】**")
        st.write("、".join(row["主要食材"]))
        st.markdown("**【調味料】**")
        st.write("、".join(row["調味料"]) if row["調味料"] else "（無額外調味料資料）")

    with st.expander("👨‍🍳 查看料理步驟 / 做法"):
        for step in row["做法"]:
            st.write(step)

    with st.expander("🔥 檢視食材卡路里分析"):
        cal_breakdown, total_cal = calculate_calories(row["主要食材"], row.get("_calc_ingredients"))
        st.dataframe(pd.DataFrame(cal_breakdown), hide_index=True, use_container_width=True)
        st.metric(label="主要食材估算總熱量", value=f"{total_cal} kcal")
        st.caption(
            "註：公克數優先採用「食譜食材公克換算」資料（已將少許、適量、大匙、顆等模糊單位換算為公克）；"
            "熱量部分「標準資料」為常見食材對照值，「類別推估」「粗略推估」則是查無精確資料時依食材分類概略估算，"
            "僅供參考，實際熱量會因品種、烹調方式與調味料而有落差。"
        )


@st.dialog("料理詳情", width="large")
def show_recipe_dialog(row, key_prefix):
    """點擊「查看完整食譜內容」時彈出的完整食譜內容視窗，含圖片"""
    with st.container(key=f"{key_prefix}_dialog_imgbox"):
        st.image(row["圖片"], use_container_width=True)
    st.subheader(row["菜名"])
    st.caption(f"風格：{row['菜系']} ｜ 烹飪時間：{row['耗時']}")
    st.write(f"**料理特色**：{row['特色']}")
    st.markdown("---")
    render_full_recipe_details(row, key_prefix=f"dialog_{key_prefix}")


# -------------------------------------------------------------
# 6. 側邊欄（快速搜尋 + LINE 好友資訊）
# -------------------------------------------------------------
def _reset_all_filters():
    st.session_state["search_keyword_input"] = ""
    st.session_state["cuisine_filter"] = []
    st.session_state["category_filter"] = []
    st.session_state["time_bucket_filter"] = None
    st.session_state["list_page"] = 0


with st.sidebar:
    st.header("🔍 快速搜尋")
    search_keyword = st.text_input(
        "輸入食材、菜名或調味料搜尋美味料理：",
        "",
        placeholder="例如：雞肉、豆腐、義大利麵、蒜香",
        key="search_keyword_input"
    )

    st.button("🍽️ 顯示全部料理", use_container_width=True, on_click=_reset_all_filters)

    st.markdown("---")
    st.markdown("### 💬 加入 LINE 好友")
    st.caption("天天推播今日特選食譜與健康低卡熱量分析！")
    LINE_URL = "https://line.me/R/ti/p/@your_line_id"
    qr_code_url = "https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=" + LINE_URL
    st.image(qr_code_url, caption="掃描 QR Code 加好友", width=160)
    st.link_button("👉 點我直接加入 LINE 好友", LINE_URL, use_container_width=True)

# -------------------------------------------------------------
# 7. 主頁面標題與置中篩選區
# -------------------------------------------------------------
st.title("🍳 今天吃啥咪！")

st.subheader("🎛️ 篩選條件")
_, filter_col, _ = st.columns([1, 6, 1])
with filter_col:
    selected_cuisines = st.multiselect(
        "① 菜系風格",
        options=CUISINE_STYLE_OPTIONS,
        default=[],
        placeholder="不選代表顯示全部菜系",
        key="cuisine_filter"
    )
    selected_categories = st.multiselect(
        "② 食材分類",
        options=INGREDIENT_CATEGORY_OPTIONS,
        default=[],
        placeholder="不選代表顯示全部食材",
        key="category_filter"
    )
    selected_time_bucket = st.radio(
        "③ 烹飪耗時",
        options=TIME_BUCKET_OPTIONS,
        index=None,
        horizontal=True,
        key="time_bucket_filter"
    )

st.markdown("---")

# -------------------------------------------------------------
# 8. 輪播控制 Session State（固定抽取 15 道菜做為精選輪播池）
# -------------------------------------------------------------
CAROUSEL_SIZE = 15
CAROUSEL_INTERVAL_SECONDS = 4

if "carousel_pool_indices" not in st.session_state:
    pool_size = min(CAROUSEL_SIZE, len(df))
    st.session_state.carousel_pool_indices = random.sample(range(len(df)), pool_size) if pool_size > 0 else []

carousel_df = df.iloc[st.session_state.carousel_pool_indices].reset_index(drop=True)

if "carousel_index" not in st.session_state:
    st.session_state.carousel_index = 0
if "carousel_last_tick" not in st.session_state:
    st.session_state.carousel_last_tick = time.time()


def _set_carousel_index(new_idx, n):
    if n <= 0:
        return
    st.session_state.carousel_index = new_idx % n
    st.session_state.carousel_last_tick = time.time()


is_default_view = (
    not selected_cuisines
    and not selected_categories
    and selected_time_bucket in (None, "全部時段")
    and not search_keyword.strip()
)

if is_default_view and len(carousel_df) > 0:

    @st.fragment(run_every=CAROUSEL_INTERVAL_SECONDS)
    def render_carousel():
        n = len(carousel_df)

        if time.time() - st.session_state.carousel_last_tick >= CAROUSEL_INTERVAL_SECONDS:
            _set_carousel_index(st.session_state.carousel_index + 1, n)

        st.subheader("🌟 主廚今日精選輪播推薦")

        c_btn1, c_card, c_btn2 = st.columns([0.1, 0.8, 0.1])

        with c_btn1:
            st.write("")
            st.write("")
            st.write("")
            if st.button("◀", key="prev_carousel", use_container_width=True):
                _set_carousel_index(st.session_state.carousel_index - 1, n)

        current_item = carousel_df.iloc[st.session_state.carousel_index]
        with c_card:
            col_img, col_info = st.columns([1, 1.2])
            with col_img:
                st.image(current_item["圖片"], use_container_width=True)
            with col_info:
                st.markdown(f"### 【推薦】{current_item['菜名']}")
                st.caption(f"分類：{current_item['菜系']} ｜ 烹飪時間：{current_item['耗時']}")
                st.write(current_item["特色"])
                with st.expander("👀 查看完整食譜內容"):
                    st.caption(f"輪播第 {st.session_state.carousel_index + 1} / {n} 道精選料理")
                    render_full_recipe_details(current_item, key_prefix=f"carousel_{st.session_state.carousel_index}")

        with c_btn2:
            st.write("")
            st.write("")
            st.write("")
            if st.button("▶", key="next_carousel", use_container_width=True):
                _set_carousel_index(st.session_state.carousel_index + 1, n)

    render_carousel()
    st.markdown("---")

# -------------------------------------------------------------
# 9. 資料篩選邏輯（菜系風格 + 食材分類 + 耗時 + 關鍵字多重比對）
# -------------------------------------------------------------
filtered_df = df.copy()

if selected_cuisines:
    filtered_df = filtered_df[filtered_df.apply(
        lambda row: bool(get_cuisine_tags(row) & set(selected_cuisines)), axis=1
    )]

if selected_categories:
    filtered_df = filtered_df[filtered_df.apply(
        lambda row: bool(get_ingredient_category_tags(row) & set(selected_categories)), axis=1
    )]

if selected_time_bucket and selected_time_bucket != "全部時段":
    filtered_df = filtered_df[filtered_df["耗時"].apply(
        lambda d: matches_time_bucket(d, selected_time_bucket)
    )]

if search_keyword.strip():
    kw = search_keyword.strip().lower()

    def matches_search(row):
        if kw in row["菜名"].lower():
            return True
        if any(kw in ing.lower() for ing in row["主要食材"]):
            return True
        if any(kw in s.lower() for s in row["調味料"]):
            return True
        return False

    filtered_df = filtered_df[filtered_df.apply(matches_search, axis=1)]

# -------------------------------------------------------------
# 10. 料理清單展示（含分頁，避免資料量過大時卡頓）
#     卡片顯示：圖片（固定尺寸）、菜名、風格/耗時、料理特色、
#     「👀 查看完整食譜內容」按鈕 -> 點擊後彈出 Dialog（含圖片＋完整內容）
# -------------------------------------------------------------

PAGE_SIZE = 12
current_filter_signature = (
    tuple(sorted(selected_cuisines)),
    tuple(sorted(selected_categories)),
    selected_time_bucket,
    search_keyword.strip().lower(),
)
if st.session_state.get("last_filter_signature") != current_filter_signature:
    st.session_state.last_filter_signature = current_filter_signature
    st.session_state.list_page = 0
if "list_page" not in st.session_state:
    st.session_state.list_page = 0

if filtered_df.empty:
    st.warning("查無符合條件的料理，請更換關鍵字或調整篩選條件重試！")
else:
    total_pages = max(1, math.ceil(len(filtered_df) / PAGE_SIZE))
    st.session_state.list_page = min(st.session_state.list_page, total_pages - 1)
    start = st.session_state.list_page * PAGE_SIZE
    page_df = filtered_df.iloc[start:start + PAGE_SIZE]

    for i in range(0, len(page_df), 2):
        row_cols = st.columns(2)
        batch = page_df.iloc[i:i + 2]

        for idx, (_, row) in enumerate(batch.iterrows()):
            with row_cols[idx]:
                card_key = f"list_{start + i}_{idx}"

                # 圖片：固定尺寸顯示
                with st.container(key=f"{card_key}_imgbox"):
                    st.image(row["圖片"], use_container_width=True)

                st.subheader(row["菜名"])
                st.caption(f"風格：{row['菜系']} ｜ 烹飪時間：{row['耗時']}")
                st.write(f"**料理特色**：{row['特色']}")

                with st.container(key=f"{card_key}_detailbtn"):
                    open_detail = st.button(
                        "👀 查看完整食譜內容", key=f"{card_key}_detail_btn", use_container_width=True
                    )
                if open_detail:
                    show_recipe_dialog(row, card_key)

                st.markdown("")

    if total_pages > 1:
        st.markdown("---")
        p_prev, p_mid, p_next = st.columns([1, 2, 1])
        with p_prev:
            if st.button("⬅️ 上一頁", disabled=st.session_state.list_page <= 0, use_container_width=True):
                st.session_state.list_page -= 1
                st.rerun()
        with p_mid:
            st.markdown(
                f"<div style='text-align:center;'>第 {st.session_state.list_page + 1} / {total_pages} 頁</div>",
                unsafe_allow_html=True
            )
        with p_next:
            if st.button("下一頁 ➡️", disabled=st.session_state.list_page >= total_pages - 1, use_container_width=True):
                st.session_state.list_page += 1
                st.rerun()