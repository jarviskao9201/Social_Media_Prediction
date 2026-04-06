import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import lightgbm as lgb
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from db_handler import MySQLHandler  # 使用你的自定義類別
load_dotenv()  # 從 .env 加載環境變數
# --- 1. 自動字體設定 (修正 AttributeError) ---
def set_mpl_chinese_font():
    # 優先尋找支援中文的字體
    font_candidates = ['Microsoft JhengHei', 'PingFang TC', 'Heiti TC', 'SimHei', 'Arial Unicode MS']
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    
    for font in font_candidates:
        if font in available_fonts:
            plt.rcParams['font.sans-serif'] = [font]
            plt.rcParams['axes.unicode_minus'] = False
            return font
    return None

class KeywordVersionForecaster:
    def __init__(self, db_handler):
        """
        傳入已經初始化好的 MySQLHandler 實例
        """
        db_handler=MySQLHandler(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        self.db = db_handler

    def extract_version(self, tag_str):
        """從 category_tag 提取版本號 (例如: 'v4.1_活動' -> 4.1)"""
        if not tag_str: return None
        match = re.search(r'(\d+\.\d+)', str(tag_str))
        return float(match.group(1)) if match else None

    def fetch_data(self):
        """整合你的 MySQLHandler 方法"""
        query = "SELECT category_tag, likes, comments_count FROM articles"
        
        # 使用你剛找到的正確方法名
        # 因為它已經回傳 pd.DataFrame()，所以直接 return 即可
        df = self.db.get_data_by_query(query)
        
        if df.empty:
            print("⚠️ 從資料庫取得的數據為空，請檢查 table 'articles' 是否有資料。")
        if not df.empty:
            print(f"✅ 成功讀取欄位: {df.columns.tolist()}")
        return df

    def run_forecast_and_show(self,target_version=None):
        # 1. 抓取與清洗
        df_raw = self.fetch_data()
        if df_raw.empty:
            print("⚠️ 資料庫中無資料")
            return

        df_raw['version'] = df_raw['category_tag'].apply(self.extract_version)
        df_raw = df_raw.dropna(subset=['version']).sort_values('version')

        # 2. 版本聚合與特徵工程
        df_ver = df_raw.groupby('version').agg({
            'likes': 'mean',
            'comments_count': 'mean'
        }).reset_index()

        # 3. 確定預測目標版本
        last_v = df_ver['version'].max()
        if target_version is None:
            target_v = round(last_v + 0.1, 1)
        else:
            target_v = float(target_version)
        
        df_ver['prev_likes'] = df_ver['likes'].shift(1)
        df_ver['prev_comments'] = df_ver['comments_count'].shift(1)
        
        train_df = df_ver.dropna().copy()
        if len(train_df) < 2:
            print(f"⚠️ 數據量不足 (目前僅 {len(df_ver)} 個版本)，無法進行趨勢預測。")
            self._plot_results(df_ver, None, None, None) # 僅顯示歷史
            return
        
        # 3. LightGBM 模型
        features = ['version', 'prev_likes', 'prev_comments']
        X = train_df[features]
        y = train_df['likes']

        model = lgb.LGBMRegressor(n_estimators=100, learning_rate=0.1, verbose=-1)
        model.fit(X, y)
        train_df['prediction'] = model.predict(X)

        # 4. 預測下一個版本 (Next Version)
        last_v = df_ver['version'].max()
        next_v = round(last_v + 0.1, 1)
        future_X = pd.DataFrame({
            'version': [next_v],
            'prev_likes': [df_ver['likes'].iloc[-1]],
            'prev_comments': [df_ver['comments_count'].iloc[-1]]
        })
        next_pred = model.predict(future_X)[0]
        self._plot_results(df_ver, train_df, target_v, next_pred)


    def _plot_results(self, df_ver, train_df, target_v, target_pred):
        # 6. 繪圖優化：顯示所有版本
        set_mpl_chinese_font()
        # 根據版本數量動態調整圖表寬度，避免擁擠
        num_versions = len(df_ver)
        fig_width = max(10, num_versions * 0.8)
        fig, ax = plt.subplots(figsize=(fig_width, 6))
        
        # --- 繪製線條 ---
        # 歷史實際點
        ax.plot(df_ver['version'], df_ver['likes'], 'o-', label='實際平均按讚數', 
                color='#1f77b4', lw=2.5, markersize=10, zorder=3)
        
        # B. 繪製模型擬合趨勢 (若有模型)
        if train_df is not None:
            ax.plot(train_df['version'], train_df['prediction'], '--', 
                    label='LightGBM 擬合趨勢', color='#ff7f0e', alpha=0.7)
        
        # C. 繪製預測目標點
        if target_v and target_pred:
            # 畫預測星號
            ax.scatter(target_v, target_pred, color='red', s=250, marker='*', 
                       label=f'預測版本 {target_v}', zorder=5)
            # 連接線
            last_v = df_ver['version'].iloc[-1]
            last_l = df_ver['likes'].iloc[-1]
            ax.plot([last_v, target_v], [last_l, target_pred], 'r:', alpha=0.5)
            
            # 數值標註
            ax.annotate(f"預測: {target_pred:.1f}", (target_v, target_pred),
                        xytext=(0, 15), textcoords="offset points", ha='center',
                        bbox=dict(boxstyle='round,pad=0.3', fc='yellow', alpha=0.6),
                        color='red', weight='bold')

        # --- 座標軸優化 ---
        # 合併所有要顯示的版本刻度（現有的 + 未來的）
        # X 軸刻度優化
        all_ticks = sorted(list(df_ver['version']))
        if target_v: all_ticks.append(target_v)
        
        ax.set_xticks(all_ticks)
        ax.set_xticklabels([f"V{v}" for v in all_ticks], rotation=45)

        ax.set_title("版本流量全覽與 LightGBM 未來預測", fontsize=16)
        ax.set_xlabel("版本號 (Version)")
        ax.set_ylabel("平均按讚數 (Likes)")
        ax.legend()
        ax.grid(True, linestyle=':', alpha=0.5)
        
        plt.tight_layout()
        plt.show()
# --- 主程式進入點 ---
if __name__ == "__main__":
    # 1. 初始化你的 Handler (根據你的類別參數調整)
    # db = MySQLHandler(host='...', user='...', ...)
    try:
        db = MySQLHandler(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "你的密碼"),
            database=os.getenv("DB_NAME", "你的資料庫名")
        )
        
        # 2. 初始化預測器
        forecaster = KeywordVersionForecaster(db)
        
        # 3. 互動式輸入
        print("\n" + "="*30)
        print("🚀 歡迎使用版本流量預測系統 (LightGBM)")
        print("="*30)
        
        user_v = input("請輸入想要預測的版本號 (例如 4.6，直接按 Enter 預測下一版): ").strip()
        
        if user_v == "":
            forecaster.run_forecast_and_show(target_version=None)
        else:
            forecaster.run_forecast_and_show(target_version=user_v)
            
    except Exception as e:
        print(f"❌ 程式執行失敗: {e}")