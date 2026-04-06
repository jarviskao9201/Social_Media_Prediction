import pandas as pd
import os
from dotenv import load_dotenv
from sqlalchemy import text
from db_handler import MySQLHandler    # 負責 MySQL 連線與操作的自定義類別
from label_manager import KeywordLabeller 

# 從 .env 檔案加載環境變數（如資料庫帳密），提升程式碼安全性
load_dotenv()

def update_article_tags(host, user, password, database):
    """
    從資料庫讀取所有文章標題，重新計算標籤並回填至資料庫
    """
    # 1. 初始化資料庫處理器與關鍵字標籤引擎
    handler = MySQLHandler(host, user, password, database)
    tagger = KeywordLabeller()
    
    print("Step 1: 正在從 MySQL 讀取總表數據...")
    
    # 2. 讀取總表 (articles) 
    # 必須同時選取 url，否則後面 Update 時會找不到對應的對象
    query = "SELECT url, title FROM articles"
    df = handler.get_data_by_query(query)
    
    # 檢查是否成功抓取到資料
    if df.empty:
        print("❌ 總表中沒有資料或讀取失敗。")
        return

    print(f"Step 2: 正在為 {len(df)} 篇文章生成新標籤...")
    
    # 3. 根據文章標題 (title) 生成對應的分類標籤
    # 使用 pandas 的 apply 功能，逐列執行 tagger.get_labels 方法
    df['new_tags'] = df['title'].apply(tagger.get_labels)

    print("Step 3: 正在將標籤更新回資料庫...")
    
    # 4. 執行批次更新 (Batch Update) 以提高效率
    try:
        # 使用 handler.engine.begin() 開啟一個資料庫事務 (Transaction)
        # 若執行過程中出錯，會自動 Rollback（回滾），確保資料完整性
        with handler.engine.begin() as conn:
            
            # A. 檢查並動態增加欄位：如果 articles 表還沒有 category_tag 欄位，則自動新增
            # VARCHAR(255) 儲存標籤字串，放在 title 欄位之後
            conn.execute(text("""
                ALTER TABLE articles 
                ADD COLUMN IF NOT EXISTS category_tag VARCHAR(255) AFTER title
            """))
            
            # B. 準備參數化 SQL 更新指令，防止 SQL 注入攻擊
            update_sql = text("""
                UPDATE articles 
                SET category_tag = :tag 
                WHERE url = :url
            """)
            
            # C. 整理批次更新的資料清單（List of Dictionaries）
            # 將 DataFrame 轉換為 SQLAlchemy 接受的參數格式
            update_params = [
                {"tag": row['new_tags'], "url": row['url']} 
                for _, row in df.iterrows()
            ]
            
            # D. 執行批次更新：SQLAlchemy 會自動優化這條指令
            conn.execute(update_sql, update_params)
            
        print(f"✅ 成功更新 {len(df)} 筆文章標籤！")
        
        # 在終端機印出前 5 筆資料，方便肉眼確認結果是否正確
        print("\n--- 更新預覽 (前 5 筆) ---")
        print(df[['title', 'new_tags']].head())
        
    except Exception as e:
        # 捕捉並印出所有可能的錯誤訊息（如資料庫連線中斷、欄位權限不足等）
        print(f"❌ 更新失敗，錯誤原因: {e}")

if __name__ == "__main__":
    # 從環境變數中讀取資料庫連線參數，避免將敏感資訊寫死在程式碼中
    db_config = {
        "host": os.getenv("DB_HOST"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME")
    }
    
    # 執行主函數
    update_article_tags(**db_config)