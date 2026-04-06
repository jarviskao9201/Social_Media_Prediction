import os
import re
import pandas as pd

def sanitize_filename(filename):
    """移除檔案名稱中的非法字元，確保 Windows/Mac 都能存檔"""
    if not filename:
        return "untitled_post"
    return re.sub(r'[\\/*?:"<>|]', "_", filename)

def init_summary_file(file_path):
    """初始化總表 Header"""
    if not os.path.exists(file_path):
        df = pd.DataFrame(columns=["文章標題", "文章內容", "文章讚數", "留言數", "URL", "關鍵字標籤"])
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        print(f"📁 已建立總表檔案: {file_path}")

def save_to_csv(df, output_dir, summary_file):
    """
    將爬取到的 DataFrame 拆分為「總表紀錄」與「獨立文章分表」
    """
    if df is None or df.empty:
        return False

    try:
        # 1. 提取文章基本資訊 (取第一筆即可)   
# 1. 偵測標籤位置
        # 先檢查有沒有 summary_keywords 欄位
        if 'summary_keywords' in df.columns:
            article_keywords = df['summary_keywords'].iloc[0]
        # 如果沒有，檢查看看是不是叫「關鍵字標籤」
        elif '關鍵字標籤' in df.columns:
            article_keywords = df['關鍵字標籤'].iloc[0]
        else:
            # 如果都抓不到，列出所有欄位名稱，方便我們找鬼
            print(f"⚠️ 找不到標籤欄位！目前的欄位有: {df.columns.tolist()}")
            article_keywords = "未分類"
        debug_info = f"文章標題: {df['文章標題'].iloc[0] if '文章標題' in df.columns else 'N/A'} | 關鍵字標籤: {article_keywords}"
        print(f"🔍 正在儲存文章... {debug_info}")
        row = df.iloc[0]
        summary_row = pd.DataFrame([{
            "文章標題": row['文章標題'],
            "文章內容": row['文章內容'],
            "文章讚數": row['文章讚數'],
            "留言數": row['留言數'],
            "URL": row['URL'],
            "關鍵字標籤": article_keywords  # 總表也加上關鍵字標籤欄位
        }])
        
        # 2. 附加到總表 (Summary)
        summary_row.to_csv(summary_file, mode='a', index=False, header=False, encoding="utf-8-sig")

        # 3. 儲存該文章的詳情分表 (Details)
        # 只保留留言相關的欄位
        detail_cols = ['留言內容', '留言讚數', '語言', '情緒標籤', '信心值']
        existing_cols = [c for c in detail_cols if c in df.columns]
        detail_df = df[existing_cols]
        
        # 處理檔名並存檔
        clean_title = sanitize_filename(row['文章標題'])
        detail_path = os.path.join(output_dir, f"{clean_title}.csv")
        detail_df.to_csv(detail_path, index=False, encoding="utf-8-sig")
        
        return True
    except Exception as e:
        print(f"❌ 儲存 CSV 時出錯: {e}")
        return False