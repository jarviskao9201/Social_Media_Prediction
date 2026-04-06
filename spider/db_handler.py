import pandas as pd
from sqlalchemy import create_engine, text
import urllib.parse
import hashlib
import re  # 💡 必須導入正規表達式模組

class MySQLHandler:
    def __init__(self, host, user, password, database):
        safe_password = urllib.parse.quote_plus(password)
        # 確保連線字串包含 charset=utf8mb4 以支援表情符號
        self.db_url = f"mysql+pymysql://{user}:{safe_password}@{host}/{database}?charset=utf8mb4"
        self.engine = create_engine(self.db_url)
        self._init_metadata_table()
        
    def convert_display_num(self, text): # 💡 加上 self
        """將 '1萬' -> 10000, '1.2k' -> 1200, '1,234' -> 1234"""
        if not text or text == "N/A":
            return 0
        
        # 移除逗號與空白，確保是字串
        clean_text = str(text).replace(',', '').strip()
        
        try:
            # 處理中文「萬」 (例如 1.2萬)
            if '萬' in clean_text:
                num_part = re.findall(r"[-+]?\d*\.\d+|\d+", clean_text)[0]
                return int(float(num_part) * 10000)
            
            # 處理英文「k」 (例如 1.5k)
            if 'k' in clean_text.lower():
                num_part = re.findall(r"[-+]?\d*\.\d+|\d+", clean_text.lower())[0]
                return int(float(num_part) * 1000)
            
            # 處理純數字 (例如 1857)
            return int(float(clean_text))
        except (IndexError, ValueError):
            return 0

    def _init_metadata_table(self):
        """初始化總目錄表"""
        with self.engine.begin() as conn:
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS articles (
                    url VARCHAR(512) PRIMARY KEY,
                    table_name VARCHAR(64),
                    title TEXT,
                    likes INT,
                    comments_count INT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            '''))

    def _get_hash_name(self, url):
        return f"article_{hashlib.md5(url.encode()).hexdigest()[:16]}"
        
    def save_to_mysql(self, df):
        if df is None or df.empty: return False
        try:
            row = df.iloc[0]
            url = row['URL']
            table_name = self._get_hash_name(url)

            # 💡 在存檔前先轉換所有數值欄位
            likes_val = self.convert_display_num(row.get('文章讚數', 0))
            comments_val = self.convert_display_num(row.get('留言數', 0))

            with self.engine.begin() as conn:
                # --- 1. 更新總表 (Metadata) ---
                conn.execute(text('''
                    INSERT INTO articles (url, table_name, title, likes, comments_count)
                    VALUES (:url, :table_name, :title, :likes, :comments_count)
                    ON DUPLICATE KEY UPDATE 
                    title=VALUES(title), likes=VALUES(likes), comments_count=VALUES(comments_count)
                '''), {
                    "url": url,
                    "table_name": table_name,
                    "title": row.get('文章標題', '無標題'),
                    "likes": likes_val,    # 💡 使用轉換後的整數
                    "comments_count": comments_val # 💡 使用轉換後的整數
                })

                # --- 2. 處理該文章的留言數據 (清洗並轉換) ---
                # 複製一份資料來處理，避免改動到原始 df
                comment_data = df[['留言內容', '留言讚數', '情緒標籤', '信心值']].copy()
                comment_data.columns = ['content', 'likes', 'sentiment_label', 'confidence']
                
                # 💡 關鍵：將「留言讚數」這一欄也進行數值轉換
                comment_data['likes'] = comment_data['likes'].apply(self.convert_display_num)

                # 建立/重置該文章的獨立表
                conn.execute(text(f"DROP TABLE IF EXISTS `{table_name}`"))
                conn.execute(text(f'''
                    CREATE TABLE `{table_name}` (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        content LONGTEXT,
                        likes INT,
                        sentiment_label VARCHAR(50),
                        confidence FLOAT
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                '''))
                
                # 寫入獨立表
                comment_data.to_sql(table_name, con=conn, if_exists='append', index=False)

            print(f"✅ 雙重存檔完成！總表已更新，獨立表 `{table_name}` 已建立。")
            return True
        except Exception as e:
            print(f"❌ 儲存失敗: {e}")
            return False

    def get_data_by_query(self, sql_query, params=None):
        try:
            return pd.read_sql(text(sql_query), self.engine, params=params)
        except Exception as e:
            print(f"⚠️ 讀取失敗: {e}")
            return pd.DataFrame()

    def get_global_stats(self):
        query = "SELECT AVG(likes) as avg_likes, SUM(comments_count) as total_comments FROM articles"
        return pd.read_sql(text(query), self.engine)