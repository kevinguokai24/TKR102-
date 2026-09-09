import streamlit as st
import pandas as pd
import re
import json
import os


# 頁面基本配置
st.set_page_config(page_title="今天吃啥咪！", layout="wide", page_icon="🍳")

# -------------------------------------------------------------
# 1. 食材單位卡路里對照表 (每 100g 估算大卡 kcal)
# -------------------------------------------------------------
CALORIE_DB = {
    "牛腱肉": 125,
    "番茄": 19,
    "洋蔥": 40,
    "紅蘿蔔": 41,
    "雞腿肉": 180,
    "老薑": 80,
    "大蒜": 149,
    "九層塔": 28,
    "大蔥": 32,
    "白蝦": 99,
    "熟酪梨": 160,
    "羅曼生菜": 17,
    "小番茄": 18,
    "義大利麵": 150,
    "新鮮蛤蜊": 50,
    "嫩豆腐": 65,
    "豬五花肉片": 518,
    "金針菇": 37,
    "老泡菜": 20
}

# -------------------------------------------------------------
# 2. 模擬清洗後的完整美食資料庫
# -------------------------------------------------------------
@st.cache_data
def load_food_data(file_path="清洗後食譜.json"):
    # 1. 檢查是否存在清洗後的 JSON 檔案
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)  # 注意：是 json.load 不是 st.json.load
        return pd.DataFrame(data)
    # 2. 若無清洗後的 JSON 檔案，使用預設資料
    fallback_data = [
        {
            "菜名": "番茄牛肉燉湯",
            "菜系": "異國料理",
            "主要食材": ["牛腱肉 250g", "番茄 200g", "洋蔥 100g", "紅蘿蔔 100g"],
            "調味料": ["月桂葉 2片", "黑胡椒 少許", "海鹽 1茶匙", "橄欖油 10ml"],
            "耗時": "60 分鐘",
            "特色": "濃郁酸甜，富含茄紅素，暖胃滋補首選。",
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
            "菜名": "台式經典三杯雞",
            "菜系": "中式料理",
            "主要食材": ["雞腿肉 300g", "老薑 50g", "大蒜 40g", "九層塔 20g"],
            "調味料": ["黑麻油 20ml", "米酒 30ml", "醬油 30ml", "冰糖 15g"],
            "耗時": "25 分鐘",
            "特色": "香氣四溢、下飯神器，台菜經典代表作。",
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
            "菜名": "日式照燒雞肉串",
            "菜系": "日韓料理",
            "主要食材": ["雞腿肉 250g", "大蔥 80g"],
            "調味料": ["日式醬油 20ml", "味醂 20ml", "清酒 15ml", "砂糖 10g"],
            "耗時": "20 分鐘",
            "特色": "鹹甜濃郁，居酒屋必備下酒菜。",
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
            "菜名": "酪梨鮮蝦低卡沙拉",
            "菜系": "健康輕食",
            "主要食材": ["白蝦 150g", "熟酪梨 100g", "羅曼生菜 100g", "小番茄 80g"],
            "調味料": ["初榨橄欖油 10ml", "檸檬汁 15ml", "海鹽 少許", "黑胡椒 少許"],
            "耗時": "15 分鐘",
            "特色": "高蛋白、優質好油脂，減脂健身族群首選。",
            "做法": [
                "1. 白蝦去殼去腸泥，川燙熟後泡冰水冰鎮瀝乾。",
                "2. 羅曼生菜洗淨瀝乾撕成片狀，小番茄對半切，酪梨切丁。",
                "3. 橄欖油、檸檬汁、鹽巴、黑胡椒調勻成沙拉油醋醬汁。",
                "4. 將所有食材盛入沙拉碗中，淋上醬汁輕輕拌勻即可食用。"
            ],
            "圖片": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=600&q=80"
        },
        {
            "菜名": "義式蒜香白酒蛤蜊麵",
            "菜系": "異國料理",
            "主要食材": ["義大利麵 100g", "新鮮蛤蜊 250g", "大蒜 30g"],
            "調味料": ["白酒 50ml", "初榨橄欖油 15ml", "海鹽 少許", "巴西里碎葉 少許"],
            "耗時": "25 分鐘",
            "特色": "鮮甜海味搭配蒜香與清爽白酒香氣。",
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
            "菜名": "韓式泡菜豆腐鍋",
            "菜系": "日韓料理",
            "主要食材": ["老泡菜 150g", "嫩豆腐 150g", "豬五花肉片 100g", "金針菇 100g"],
            "調味料": ["韓式辣醬 15g", "韓式辣粉 5g", "醬油 10ml", "蒜泥 10g", "香油 5ml"],
            "耗時": "20 分鐘",
            "特色": "酸辣過癮，暖身開胃，一鍋搞定豐富一餐。",
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

df = load_food_data()

# -------------------------------------------------------------
# 3. 正規表達式：解析食材重量並計算卡路里
# -------------------------------------------------------------
def calculate_calories(ingredient_list):
    """
    透過正規表達式提取重量 (g / 克 / ml / 毫升)，
    並依照每 100g 的卡路里計算各食材熱量。
    """
    results = []
    total_kcal = 0

    for item in ingredient_list:
        # 正規化比對：找尋品名與數量 (例如: "牛腱肉 250g")
        match = re.search(r"(\d+(?:\.\d+)?)\s*(g|克|ml|毫升)", item, re.IGNORECASE)
        matched_ingredient = None
        for name in CALORIE_DB:
            if name in item:
                matched_ingredient = name
                break
        
        if match and matched_ingredient:
            weight = float(match.group(1))
            unit_kcal = CALORIE_DB[matched_ingredient]
            cal = round((weight / 100.0) * unit_kcal, 1)
            total_kcal += cal
            results.append({
                "食材": matched_ingredient,
                "用量": f"{weight}g",
                "每100g熱量": f"{unit_kcal} kcal",
                "估算卡路里": f"{cal} kcal"
            })
        else:
            results.append({
                "食材": item,
                "用量": "適量",
                "每100g熱量": "參考標準",
                "估算卡路里": "-"
            })
            
    return results, round(total_kcal, 1)

# -------------------------------------------------------------
# 4. 側邊欄（移除用餐時段與難度，僅保留菜系風格）
# -------------------------------------------------------------
with st.sidebar:
    st.header("🍽️ 找料理選單")
    cuisine_options = ["全部菜系"] + sorted(df["菜系"].unique().tolist())
    selected_cuisine = st.selectbox("選擇菜系風格：", cuisine_options)
    
    st.markdown("---")
    st.markdown("### 💬 加入 LINE 好友")
    st.caption("天天推播今日特選食譜與健康低卡熱量分析！")
    LINE_URL = "https://line.me/R/ti/p/@your_line_id"
    qr_code_url = "https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=" + LINE_URL
    st.image(qr_code_url, caption="掃描 QR Code 加好友", width=160)
    st.link_button("👉 點我直接加入 LINE 好友", LINE_URL, use_container_width=True)

# -------------------------------------------------------------
# 5. 主頁面：關鍵字搜尋與首頁輪播控制
# -------------------------------------------------------------
st.title("🍳 智能美味生活館")

# 關鍵字搜尋框
search_keyword = st.text_input("🔍 輸入食材、菜名或調味料搜尋美味料理（如：雞肉、豆腐、義大利麵、蒜香）：", "")

# 輪播控制 Session State
if "carousel_index" not in st.session_state:
    st.session_state.carousel_index = 0

# 當使用者未篩選且無輸入關鍵字時，呈現精選輪播區塊
is_default_view = (selected_cuisine == "全部菜系" and not search_keyword.strip())

if is_default_view:
    st.subheader("🌟 主廚今日精選輪播推薦")
    
    # 輪播控制按鈕與容器
    c_btn1, c_card, c_btn2 = st.columns([0.1, 0.8, 0.1])
    
    with c_btn1:
        st.write("")
        st.write("")
        st.write("")
        if st.button("◀", key="prev_carousel", use_container_width=True):
            st.session_state.carousel_index = (st.session_state.carousel_index - 1) % len(df)
            st.rerun()

    current_item = df.iloc[st.session_state.carousel_index]
    with c_card:
        col_img, col_info = st.columns([1, 1.2])
        with col_img:
            st.image(current_item["圖片"], use_container_width=True)
        with col_info:
            st.markdown(f"### 【推薦】{current_item['菜名']}")
            st.caption(f"分類：{current_item['菜系']} ｜ 烹飪時間：{current_item['耗時']}")
            st.write(current_item["特色"])
            ingredients_display = " ".join([f"`{i}`" for i in current_item["主要食材"]])
            st.markdown(f"**主要食材**：{ingredients_display}")
            st.info(f"💡 輪播第 {st.session_state.carousel_index + 1} / {len(df)} 道精選料理")

    with c_btn2:
        st.write("")
        st.write("")
        st.write("")
        if st.button("▶", key="next_carousel", use_container_width=True):
            st.session_state.carousel_index = (st.session_state.carousel_index + 1) % len(df)
            st.rerun()
            
    st.markdown("---")

# -------------------------------------------------------------
# 6. 資料篩選邏輯（菜系 + 關鍵字多重比對）
# -------------------------------------------------------------
filtered_df = df.copy()

if selected_cuisine != "全部菜系":
    filtered_df = filtered_df[filtered_df["菜系"] == selected_cuisine]

if search_keyword.strip():
    kw = search_keyword.strip().lower()
    
    def matches_search(row):
        # 搜尋菜名
        if kw in row["菜名"].lower():
            return True
        # 搜尋食材
        if any(kw in ing.lower() for ing in row["主要食材"]):
            return True
        # 搜尋調味料
        if any(kw in s.lower() for s in row["調味料"]):
            return True
        return False
        
    filtered_df = filtered_df[filtered_df.apply(matches_search, axis=1)]

# -------------------------------------------------------------
# 7. 料理清單展示（包含食材、調味料、做法與卡路里計算）
# -------------------------------------------------------------
st.write(f"共找到 **{len(filtered_df)}** 道推薦料理")

if filtered_df.empty:
    st.warning("查無符合條件的料理，請更換關鍵字或側邊欄菜系重試！")
else:
    for i in range(0, len(filtered_df), 2):
        row_cols = st.columns(2)
        batch = filtered_df.iloc[i:i+2]
        
        for idx, (_, row) in enumerate(batch.iterrows()):
            with row_cols[idx]:
                st.image(row["圖片"], use_container_width=True)
                st.subheader(row["菜名"])
                st.caption(f"風格：{row['菜系']} ｜ 烹飪時間：{row['耗時']}")
                st.write(f"**料理特色**：{row['特色']}")
                
                # 查看食材與調味料清單
                with st.expander("🛒 查看食材與調味料清單"):
                    st.markdown("**【主要食材】**")
                    st.write("、".join(row["主要食材"]))
                    st.markdown("**【調味料】**")
                    st.write("、".join(row["調味料"]))

                # 查看詳細料理做法
                with st.expander("👨‍🍳 查看料理步驟 / 做法"):
                    for step in row["做法"]:
                        st.write(step)
                        
                # 運用正規表示式計算食材對應卡路里
                with st.expander("🔥 檢視食材卡路里分析 (正規化萃取計算)"):
                    cal_breakdown, total_cal = calculate_calories(row["主要食材"])
                    st.dataframe(pd.DataFrame(cal_breakdown), hide_index=True, use_container_width=True)
                    st.metric(label="主要食材估算總熱量", value=f"{total_cal} kcal")
                    st.caption("註：數值採用正規表示式提取重量並比對標準食材庫換算，實際熱量會依調味料用量有些微差異。")
                
                st.markdown("")