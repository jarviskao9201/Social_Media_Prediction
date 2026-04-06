from transformers import pipeline, AutoTokenizer
import pandas as pd
from langdetect import detect, DetectorFactory
from label_manager import KeywordLabeller # 匯入新檔案

DetectorFactory.seed = 0 # 確保結果穩定

class SentimentAnalyzer:
    def __init__(self):
        self.labeller = KeywordLabeller()
        print("🤖 分析器已掛載關鍵字標籤功能")
        print("⏳ 正在啟動 XLM-RoBERTa 與 全球語系偵測引擎...")
        self.model_path = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
        tokenizer = AutoTokenizer.from_pretrained(self.model_path, use_fast=False)
        
        self.sentiment_task = pipeline(
            "sentiment-analysis", 
            model=self.model_path, 
            tokenizer=tokenizer
        )
        
        self.label_map = {"Positive": "正面", "Neutral": "中性", "Negative": "負面"}
        
        # 💡 大幅擴充的語言代碼地圖
        self.lang_map = {
            # 亞洲語系
            'zh-cn': '簡體中文', 'zh-tw': '繁體中文', 'zh': '中文',
            'ja': '日文', 'ko': '韓文', 'th': '泰文', 'vi': '越南文',
            'id': '印尼文', 'ms': '馬來文', 'tl': '菲律賓文',
            
            # 歐洲語系
            'en': '英文', 'ru': '俄文', 'fr': '法文', 'de': '德文',
            'es': '西班牙文', 'pt': '葡萄牙文', 'it': '義大利文',
            'nl': '荷蘭文', 'pl': '波蘭文', 'tr': '土耳其文',
            
            # 其他
            'ar': '阿拉伯文', 'hi': '印地文'
        }

    def get_language(self, text):
        # 如果是純表情符號或數字，偵測會報錯，所以加個長度檢查
        if not text or len(text.strip()) < 2:
            return "表情/符號"
            
        try:
            lang_code = detect(text)
            # 回傳對應名稱，如果不在地圖裡就回傳原始代碼
            return self.lang_map.get(lang_code, f"其他({lang_code})")
        except:
            return "偵測失敗"

    def analyze(self, comments , article_title):
            if not comments: 
                return pd.DataFrame()
            try:
            # 取得情緒預測結果
                predictions = self.sentiment_task(comments,truncation=True,max_length=512)
            except Exception as e:
                print(f"⚠️ 分析失敗: {e}")
                return pd.DataFrame()  
            data = []      
            for text, pred in zip(comments, predictions):
                data.append({
                    "留言內容": text,
                    "語言": self.get_language(text),
                    "情緒標籤": self.label_map.get(pred['label'], pred['label']),
                    "信心值": round(pred['score'], 4),
                })
            df = pd.DataFrame(data)
            # 【檢查重點】：這裡必須是 article_title
                    # 確保 self.labeller 已經在 __init__ 被實例化
            print(f"🔍 分析完成，正在套用關鍵字標籤... (文章標題: {article_title})")
            df['summary_keywords'] = self.labeller.get_labels(article_title)
            return df