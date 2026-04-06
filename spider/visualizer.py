import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine, text
import urllib.parse
import os
from dotenv import load_dotenv
from predictor import KeywordVersionForecaster

# 載入環境變數
load_dotenv()

class DataVisualizer:
    def __init__(self):
        # 從 .env 讀取設定 (請確保與你的爬蟲設定一致)
        host = os.getenv("DB_HOST")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        database = os.getenv("DB_NAME")
        
        safe_password = urllib.parse.quote_plus(password)
        self.db_url = f"mysql+pymysql://{user}:{safe_password}@{host}/{database}?charset=utf8mb4"
        self.engine = create_engine(self.db_url)
        
        # 設定中文顯示 (Windows 使用 Microsoft YaHei, Mac 使用 Arial Unicode MS)
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
        sns.set_theme(style="whitegrid", font='Microsoft YaHei')

    def get_df(self, sql):
        """通用讀取資料方法"""
        try:
            return pd.read_sql(text(sql), self.engine)
        except Exception as e:
            print(f"❌ 讀取失敗: {e}")
            return pd.DataFrame()

    def plot_total_sentiment(self):
        """1. 彙整所有獨立表，畫出全站情緒比例"""
        print("📊 正在彙整全站情緒資料...")
        # 先從總表抓出所有獨立表的名稱
        tables_df = self.get_df("SELECT table_name FROM articles")
        if tables_df.empty: 
            print("目前沒有文章資料。")
            return

        # 構建 UNION 查詢
        queries = [f"SELECT sentiment_label FROM `{name}`" for name in tables_df['table_name']]
        final_query = " UNION ALL ".join(queries)
        df = self.get_df(final_query)

        if not df.empty:
            counts = df['sentiment_label'].value_counts()
            plt.figure(figsize=(8, 8))
            plt.pie(counts, labels=counts.index, autopct='%1.1f%%', startangle=140, 
                    colors=sns.color_palette("pastel"), explode=[0.03]*len(counts))
            plt.title("所有文章 - 讀者情緒分佈總覽", fontsize=16)
            plt.show()

    def plot_top_articles(self, limit=10):
        """2. 比較熱門文章讚數"""
        print(f"📊 正在生成前 {limit} 名熱門文章圖表...")
        df = self.get_df(f"SELECT title, likes FROM articles ORDER BY likes DESC LIMIT {limit}")
        
        if not df.empty:
            plt.figure(figsize=(10, 6))
            # 標題太長切掉部分文字
            df['short_title'] = df['title'].apply(lambda x: x[:15] + '...' if len(x)>15 else x)
            sns.barplot(
                data=df, 
                x='likes', 
                y='short_title', 
                hue='short_title',  # 指定顏色變數
                palette="viridis", 
                legend=False        # 隱藏圖例（因為 y 軸已經有標籤了）
            )
            plt.title(f"前 {limit} 名文章讚數排行榜", fontsize=16)
            plt.xlabel("讚數")
            plt.ylabel("文章標題")
            plt.tight_layout()
            plt.show()

    def plot_sentiment_comparison(self):
        """3. 各文章情緒對比 (堆疊長條圖)"""
        print("📊 正在生成各文章情緒對比圖...")
        tables_df = self.get_df("SELECT title, table_name FROM articles LIMIT 10")
        all_data = []

        for _, row in tables_df.iterrows():
            q = f"SELECT sentiment_label, COUNT(*) as count FROM `{row['table_name']}` GROUP BY sentiment_label"
            temp = self.get_df(q)
            temp['article'] = row['title'][:10] + "..."
            all_data.append(temp)

        if all_data:
            df_all = pd.concat(all_data)
            df_pivot = df_all.pivot(index='article', columns='sentiment_label', values='count').fillna(0)
            
            df_pivot.plot(kind='bar', stacked=True, figsize=(12, 7), colormap='Set3')
            plt.title("各文章情緒組成對比", fontsize=16)
            plt.xlabel("文章")
            plt.ylabel("留言數量")
            plt.xticks(rotation=45)
            plt.legend(title="情緒")
            plt.tight_layout()
            plt.show()

if __name__ == "__main__":
    viz = DataVisualizer()
    
    # 你可以選擇要執行哪一個圖表
    viz.plot_total_sentiment()      # 圓餅圖：全站情緒
    viz.plot_top_articles()         # 條形圖：熱門排行
    viz.plot_sentiment_comparison()  # 堆疊圖：文章情緒對比