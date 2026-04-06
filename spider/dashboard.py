import streamlit as st
import requests
import pandas as pd
import altair as alt
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

st.set_page_config(page_title="HSR 極速戰情室", layout="wide")

def set_mpl_chinese_font():
    # 1. 定義字體檔案路徑 (剛才下載的位置)
    font_path = '/home/hsradmin/hsr-socialmedia-prediction/NotoSansTC-Regular.ttf'
    
    if os.path.exists(font_path):
        # 強制載入指定路徑的字體
        font_prop = fm.FontProperties(fname=font_path)
        # 註冊到 fontManager
        fm.fontManager.addfont(font_path)
        # 設定為全域預設字體 (使用字體檔案內部的名稱，通常是 'Noto Sans CJK TC' 或 'Noto Sans TC')
        plt.rcParams['font.sans-serif'] = [font_prop.get_name()]
        plt.rcParams['axes.unicode_minus'] = False
        print(f"✅ 已成功從路徑載入字體: {font_path}")
    else:
        # 2. 如果檔案不存在，嘗試自動搜尋系統字體 (備援方案)
        font_candidates = ['Noto Sans CJK TC', 'Noto Sans CJK JP', 'SimHei', 'WenQuanYi Micro Hei']
        available_fonts = [f.name for f in fm.fontManager.ttflist]
        for font in font_candidates:
            if font in available_fonts:
                plt.rcParams['font.sans-serif'] = [font]
                print(f"✅ 已從系統載入備援字體: {font}")
                break
    
    plt.rcParams['axes.unicode_minus'] = False

set_mpl_chinese_font()
API_BASE_URL = "http://127.0.0.1:8000"

st.title("🚂 Honkai: Star Rail 極速分析戰情室")
st.markdown("---")

