import os
import asyncio
from dotenv import load_dotenv
import pandas as pd
from playwright.async_api import async_playwright
from analyzer import SentimentAnalyzer
# 匯入你的爬蟲函式
from scraper_hoyolab import clean_ui, scrape_article_details
# 匯入你的儲存函式
from data_handler import init_summary_file, save_to_csv
from db_handler import MySQLHandler
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

load_dotenv()  # 載入 .env 檔案中的環境變數
analyzer = SentimentAnalyzer()
db = MySQLHandler(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
target_url = "https://www.hoyolab.com/circles/6/39/official?page_type=39&page_sort=news"
async def to_csv(target_url: str):
    output_dir = "hoyolab_test_output_4"
    summary_file = os.path.join(output_dir, "articles_summary.csv")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 初始化總表
    init_summary_file(summary_file)
    analyzer = SentimentAnalyzer() # 確保已定義分析器實例

    print("查尋資料庫中已存在的文章...")
    
    try:
        existing_df = db.get_data_by_query("SELECT url FROM articles")
        # 確保資料庫有欄位 'url'，並轉成 set 提高查詢速度
        processed_urls = set(existing_df['url'].tolist()) if not existing_df.empty else set()
        print(f"✅ 已載入 {len(processed_urls)} 筆已處理網址，將自動跳過。")
    except Exception as e:
        print(f"⚠️ 無法讀取舊資料 (可能是第一次執行): {e}")
        processed_urls = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True,args=["--no-sandbox"]) 
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto(target_url,timeout=60000)
        
        while True:
            await clean_ui(page)
            
            # 抓取連結
            urls = await page.evaluate("""
                () => Array.from(document.querySelectorAll('a[href*="/article/"]')).map(a => a.href)
            """)
            new_urls = [u for u in urls if u not in processed_urls]
            
            if new_urls:
                for url in new_urls:
                    # 執行內層爬取與 AI 分析
                    df = await scrape_article_details(context, analyzer, url)
                    
                    if df is not None and not df.empty:
                        # 1. 儲存至 CSV
                        csv_success = save_to_csv(df, output_dir, summary_file)
                        
                        # 2. 儲存至 MySQL (假設你的實例名稱為 db)
                        db_success = db.save_to_mysql(df)
                        
                        # 只要其中一個儲存成功，就標記為已處理
                        if db_success or csv_success:
                            processed_urls.add(url)
                            print(f"✅ 成功處理並儲存文章 (CSV: {csv_success}, SQL: {db_success})")
                        # 3. 如果資料庫失敗了，至少給個警告，但不要讓爬蟲卡死
                        if not db_success:
                            print(f"⚠️ 警告：{url} 存入資料庫失敗，但已存入 CSV 並跳過該網址。")

                    await asyncio.sleep(1)
            
            else:
                # 外層雙層捲動偵測
                print("⏳ 列表無更新，執行外層捲動偵測...")
                last_h = await page.evaluate("document.body.scrollHeight")
                
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.mouse.wheel(0, -600)
                await asyncio.sleep(0.5)
                await page.mouse.wheel(0, 1200)
                await asyncio.sleep(13)
                
                if (await page.evaluate("document.body.scrollHeight")) == last_h:
                    print("🏁 列表已到底部。")
                    break

        await browser.close()
if __name__ == "__main__":
    asyncio.run(to_csv(target_url))