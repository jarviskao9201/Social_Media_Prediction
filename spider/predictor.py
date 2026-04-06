import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import lightgbm as lgb
from sqlalchemy import create_engine, text
import numpy as np

# 設定中文顯示 (根據系統環境調整)
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS'] # Mac 使用
plt.rcParams['axes.unicode_minus'] = False

class KeywordVersionForecaster:
    def __init__(self, engine=None):
        self.engine = engine
    # --- 自動尋找系統中可用的中文字體 ---
    def set_mpl_chinese_font():
        # 優先順序：微軟正黑體 (Win), 蘋方 (Mac), 儷黑 (Mac), 黑體 (Linux/Generic)
        font_names = ['Microsoft JhengHei', 'PingFang TC', 'Heiti TC', 'SimHei', 'Arial Unicode MS']
        
        # 取得系統目前安裝的所有字體清單
        # 注意：這裡使用 fm.fontManager (大寫 M)
        available_fonts = [f.name for f in fm.fontManager.ttflist]
        
        found = False
        for font in font_names:
            if font in available_fonts:
                plt.rcParams['font.sans-serif'] = [font]
                found = True
                break
                
        # 解決座標軸負號顯示為方塊的問題
        plt.rcParams['axes.unicode_minus'] = False
        
        if not found:
            print("⚠️ 系統中找不到預設中文字體，圖表標籤可能顯示為方塊。")
    # 呼叫設定函式
    set_mpl_chinese_font()
    
    def extract_version(self, tag_str):
        """從 category_tag 中提取版本號 (如: 'v4.1_活動' -> 4.1)"""
        if not tag_str: return None
        match = re.search(r'(\d+\.\d+)', str(tag_str))
        return float(match.group(1)) if match else None

    def get_data(self):
        """從 MySQL 讀取或生成模擬數據"""
        if self.engine:
            query = "SELECT category_tag, likes, comments FROM articles"
            df = pd.read_sql(text(query), self.engine)
        else:
            # --- 模擬數據生成 (供測試使用) ---
            data = {
                'category_tag': ['v1.0_初始', 'v1.1_更新', 'v1.2_活動', 'v2.0_大改', 'v2.1_修復', 'v2.2_熱門'],
                'likes': [100, 120, 250, 400, 380, 500],
                'comments': [10, 15, 40, 80, 70, 110]
            }
            df = pd.DataFrame(data)
            print("💡 使用模擬數據運行中...")
        return df

    def process_and_predict(self):
        raw_df = self.get_data()
        
        # 1. 提取版本並排序
        raw_df['version'] = raw_df['category_tag'].apply(self.extract_version)
        raw_df = raw_df.dropna(subset=['version']).sort_values('version')

        # 2. 按版本聚合 (處理同版本多篇文章的情況)
        df_ver = raw_df.groupby('version').agg({
            'likes': 'mean',
            'comments': 'mean'
        }).reset_index()

        # 3. 特徵工程 (滯後特徵)
        df_ver['prev_likes'] = df_ver['likes'].shift(1)
        df_ver['prev_comments'] = df_ver['comments'].shift(1)
        
        # 準備訓練集 (移除第一筆因為沒有 prev 資料)
        train_df = df_ver.dropna().copy()
        
        if len(train_df) < 2:
            return "⚠️ 數據量不足，至少需要 3 個版本才能計算趨勢。"

        # 4. LightGBM 模型訓練
        features = ['version', 'prev_likes', 'prev_comments']
        X = train_df[features]
        y = train_df['likes']

        model = lgb.LGBMRegressor(n_estimators=100, learning_rate=0.1, verbose=-1)
        model.fit(X, y)
        train_df['prediction'] = model.predict(X)

        # 5. 預測未來版本 (例如 2.2 之後預測 2.3)
        last_version = df_ver['version'].max()
        next_version = round(last_version + 0.1, 1)
        future_X = pd.DataFrame({
            'version': [next_version],
            'prev_likes': [df_ver['likes'].iloc[-1]],
            'prev_comments': [df_ver['comments'].iloc[-1]]
        })
        next_pred = model.predict(future_X)[0]

        # --- 繪圖 ---
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 實測點
        ax.plot(df_ver['version'], df_ver['likes'], 'o-', label='各版本實際平均讚數', markersize=8, color='#1f77b4')
        # 模型擬合線
        ax.plot(train_df['version'], train_df['prediction'], '--', label='LightGBM 學習趨勢', color='#ff7f0e')
        # 未來預測點
        ax.scatter(next_version, next_pred, color='red', s=200, marker='*', label='下個版本預測點', zorder=5)
        
        # 數值標註
        ax.annotate(f"預測 Ver {next_version}\n{next_pred:.1f} Likes", 
                    (next_version, next_pred), xytext=(-20, 20), 
                    textcoords='offset points', ha='center', 
                    bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5))

        ax.set_title("基於 category_tag 版本的流量預測圖表", fontsize=15)
        ax.set_xlabel("版本號 (Version)")
        ax.set_ylabel("平均按讚數")
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        return fig

# --- 執行處 ---
if __name__ == "__main__":
    # 如果你有資料庫，請取消下面兩行的註釋並填寫正確資訊
    # engine = create_engine('mysql+pymysql://user:pass@host/dbname')
    # forecaster = KeywordVersionForecaster(engine)
    
    forecaster = KeywordVersionForecaster() # 使用模擬數據測試
    fig = forecaster.process_and_predict()
    
    if isinstance(fig, str):
        print(fig)
    else:
        plt.show()