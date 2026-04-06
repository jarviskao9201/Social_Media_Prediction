import asyncio
import pandas as pd
import traceback
import re
from playwright.async_api import async_playwright
from sqlalchemy import text  # 💡 用於執行標籤補丁 SQL
import os
from dotenv import load_dotenv

# 導入你的模組與隊友的模組
from analyzer import SentimentAnalyzer
from db_handler import MySQLHandler
from label_manager import KeywordLabeller

# 加載 .env 環境變數
load_dotenv()

# --- 核心配置區 ---
TARGET_USER_URL = "https://www.miyoushe.com/sr/accountCenter/postList?id=288909600"
MAX_COMMENTS = 10  # 💡 依照要求，每篇只取前 10 則
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

async def intercept_response(response, storage):
    """攔截器：負責抓取文章列表與留言內容的 JSON 數據包"""
    url = response.url
    if response.status == 200:
        # 1. 攔截文章列表
        if "userPost" in url or "getPostList" in url:
            try:
                data = await response.json()
                posts = data.get("data", {}).get("list", [])
                existing_ids = {p['post']['post_id'] for p in storage["posts"]}
                for p in posts:
                    if p['post']['post_id'] not in existing_ids:
                        storage["posts"].append(p)
            except: pass

        # 2. 攔截留言列表
        if "reply/list" in url or "getPostReplies" in url:
            try:
                data = await response.json()
                replies = data.get("data", {}).get("list", [])
                storage["current_replies"].extend(replies)
            except: pass

def clean_html(raw_html):
    """清理米游社留言中的 HTML 標籤與特殊字元"""
    if not raw_html: return ""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', str(raw_html))
    return cleantext.replace('&nbsp;', ' ').strip()

async def process_and_save(storage, post_raw, url, analyzer, db):
    """整合數據、調用 AI 分析，並使用隊友的 Handler 存檔"""
    # 💡 關鍵：切片取前 10 則
    raw_replies = storage.get("current_replies", [])[:MAX_COMMENTS]
    if not raw_replies:
        print(f"⚠️ 文章 {url} 沒抓到留言數據，跳過分析。")
        return False

    print(f"🧠 正在分析該篇前 {len(raw_replies)} 則留言...")
    
    comment_data = []
    for r in raw_replies:
        content = clean_html(r.get('reply', {}).get('content', ''))
        if content:
            comment_data.append({
                "text": content,
                "likes": r.get('stat', {}).get('like_num', 0)
            })

    if not comment_data: return False

    # AI 情緒分析
    texts = [c["text"] for c in comment_data]
    analysis_df = analyzer.analyze(texts)

    # 封裝成符合 db_handler 預期的 DataFrame 格式
    final_rows = []
    for i in range(len(analysis_df)):
        final_rows.append({
            "URL": url,
            "文章標題": post_raw.get('post', {}).get('subject', '無標題'),
            "文章讚數": post_raw.get('stat', {}).get('like_num', 0),
            "留言數": post_raw.get('stat', {}).get('reply_num', 0),
            "留言內容": texts[i],
            "留言讚數": comment_data[i]["likes"],
            "情緒標籤": analysis_df.iloc[i].get("情緒標籤", "中性"),
            "信心值": analysis_df.iloc[i].get("信心值", 0.0)
        })

    # 呼叫隊友寫的 save_to_mysql (內含單位轉換與雜湊分表邏輯)
    return db.save_to_mysql(pd.DataFrame(final_rows))

async def main():
    print("🚀 啟動米游社全自動數據流水線 (整合測試版)...")
    analyzer = SentimentAnalyzer()
    db = MySQLHandler(**DB_CONFIG)
    tagger = KeywordLabeller()  # 💡 初始化標籤處理器
    api_storage = {"posts": [], "current_replies": []}

    async with async_playwright() as p:
        # 本機測試建議 headless=False 觀察過程
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # 註冊攔截器
        page.on("response", lambda res: asyncio.ensure_future(intercept_response(res, api_storage)))

        # 階段一：深度掃描歷年文章 ID
        print(f"🌍 正在進入主頁掃描歷年文章...")
        await page.goto(TARGET_USER_URL, wait_until="domcontentloaded")
        
        last_count = 0
        no_new_count = 0
        while no_new_count < 3:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(3)
            current_count = len(api_storage["posts"])
            print(f"📑 已發現 {current_count} 篇文章...")
            if current_count > last_count:
                no_new_count = 0
                last_count = current_count
            else:
                no_new_count += 1
                await page.mouse.wheel(0, -500)
                await asyncio.sleep(1)
                await page.mouse.wheel(0, 1000)

        if not api_storage["posts"]:
            print("❌ 掃描失敗，未取得任何文章。")
            await browser.close()
            return

        # 階段二：逐篇採集留言並更新標籤
        print(f"🎯 掃描結束！準備採集共 {len(api_storage['posts'])} 篇文章的數據...")
        
        for index, post in enumerate(api_storage["posts"]):
            p_id = post['post']['post_id']
            p_title = post['post']['subject']
            p_url = f"https://www.miyoushe.com/sr/article/{p_id}"
            
            print(f"📝 ({index+1}/{len(api_storage['posts'])}) 處理中: {p_title}")
            
            api_storage["current_replies"] = [] 
            try:
                await page.goto(p_url, wait_until="networkidle", timeout=60000)
                await page.evaluate("window.scrollTo(0, 1500)")
                await asyncio.sleep(3) # 等待留言 API 加載
                
                # 1. 執行基礎存檔 (留言分析)
                success = await process_and_save(api_storage, post, p_url, analyzer, db)
                
                # 2. 💡 標籤補丁：在不改動隊友 db_handler 的情況下，同步更新標籤
                if success:
                    current_tag = tagger.get_labels(p_title)
                    with db.engine.begin() as conn:
                        # 自動補全 category_tag 欄位
                        conn.execute(text("ALTER TABLE articles ADD COLUMN IF NOT EXISTS category_tag VARCHAR(255) AFTER title"))
                        # 寫入標籤
                        conn.execute(text("UPDATE articles SET category_tag = :tag WHERE url = :url"), 
                                     {"tag": current_tag, "url": p_url})
                    print(f"🏷️ 標籤 [{current_tag}] 已同步至總表。")

            except Exception as e:
                print(f"⚠️ 跳過文章 {p_id}，原因: {e}")
            
            await asyncio.sleep(1.5) # 防封鎖休息

        print("🏁 任務圓滿達成！")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
