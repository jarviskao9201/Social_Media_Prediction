import re

class KeywordLabeller:
    def __init__(self):
        self.tag_rules = {
            '活動': ['差分宇宙','Divergent Universe','模擬宇宙','Simulated Universe','貨幣戰爭','Currency Wars'],
            '角色':['角色預告','Character Trailer','角色預覽','Character Preview','角色介紹','Character Introduction'],  
            '1.0': ['1.0', '通往群星的軌道','The Rail Unto the Stars'],
            '1.1': ['1.1','銀河漫遊','Galactic Roaming'],
            '1.2': ['1.2','仙骸有終','Even Immortality Ends'],
            '1.3': ['1.3','天鏡映劫塵','Celestial Eyes Above Mortal Ruins'],
            '1.4': ['1.4','冬夢激醒','Jolted Awake From a Winter Dream'],
            '1.5': ['1.5','迷離幻夜談','The Crepuscule Zone'],
            '1.6': ['1.6','庸與神的冠冕','Crown of the Mundane and Divine'],
            '2.0': ['2.0','假如在午夜入夢','If One Dreams At Midnight'], 
            '2.1': ['2.1','狂熱奔向深淵','Into the Yawning Chasm'],
            '2.2': ['2.2','等醒來再哭泣','Then Wake to Weep'],
            '2.3': ['2.3','再見，匹諾康尼','Farewell, Penacony'],
            '2.4': ['2.4','明霄競武試鋒芒','Finest Duel Under the Pristine Blue'],
            '2.5': ['2.5','碧羽飛黃射天狼','Flying Aureus Shot to Lupine Rue'],
            '2.6': ['2.6','毗乃昆尼末法世記',"Annals of Pinecany's Mappou Age"],
            '2.7': ['2.7','在第八日啟程','A New Venture on the Eighth Dawn'],
            '3.0': ['3.0','再創世的凱歌','Paean of Era Nova'],
            '3.1': ['3.1','門扉之啟，王座之終','Light Slips the Gate, Shadow Greets the Throne'],
            '3.2': ['3.2','走過安眠地的花叢','Through the Petals in the Land of Repose'],
            '3.3': ['3.3','在黎明升起時墜落',"The Fall at Dawn's Rise"],
            '3.4': ['3.4','因為太陽將要毀傷','For the Sun is Set to Die'],
            '3.5': ['3.5','英雄未死之前','Before Their Deaths'],
            '3.6': ['3.6','於長夜重返大地','Back to Earth in Evernight'],
            '3.7': ['3.7','成為昨日的明天','最漫長的一夜','As Tomorrow Became Yesterday'],
            '3.8': ['3.8','記憶是夢的開場白','Memories are the Prelude to Dreams'],
            '4.0': ['4.0','滿月是神不在的時間','No Aha At Full Moon'],
            '4.1': ['4.1','獻給破曉的失控','Unraveled for Daybreak'],

            '成年男': ['Archer','銀枝','银枝','Argenti','不死途','Ashveil','刃','Blade','波提歐','波提欧','Boothill','真理醫生','真理医生','Dr. Ratio','傑帕德','杰帕德','Gepard','景元','Jing Yuan','羅剎','罗刹','Luocha','萬敵','万敌','Mydei','白厄','Phainon','瓦爾特','瓦尔特','Welt'],
            '青年男': ['那刻夏','Anaxa','砂金','Aventurine','丹恒','丹恆','Dan Heng','椒丘','Jiaoqiu','星期日','Sunday'],
            '少年男': ['彥卿','彦卿','Yanqing'],
            '成年女': ['黃泉','Acheron','阿格萊雅','阿格莱雅','Aglaea','黑天鹅','黑天鵝','Black Swan','飛霄','飞霄','Feixiao','姬子','Himeko','翡翠','翡翠','Jade','卡芙卡','Kafka','大理花','大丽花','The Dahlia'],
            '青年女': ['布洛妮婭','布洛妮娅','Bronya','遐蝶','遐蝶','Castorice','賽飛兒','赛飞儿','Cipher','昔漣','昔涟','Cyrene','长夜月','長夜月','Evernight','流螢','流萤','Firefly','忘歸人','忘归人','Fugue','海瑟音','Hysilens','鏡流','镜流','Jingliu','靈砂','灵砂','Lingsha','亂破','乱破','Rappa','知更鳥','知更鸟','Robin','阮•梅','阮梅''Ruan Mei','Saber','希兒','希儿','Seele','大黑塔','大黑塔','The Herta','托帕&帳帳','托帕&账账','Topaz & Numby','爻光','Yao Guang'],
            '少年女': ['刻律德菈','Cerydra','克拉拉','Clara','符玄','Fu Xuan','藿藿','Huohuo','風堇','风堇','Hyacine','銀狼','银狼','Silver Wolf','花火','Sparkle','火花','Sparxie','雲璃','	云璃','Yunli'],
            '幼年女': ['白露','Bailu','缇宝','緹寶','Tribbie']
        }

    def get_labels(self, title):
        if not title:
            return "一般討論"
            
        matched_tags = []
        # 確保轉成字串並去除空白
        clean_title = str(title).strip()
        
        # 直接使用字串包含比對，這比正則表達式更穩
        for tag_name, keywords in self.tag_rules.items():
            for kw in keywords:
                if kw in clean_title:
                    matched_tags.append(tag_name)
                    break # 只要該分類中有一種關鍵字對中，就跳到下個分類
        
        # 輸出除錯訊息，讓你在終端機看到結果
        res = ",".join(matched_tags) if matched_tags else "一般討論"
        print(f"DEBUG - 標題: {clean_title} | 匹配結果: {res}")
        
        return res