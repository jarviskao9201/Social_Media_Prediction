import os
import pandas as pd
import json
import re
import urllib.parse
from sqlalchemy import create_engine
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

def run_fast_etl():
    print("⏳ [1/4] 正在透過 .env 設定連線至 AWS...")
    
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_NAME")
    
    if not all([db_user, db_password, db_host, db_name]):
        print("❌ 錯誤：無法從 .env 讀取完整的資料庫設定，請檢查檔案內容。")
        return
    
    safe_pwd = urllib.parse.quote_plus(db_password)
    engine = create_engine(f"mysql+pymysql://{db_user}:{safe_pwd}@{db_host}/{db_name}?charset=utf8mb4")
    
    print("⏳ [2/4] 撈取文章總表...")
    articles_df = pd.read_sql("SELECT table_name, title, likes, comments_count, category_tag FROM articles", engine)
    total_articles = len(articles_df)
    print(f"✅ 找到 {total_articles} 篇文章，準備進行雲端運算。")

    # 預先為總表打上 版本、玩法、體型的標籤，方便計算「文章數」
    def extract_version(tag_str):
        match = re.search(r'(\d+\.\d+)', str(tag_str))
        return float(match.group(1)) if match else None
    
    articles_df['version'] = articles_df['category_tag'].apply(extract_version)
    
    modes = ['差分宇宙', '模擬宇宙', '虛構敘事', '忘卻之庭', '末日幻影']
    articles_df['game_mode'] = articles_df['title'].apply(lambda x: next((m for m in modes if m.lower() in str(x).lower()), None))
    
    body_types = ['成年男', '青年男', '少年男', '成年女', '青年女', '少年女', '幼年女']
    articles_df['body_type'] = articles_df['category_tag'].apply(lambda x: next((bt for bt in body_types if bt in str(x)), None))

    all_version_sentiments = []
    all_mode_sentiments = []

    print("🧠 [3/4] 命令 AWS 進行留言情緒加總...")
    for i, row in articles_df.iterrows():
        if i > 0 and i % 50 == 0:
            print(f"   ... 已處理 {i} / {total_articles} 篇文章")

        t_name = row['table_name']
        v_tag = row['version']
        m_tag = row['game_mode']

        try:
            query = f"SELECT sentiment_label, SUM(likes) as total_likes FROM `{t_name}` GROUP BY sentiment_label"
            agg_df = pd.read_sql(query, engine)

            if not agg_df.empty:
                if pd.notnull(v_tag):
                    agg_df['version'] = str(v_tag)
                    all_version_sentiments.append(agg_df[['version', 'sentiment_label', 'total_likes']])
                if m_tag:
                    agg_df['game_mode'] = m_tag
                    all_mode_sentiments.append(agg_df[['game_mode', 'sentiment_label', 'total_likes']])
        except Exception:
            continue 

    print("📊 [4/4] 結算各項指標 (包含文章數)...")
    
    # 1. 角色熱度 (擴充為全圖鑑，並計算文章數)
    char_map = {
        '黃泉': ['黃泉', 'Acheron'], '流螢': ['流螢', 'Firefly'], '砂金': ['砂金', 'Aventurine'],
        '知更鳥': ['知更鳥', 'Robin'], '花火': ['花火', 'Sparkle'], '黑天鵝': ['黑天鵝', 'Black Swan'],
        '卡芙卡': ['卡芙卡', 'Kafka'], '銀狼': ['銀狼', 'Silver Wolf'], '真理醫生': ['真理醫生', 'Dr. Ratio'],
        '阮•梅': ['阮•梅', '阮梅', 'Ruan Mei'], '鏡流': ['鏡流', 'Jingliu'], '托帕': ['托帕', 'Topaz'],
        '符玄': ['符玄', 'Fu Xuan'], '飲月': ['飲月', 'Dan Heng', 'IL'], '景元': ['景元', 'Jing Yuan'],
        '希兒': ['希兒', 'Seele'], '羅剎': ['羅剎', 'Luocha'], '刃': ['刃', 'Blade'],
        '藿藿': ['藿藿', 'Huohuo'], '波提歐': ['波提歐', 'Boothill'], '翡翠': ['翡翠', 'Jade'],
        '雲璃': ['雲璃', 'Yunli'], '飛霄': ['飛霄', 'Feixiao'], '靈砂': ['靈砂', 'Lingsha'],
        '亂破': ['亂破', 'Rappa'], '姬子': ['姬子', 'Himeko'], '瓦爾特': ['瓦爾特', 'Welt'],
        '布洛妮婭': ['布洛妮婭', '鴨鴨', 'Bronya'], '傑帕德': ['傑帕德', 'Gepard'], '克拉拉': ['克拉拉', 'Clara'],
        '彥卿': ['彥卿', 'Yanqing'], '白露': ['白露', 'Bailu']
    }
    char_records = [{'character': name, 'likes': row['likes']} for _, row in articles_df.iterrows() for name, aliases in char_map.items() if any(a.lower() in str(row['title']).lower() for a in aliases)]
    
    all_chars_data = {}
    if char_records:
        char_df = pd.DataFrame(char_records)
        all_chars_data = char_df.groupby('character').agg(
            平均讚數=('likes', 'mean'),
            文章數=('likes', 'count')
        ).round(1).to_dict(orient='index')

    # 2. 體型熱度 (讚數 + 文章數)
    bt_stats = {}
    bt_df = articles_df.dropna(subset=['body_type'])
    if not bt_df.empty:
        bt_stats = bt_df.groupby('body_type').agg(
            總讚數=('likes', 'sum'),
            文章數=('likes', 'count')
        ).to_dict(orient='index')

    # 3. 版本情緒 & 玩法情緒
    v_sentiment = {}
    if all_version_sentiments:
        v_df = pd.concat(all_version_sentiments, ignore_index=True)
        v_sentiment = v_df.groupby(['version', 'sentiment_label'])['total_likes'].sum().unstack(fill_value=0).to_dict(orient='index')

    m_sentiment = {}
    if all_mode_sentiments:
        m_df = pd.concat(all_mode_sentiments, ignore_index=True)
        m_sentiment = m_df.groupby(['game_mode', 'sentiment_label'])['total_likes'].sum().unstack(fill_value=0).to_dict(orient='index')

    # 取得各版本與玩法的「文章數」
    v_counts = articles_df.dropna(subset=['version']).groupby('version').size().to_dict()
    m_counts = articles_df.dropna(subset=['game_mode']).groupby('game_mode').size().to_dict()

    # 打包儲存
    final_data = {
        "characters_stats": all_chars_data,
        "body_type_stats": bt_stats,
        "version_sentiment": v_sentiment,
        "version_counts": {str(k): int(v) for k, v in v_counts.items()},
        "mode_sentiment": m_sentiment,
        "mode_counts": {str(k): int(v) for k, v in m_counts.items()}
    }
    
    with open('dashboard_data.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
        
    print("✨ 大功告成！包含全角色與文章數的 dashboard_data.json 已產生！")

if __name__ == "__main__":
    run_fast_etl()