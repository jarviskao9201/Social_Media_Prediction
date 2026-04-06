import requests
import pandas as pd
import time
import os
from dotenv import load_dotenv

# 引入你的模組
from analyzer import SentimentAnalyzer 
from db_handler import MySQLHandler

# 加載 .env 環境變數
load_dotenv()

def fetch_user_submitted_posts(username, max_posts=10):
    print(f"🗂️ 準備抓取 @{username} 的發文清單...")
    posts_list = []
    after = None  
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    while True:
        url = f"https://www.reddit.com/user/{username}/submitted.json"
        params = {'limit': 25} 
        if after: params['after'] = after
            
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"❌ 取得文章清單失敗，狀態碼：{response.status_code}")
            break
            
        data = response.json()
        children = data.get('data', {}).get('children', [])
        
        for child in children:
            post_data = child.get('data', {})
            posts_list.append({
                '文章標題': post_data.get('title', '無標題'),
                '文章按讚數': post_data.get('score', 0),
                '網址': "https://www.reddit.com" + post_data.get('permalink')
            })
            
            if max_posts and len(posts_list) >= max_posts:
                return posts_list

        after = data.get('data', {}).get('after')
        if not after: break
            
        print(f"翻頁中... 目前已收集 {len(posts_list)} 篇文章，停頓 2 秒防封鎖...")
        time.sleep(2) 
        
    return posts_list

def fetch_reddit_json(url):
    if not url.endswith('.json'):
        url = url.split('?')[0] + '.json'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else None

def parse_comments_tree(comments_list, depth=0):
    extracted = []
    for item in comments_list:
        if item.get('kind') == 't1':
            data = item.get('data', {})
            text_body = data.get('body', '').strip()
            
            if text_body and text_body not in ['[deleted]', '[removed]']:
                extracted.append({
                    "留言內容": text_body,
                    "留言讚數": data.get('score', 0)
                })
                
            replies = data.get('replies', '')
            if isinstance(replies, dict):
                reply_comments = replies.get('data', {}).get('children', [])
                extracted.extend(parse_comments_tree(reply_comments, depth + 1))
    return extracted

if __name__ == "__main__":
    target_user = "HonkaiStarRail"
    
    # ⚠️ 這裡先抓最新 5 篇測試，確認沒問題後，可改成 max_posts=None 抓取全部
    my_posts = fetch_user_submitted_posts(target_user, max_posts=None)
    
    if not my_posts:
        exit()
        
    print(f"\n✅ 成功取得 {len(my_posts)} 篇文章，準備啟動爬蟲與寫入程序...\n")
    
# ==========================================
    # 1. 啟動你的 MySQLHandler 與情緒分析器
    # ==========================================
    # 直接在這裡填寫你的真實資料庫帳號密碼
    db = MySQLHandler(
        host="IP",       # 或是你遠端伺服器的 IP
        user="MySQL 帳號",            # 你的 MySQL 帳號
        password="MySQL 密碼", # 你的 MySQL 密碼 (記得保留前後的引號)
        database="資料庫名稱"      # 資料庫名稱
    )
    
    analyzer = SentimentAnalyzer()
    
    # ==========================================
    # 2. 開始逐篇抓取與分析
    # ==========================================
    for idx, post in enumerate(my_posts):
        print(f"\n[{idx+1}/{len(my_posts)}] 正在處理：{post['文章標題'][:30]}...")
        
        json_data = fetch_reddit_json(post['網址'])
        parsed_data = []
        if json_data:
            comment_tree_data = json_data[1]['data']['children']
            parsed_data = parse_comments_tree(comment_tree_data, depth=0)
            
        comments_count = len(parsed_data)
        print(f"   -> 獲得 {comments_count} 則留言")

        # 如果有留言，才進行情緒分析與寫入
        if comments_count > 0:
            # 取出留言文字餵給 AI 模型
            texts_only = [item["留言內容"] for item in parsed_data]
            results_df = analyzer.analyze(texts_only)
            
            # 💡 完美對接：根據 db_handler.py 要求的結構建立 DataFrame
            db_records = []
            for i in range(comments_count):
                db_records.append({
                    "URL": post['網址'],                         
                    "文章標題": post['文章標題'],                
                    "文章讚數": post['文章按讚數'],              
                    "留言數": comments_count,                    
                    "留言內容": parsed_data[i]["留言內容"],      
                    "留言讚數": parsed_data[i]["留言讚數"],      
                    "情緒標籤": results_df.iloc[i]["情緒標籤"],  
                    "信心值": float(results_df.iloc[i]["信心值"])
                })
            
            # 將資料轉換為 DataFrame
            post_df = pd.DataFrame(db_records)
            
            # 呼叫你的 db_handler 將資料寫入 MySQL
            db.save_to_mysql(post_df)
            
        time.sleep(2) 
        
    print("\n✅ 所有文章爬取完畢！")
    print("👉 下一步：請在終端機執行 `python update_tags.py` 來為資料庫打上標籤！")