try:
    response = requests.get(f"{API_BASE_URL}/api/dashboard_data")
    if response.status_code == 200 and response.json()["status"] == "success":
        data = response.json()["data"]
        
        # ==========================================
        # 🎛️ 全域互動控制面板
        # ==========================================
        st.markdown("### 🎛️ 互動分析控制面板")
        
        ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1, 1, 1])
        with ctrl_col1:
            display_metric = st.radio("📊 選擇分析指標：", ["讚數 (熱度)", "文章數 (討論量)"], horizontal=True)
        with ctrl_col2:
            sort_option = st.radio("↕️ 圖表排序方式：", ["由高到低", "由低到高", "依名稱"], horizontal=True)
        with ctrl_col3:
            max_chars = len(data.get("characters_stats", {}))
            top_n = st.slider("🏆 顯示前 N 名角色：", min_value=3, max_value=max_chars, value=10) if max_chars > 0 else 10

        st.markdown("<br>", unsafe_allow_html=True)

        # 包含大小寫的顏色對應，確保圖表顏色正確
        sentiment_scale = alt.Scale(
            domain=['Positive', 'Neutral', 'Negative', 'positive', 'neutral', 'negative', '正面', '中性', '負面'], 
            range=['#2ca02c', '#7f7f7f', '#d62728', '#2ca02c', '#7f7f7f', '#d62728', '#2ca02c', '#7f7f7f', '#d62728']
        )

        # ==========================================
        # 🌟 繪圖區塊
        # ==========================================
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("1. 版本玩家回饋")
            if data.get("version_sentiment"):
                df_v = pd.DataFrame.from_dict(data["version_sentiment"], orient='index')
                df_v['文章數'] = df_v.index.map(data.get("version_counts", {}))
                version_order = df_v.index.tolist() 
                
                if display_metric == "讚數 (熱度)":
                    df_v_plot = df_v.drop(columns=['文章數']).reset_index().melt(id_vars='index', var_name='情緒', value_name='數值')
                    y_title = '留言總讚數'
                else:
                    df_v_plot = df_v[['文章數']].reset_index().rename(columns={'文章數': '數值'})
                    df_v_plot['情緒'] = '文章數'
                    y_title = '被提及的文章數'

                chart1 = alt.Chart(df_v_plot).mark_bar().encode(
                    x=alt.X('index:N', sort=version_order, title='版本號'),
                    y=alt.Y('數值:Q', title=y_title),
                    color=alt.Color('情緒:N', scale=sentiment_scale) if display_metric == "讚數 (熱度)" else alt.value('#1f77b4'),
                    tooltip=['index', '數值', '情緒'] if display_metric == "讚數 (熱度)" else ['index', '數值']
                ).properties(height=350)
                # ✨ 升級為 width='stretch'
                st.altair_chart(chart1, width='stretch')
            else:
                st.info("無版本回饋資料")

        with col2:
            st.subheader(f"2. 角色熱度排行 (Top {top_n})")
            if data.get("characters_stats"):
                df_c = pd.DataFrame.from_dict(data["characters_stats"], orient='index').reset_index().rename(columns={'index': '角色'})
                target_col = "平均讚數" if display_metric == "讚數 (熱度)" else "文章數"
                
                if sort_option == "由高到低": df_c = df_c.sort_values(by=target_col, ascending=False)
                elif sort_option == "由低到高": df_c = df_c.sort_values(by=target_col, ascending=True)
                elif sort_option == "依名稱": df_c = df_c.sort_values(by="角色", ascending=True)
                
                df_c = df_c.head(top_n) 
                
                char_order = df_c['角色'].tolist()
                chart2 = alt.Chart(df_c).mark_bar(color='#9467bd').encode(
                    x=alt.X('角色:N', sort=char_order, title=''),
                    y=alt.Y(f'{target_col}:Q', title=target_col),
                    tooltip=['角色', '平均讚數', '文章數'] 
                ).properties(height=350)
                # ✨ 升級為 width='stretch'
                st.altair_chart(chart2, width='stretch')
            else:
                st.info("無角色熱度資料")

        st.markdown("---")
        col3, col4 = st.columns(2)
        
        with col3:
            st.subheader("3. 喜愛角色的外觀")
            if data.get("body_type_stats"):
                df_b = pd.DataFrame.from_dict(data["body_type_stats"], orient='index').reset_index().rename(columns={'index': '體型'})
                target_col = "總讚數" if display_metric == "讚數 (熱度)" else "文章數"
                
                if sort_option == "由高到低": df_b = df_b.sort_values(by=target_col, ascending=False)
                elif sort_option == "由低到高": df_b = df_b.sort_values(by=target_col, ascending=True)
                elif sort_option == "依名稱": df_b = df_b.sort_values(by="體型", ascending=True)

                body_order = df_b['體型'].tolist()
                chart3 = alt.Chart(df_b).mark_bar(color='#ff7f0e').encode(
                    x=alt.X('體型:N', sort=body_order, title=''),
                    y=alt.Y(f'{target_col}:Q', title=target_col),
                    tooltip=['體型', '總讚數', '文章數']
                ).properties(height=350)
                # ✨ 升級為 width='stretch'
                st.altair_chart(chart3, width='stretch')
            else:
                st.info("無體型偏好資料")
                
        with col4:
            st.subheader("4. 常駐玩法回饋")
            if data.get("mode_sentiment"):
                df_m = pd.DataFrame.from_dict(data["mode_sentiment"], orient='index')
                df_m['文章數'] = df_m.index.map(data.get("mode_counts", {}))
                
                sentiment_cols = [col for col in ['Positive', 'Neutral', 'Negative', '正面', '中性', '負面', 'positive', 'neutral', 'negative'] if col in df_m.columns]
                df_m['總讚數'] = df_m[sentiment_cols].sum(axis=1)
                
                target_col = "總讚數" if display_metric == "讚數 (熱度)" else "文章數"
                
                if sort_option == "由高到低": df_m = df_m.sort_values(by=target_col, ascending=False)
                elif sort_option == "由低到高": df_m = df_m.sort_values(by=target_col, ascending=True)
                elif sort_option == "依名稱": df_m = df_m.sort_index()
                
                mode_order = df_m.index.tolist()
                
                if display_metric == "讚數 (熱度)":
                    df_m_plot = df_m.drop(columns=['總讚數', '文章數']).reset_index().melt(id_vars='index', var_name='情緒', value_name='數值')
                    chart4 = alt.Chart(df_m_plot).mark_bar().encode(
                        x=alt.X('index:N', sort=mode_order, title=''),
                        y=alt.Y('數值:Q', title='總讚數'),
                        color=alt.Color('情緒:N', scale=sentiment_scale)
                    ).properties(height=350)
                else:
                    df_m_plot = df_m[['文章數']].reset_index().rename(columns={'文章數': '數值'})
                    chart4 = alt.Chart(df_m_plot).mark_bar(color='#1f77b4').encode(
                        x=alt.X('index:N', sort=mode_order, title=''),
                        y=alt.Y('數值:Q', title='被提及的文章數'),
                        tooltip=['index', '數值']
                    ).properties(height=350)
                    
                # ✨ 升級為 width='stretch'
                st.altair_chart(chart4, width='stretch')
            else:
                st.info("無常駐玩法資料")

        st.markdown("---")
        
        # ==========================================
        # 🌟 第三排：圖表 5 (動態呼叫預測模組)
        # ==========================================
        st.subheader("5. 🔮 未來版本流量預測趨勢 (LightGBM)")
        
        target_v_input = st.text_input("輸入欲預測的版本號 (留白則自動預測下一版)：", "")
        
        if st.button("啟動 AI 模型運算", type="primary"):
            with st.spinner("🧠 正在呼叫 predictor_test 進行機器學習運算..."):
                try:
                    url = f"{API_BASE_URL}/api/predict"
                    if target_v_input: url += f"?version={target_v_input}"
                    
                    pred_res = requests.get(url)
                    if pred_res.status_code == 200:
                        pred_data = pred_res.json()
                        if pred_data.get("status") == "success":
                            x_hist = pred_data["plot_data"]["x_hist"]
                            y_hist = pred_data["plot_data"]["y_hist"]
                            x_train = pred_data["plot_data"]["x_train"]
                            y_fit = pred_data["plot_data"]["y_fit"]
                            next_v = pred_data["target_version"]
                            pred_y = pred_data["predicted_likes"]

                            fig, ax = plt.subplots(figsize=(12, 6))
                            ax.plot(x_hist, y_hist, marker='o', markersize=8, linestyle='-', linewidth=2.5, label='實際平均按讚數', color='#1f77b4', zorder=3)
                            ax.plot(x_train, y_fit, linestyle='--', linewidth=2, label='LightGBM 擬合趨勢', color='#ff7f0e', alpha=0.7)
                            ax.scatter(next_v, pred_y, color='red', marker='*', s=300, label=f'預測版本 {next_v}', zorder=5)

                            ax.annotate(f"預測: {pred_y:.1f}", (next_v, pred_y), xytext=(0, 15), textcoords="offset points", ha='center', bbox=dict(boxstyle='round,pad=0.3', fc='yellow', alpha=0.6), color='red', weight='bold')

                            all_ticks = sorted(list(set(x_hist + [next_v])))
                            ax.set_xticks(all_ticks)
                            ax.set_xticklabels([f"V{v}" for v in all_ticks], rotation=45)

                            ax.set_title("版本流量全覽與 LightGBM 未來預測", fontsize=16)
                            ax.set_xlabel("版本號 (Version)")
                            ax.set_ylabel("平均按讚數 (Likes)")
                            ax.grid(True, linestyle=':', alpha=0.5)
                            ax.legend()
                            plt.tight_layout()

                            st.pyplot(fig)
                            st.success(f"✅ 模型運算完成！預估版本 {next_v} 的平均按讚數為 **{pred_y} 讚**。")
                        else:
                            st.error(f"❌ 預測失敗：{pred_data.get('message')}")
                    else:
                        st.error("API 伺服器錯誤。")
                except Exception as e:
                    st.error(f"連線異常：{e}")

    else:
        st.error("API 回傳失敗，請確認 generate_summary.py 已經產生檔案。")

except requests.exceptions.ConnectionError:
    st.error("無法連線到 API 伺服器！請確認另一個終端機是否有執行 `uvicorn api_server:app --reload`")