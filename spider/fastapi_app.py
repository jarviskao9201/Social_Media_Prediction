from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from visualizer import KeywordVersionForecaster
import uvicorn
import sys
import asyncio
import io
import base64
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine, text
import urllib.parse
import os
from dotenv import load_dotenv

# 假設你的爬蟲主函數在 main.py
# from main import to_csv 

load_dotenv()
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# --- 資料庫連線 (建議拉出成全域或使用 Dependency) ---
def get_db_engine():
    user = os.getenv("DB_USER")
    password = urllib.parse.quote_plus(os.getenv("DB_PASSWORD"))
    host = os.getenv("DB_HOST")
    database = os.getenv("DB_NAME")
    return create_engine(f"mysql+pymysql://{user}:{password}@{host}/{database}?charset=utf8mb4")

engine = get_db_engine()

# ---    工具：圖表轉 Base64 ---
def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return img_str

# --- 路由設定 ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    status_info = {"project_name": "HoYoLAB 數據分析監控", "status": "Online"}
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"info": status_info}
    )

@app.post("/start_crawl")
async def start_crawl(target_url: str, background_tasks: BackgroundTasks):
    # background_tasks.add_task(to_csv, target_url=target_url)
    return {"message": "爬蟲任務已在後台啟動", "target": target_url}

# --- 圖表 API 區塊 ---

@app.get("/chart/{chart_type}", response_class=HTMLResponse)
async def get_chart(request: Request, chart_type: str):
    fig, ax = plt.subplots(figsize=(10, 6))
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False

    try:
        if chart_type == "sentiment":
            # 1. 全站情緒圓餅圖
            tables_df = pd.read_sql(text("SELECT table_name FROM articles"), engine)
            queries = [f"SELECT sentiment_label FROM `{name}`" for name in tables_df['table_name']]
            df = pd.read_sql(text(" UNION ALL ".join(queries)), engine)
            counts = df['sentiment_label'].value_counts()
            ax.pie(counts, labels=counts.index, autopct='%1.1f%%', startangle=140, colors=sns.color_palette("pastel"))
            ax.set_title("全站情緒分佈總覽")

        elif chart_type == "top":
            # 2. 熱門文章長條圖
            df = pd.read_sql(text("SELECT title, likes FROM articles ORDER BY likes DESC LIMIT 10"), engine)
            df['short_title'] = df['title'].apply(lambda x: x[:12] + '...')
            sns.barplot(data=df, x='likes', y='short_title', ax=ax, palette="viridis")
            ax.set_title("前 10 名熱門文章")

        elif chart_type == "trend":
                    # 🚀 使用你封裝好的類別
                    forecaster = KeywordVersionForecaster(engine)
                    result = forecaster.generate_chart()
                    
                    # 如果回傳的是字串，代表出錯或資料不足
                    if isinstance(result, str):
                        return f'<div class="p-4 text-orange-500 font-bold">{result}</div>'
                    
                    # 如果回傳的是 fig 物件，則轉為 Base64
                    img_base64 = fig_to_base64(result)
                    return f'<img src="data:image/png;base64,{img_base64}" class="w-full rounded shadow-lg">'

        else:
            return "查無此圖表類型"

    except Exception as e:
        return f'<div class="p-4 text-red-500 font-bold">分析發生錯誤: {str(e)}</div>'

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    uvicorn.run(app, host="0.0.0.0", port=8000)