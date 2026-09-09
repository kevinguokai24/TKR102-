import streamlit as st
import pandas as pd

# 頁面基本配置
st.set_page_config(page_title="美味指南 - 智能美食推薦", layout="wide", page_icon="🍳")

# 1. 模擬清洗後的美食資料庫 (可替換為 pd.read_csv("cleaned_recipes.csv"))
@st.cache_data
def load_food_data():
    data = [
        {
            "菜名": "番茄牛肉燉湯",
            "菜系": "異國料理",
            "餐別": "正餐",
            "烹飪難度": "中等",
            "主要食材": ["牛腱肉", "番茄", "洋蔥", "紅蘿蔔", "月桂葉"],
            "耗時": "60 分鐘",
            "特色": "濃郁酸甜，富含茄紅素，暖胃滋補首選。",
            "圖片": "https://images.unsplash.com/photo-1547592166-23ac45744acd?w=600&q=80"
        },
        {
            "菜名": "台式經典三杯雞",
            "菜系": "中式料理",
            "餐別": "正餐",
            "烹飪難度": "簡單",
            "主要食材": ["雞腿肉", "老薑", "大蒜", "黑麻油", "九層塔", "米酒"],
            "耗時": "25 分鐘",
            "特色": "香氣四溢、下飯神器，台菜經典代表作。",
            "圖片": "https://images.unsplash.com/photo-1598515214211-89d3c73ae83b?w=600&q=80"
        },
        {
            "菜名": "日式照燒雞肉串",
            "菜系": "日韓料理",
            "餐別": "宵夜/點心",
            "烹飪難度": "簡單",
            "主要食材": ["雞腿肉", "大蔥", "日式醬油", "味醂", "清酒"],
            "耗時": "20 分鐘",
            "特色": "鹹甜濃郁，居酒屋必備下酒菜。",
            "圖片": "https://images.unsplash.com/photo-1532550907401-a500c9a57435?w=600&q=80"
        },
        {
            "菜名": "酪梨鮮蝦低卡沙拉",
            "菜系": "健康輕食",
            "餐別": "輕食/早餐",
            "烹飪難度": "簡單",
            "主要食材": ["白蝦", "熟酪梨", "羅曼生菜", "小番茄", "橄欖油", "檸檬汁"],
            "耗時": "15 分鐘",
            "特色": "高蛋白、好油脂，減脂健身族群最愛。",
            "圖片": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=600&q=80"
        },
        {
            "菜名": "義式蒜香白酒蛤蜊麵",
            "菜系": "異國料理",
            "餐別": "正餐",
            "烹飪難度": "中等",
            "主要食材": ["義大利麵", "新鮮蛤蜊", "大蒜", "白酒", "初榨橄欖油", "巴西里"],
            "耗時": "25 分鐘",
            "特色": "鮮甜海味搭配蒜香與清爽白酒香氣。",
            "圖片": "https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=600&q=80"
        },
        {
            "菜名": "韓式泡菜豆腐鍋",
            "菜系": "日韓料理",
            "餐別": "正餐",
            "烹飪難度": "簡單",
            "主要食材": ["老泡菜", "嫩豆腐", "豬五花肉片", "金針菇", "韓式辣醬"],
            "耗時": "20 分鐘",
            "特色": "酸辣過癮，暖身開胃，一鍋搞定一餐。",
            "圖片": "https://images.unsplash.com/photo-1583032015879-c5c56c2e8b01?w=600&q=80"
        }
    ]
    return pd.DataFrame(data)

df = load_food_data()

# 2. 側邊欄：選單過濾區 + LINE 加入好友區塊
with st.sidebar:
    st.header("🍽️ 找料理選單")
    
    cuisine_options = ["全部菜系"] + sorted(df["菜系"].unique().tolist())
    selected_cuisine = st.selectbox("1. 選擇菜系風格：", cuisine_options)
    
    meal_options = ["全部時段"] + sorted(df["餐別"].unique().tolist())
    selected_meal = st.selectbox("2. 選擇用餐時段：", meal_options)
    
    difficulty_options = ["全部難度"] + sorted(df["烹飪難度"].unique().tolist())
    selected_difficulty = st.selectbox("3. 烹飪難度：", difficulty_options)
    
    st.markdown("---")
    
    # LINE 加入好友區塊
    st.markdown("### 💬 加入 LINE 好友")
    st.caption("加入美食官方帳號，天天推播今日菜單與獨家減脂食譜！")
    
    LINE_URL = "https://line.me/R/ti/p/@your_line_id"  # 替換為你的 LINE 連結或 QR Code
    qr_code_url = "https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=" + LINE_URL
    
    st.image(qr_code_url, caption="掃描 QR Code 加好友", width=160)
    st.link_button("👉 點我直接加入 LINE 好友", LINE_URL, use_container_width=True)

# 3. 資料篩選邏輯
filtered_df = df.copy()

if selected_cuisine != "全部菜系":
    filtered_df = filtered_df[filtered_df["菜系"] == selected_cuisine]

if selected_meal != "全部時段":
    filtered_df = filtered_df[filtered_df["餐別"] == selected_meal]

if selected_difficulty != "全部難度":
    filtered_df = filtered_df[filtered_df["烹飪難度"] == selected_difficulty]

# 4. 主頁面展示
st.title("🍳 智能美味生活館")
st.write(f"共找到 **{len(filtered_df)}** 道推薦料理")
st.markdown("---")

if filtered_df.empty:
    st.info("查無符合條件的料理，請在左側換個選單條件試試看！")
else:
    # 兩欄卡片式排版
    for i in range(0, len(filtered_df), 2):
        row_cols = st.columns(2)
        batch = filtered_df.iloc[i:i+2]
        
        for idx, (_, row) in enumerate(batch.iterrows()):
            with row_cols[idx]:
                st.image(row["圖片"], use_container_width=True)
                st.subheader(row["菜名"])
                st.caption(f"風格：{row['菜系']} ｜ 時段：{row['餐別']} ｜ 難度：{row['烹飪難度']} ｜ 烹飪時間：{row['耗時']}")
                st.write(f"**簡介**：{row['特色']}")
                
                # 食材標籤展開區塊
                with st.expander("🛒 查看必備食材清單"):
                    ingredients_md = " ".join([f"`{item}`" for item in row["主要食材"]])
                    st.markdown(ingredients_md)
                st.markdown("")