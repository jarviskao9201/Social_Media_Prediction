# Social_Media_Prediction
========================================================================
   HSR Social Media Analytics & Prediction - Project Documentation
========================================================================

1. [專案簡介]
------------------------------------------------------------------------
本專案是一個全方位的數據分析平台，專門針對《崩壞：星穹鐵道》的社群數據進行分析。
系統整合了多平台爬蟲、自動化資料清洗、情緒標籤化處理，並利用機器學習模型 (LightGBM) 
進行版本熱度預測。最後透過 Streamlit 儀表板與 FastAPI 介面提供視覺化成果。


2. [檔案目錄說明]
------------------------------------------------------------------------
【核心啟動程式】
- api_server.py         : 系統後端 API (FastAPI)，負責傳遞數據與 AI 預測結果。
- dashboard.py          : 前端監控戰情室 (Streamlit)，提供互動式圖表。
- main.py               : 專案啟動入口。

【爬蟲模組 (Scrapers)】
- miyoushe_main.py      : 米遊社 (Miyoushe) 貼文與留言抓取主程式。
- reddit_main.py        : Reddit 全球社群數據採集程式。
- scraper_hoyolab.py    : HoYoLAB 官方論壇爬蟲邏輯。

【數據處理與分析】
- generate_summary.py   : 數據預處理腳本，將資料聚合至 dashboard_data.json。
- analyzer.py           : 資料統計與分析邏輯。
- visualizer.py         : 靜態圖表產生工具。
- update_tags.py        : 管理與更新版本、角色、體型等關鍵字標籤。

【機器學習與預測】
- predictor_test.py     : 流量預測核心模型 (LightGBM)，包含特徵工程與訓練。
- predictor.py          : 預測模型相關類別封裝。

【資料庫與工具】
- db_handler.py         : 資料庫 (MySQL/RDS) 連線與 CRUD 封裝。
- .env                  : 環境變數設定檔 (需自行建立，包含資料庫密碼)。
- dashboard_data.json   : 預先快取的統計數據檔案。


3. [技術棧 (Tech Stack)]
------------------------------------------------------------------------
- 語言: Python 3.12+
- 框架: FastAPI, Streamlit
- 機器學習: LightGBM, Scikit-learn
- 資料庫: MySQL / AWS RDS
- 雲端部署: AWS EC2 (Ubuntu), Nginx (Reverse Proxy), Tmux


4. [部署與執行步驟]
------------------------------------------------------------------------
步驟 1: 建立虛擬環境
   $ python3 -m venv .venv
   $ source .venv/bin/activate

步驟 2: 安裝套件
   $ pip install -r requirements.txt

步驟 3: 啟動後端 API (建議使用 tmux)
   $ uvicorn api_server:app --host 0.0.0.0 --port 8000

步驟 4: 啟動前端網頁
   $ streamlit run dashboard.py


5. [備註]
------------------------------------------------------------------------
- 執行前請確保 .env 檔案中已正確配置資料庫連線資訊。
- AWS 部署請確認 Security Group 已開啟 Port 80, 8000, 8501。
- 若遇到 libgomp.so.1 錯誤，請執行: sudo apt install libgomp1

------------------------------------------------------------------------
最後更新日期: 2026-04-07
開發團隊: Ivan & Team
========================================================================
