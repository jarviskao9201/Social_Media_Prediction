import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from predictor_test import KeywordVersionForecaster
from db_handler import MySQLHandler
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="HSR 極速 API 伺服器")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# 初始化預測器實例 (全域變數，啟動時即載入)
db = MySQLHandler(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
)
forecaster = KeywordVersionForecaster(db_handler=db)

@app.get("/api/dashboard_data")
def get_dashboard_data():
    """讀取前四張圖的靜態 JSON 檔案"""
    try:
        with open('dashboard_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {"status": "success", "data": data}
    except FileNotFoundError:
        return {"status": "error", "message": "找不到檔案，請先執行 generate_summary.py"}

@app.get("/api/predict")
def predict_traffic(version: str = None):
    """呼叫 predictor_test.py 裡面的模組進行即時運算"""
    # 如果前端有傳 version 就用前端的，沒有就傳 None 讓模組自動算下一版
    target_v = float(version) if version else None
    result = forecaster.get_forecast_data(target_version=target_v)
    return result