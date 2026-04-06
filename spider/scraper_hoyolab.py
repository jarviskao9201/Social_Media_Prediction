import asyncio
import pandas as pd
from playwright.async_api import async_playwright

async def clean_ui(page):
    """清除遮罩與彈窗，確保捲動順暢"""
    await page.evaluate("""() => {
        const masks = ['.mhy-login-modal', '.mhy-modal-mask', '.mhy-dialog__wrapper', '[class*="mask"]'];
        masks.forEach(s => document.querySelectorAll(s).forEach(el => el.remove()));
        document.body.style.overflow = 'auto';
    }""")

async def scrape_article_details(context, analyzer, url):
    """
    進入文章內頁，抓取標題、內容、留言及其讚數。
    回傳：包含 [文章標題, 文章內容, 文章讚數, 留言數, 留言內容, 留言讚數, 語言, 情緒標籤, 信心值, URL] 的 DataFrame
    """
    page = await context.new_page()
    try:
        print(f"📖 進入文章: {url}")
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(4)
        await clean_ui(page)

        # 1. 抓取文章元數據 (新增標題抓取)
        meta_data = await page.evaluate("""() => {
            const stats = document.querySelectorAll('.mhy-article-page-stats__item');
            const totalText = stats[0]?.innerText.trim() || "0";
            
            // 抓取文章標題
            const titleEl = document.querySelector('.mhy-article-page__title') || 
                           document.querySelector('.mhy-news-card__title') ||
                           document.querySelector('h1');
            
            return {
                title: titleEl?.innerText.trim() || "無標題",
                content: document.querySelector('.mhy-article-page__content')?.innerText.trim() || "無內容",
                comment_total: totalText,
                comment_total_num: parseInt(totalText.replace(/[^0-9]/g, '')) || 0,
                likes: stats[2]?.innerText.trim() || "0"
            };
        }""")

        target_total = meta_data['comment_total_num']
        print(f"🎯 文章: {meta_data['title']} | 目標留言: {target_total}")

        # 2. 全量抓取邏輯 (使用字典確保內容唯一且保留最高讚數)
        captured_data = {}
        no_new_data_streak = 0
        scroll_count = 0

        while len(captured_data) < target_total:
            scroll_count += 1
            current_batch = await page.evaluate("""() => {
                const results = [];
                const selectors = ['.mhy-comment-card', '.mhy-article-comment-card', '.reply-card', '.mhy-comment-list__item'];
                let nodes = [];
                selectors.forEach(s => { document.querySelectorAll(s).forEach(el => nodes.push(el)); });
                const uniqueNodes = [...new Set(nodes)];

                uniqueNodes.forEach(node => {
                    const contentEl = node.querySelector('pre') || node.querySelector('[class*="content"]') || node.querySelector('.replyContentWrapperWithBubble');
                    const likeEl = node.querySelector('[class*="status-num"]') || node.querySelector('[class*="like-num"]') || node.querySelector('.mhy-like span');
                    
                    if (contentEl) {
                        let commentParts = [];
                        const images = contentEl.querySelectorAll('img.emoticon-image');
                        let hasImages = images.length > 0;
                        if (hasImages) {
                            images.forEach(img => {
                                const emojiId = img.getAttribute('data-id') || "unknown";
                                commentParts.push(`[貼圖ID:${emojiId}]`);
                            });
                        }
                        const textOnly = contentEl.innerText.trim();
                        let finalComment = textOnly + (textOnly && hasImages ? " " : "") + commentParts.join(" ");

                        if (finalComment.length > 0) {
                            let likeText = likeEl ? likeEl.innerText.trim() : "0";
                            let likeNum = likeText.includes('k') ? parseFloat(likeText.replace('k', '')) * 1000 : parseInt(likeText.replace(/[^0-9]/g, '')) || 0;
                            results.push({ text: finalComment, likes: likeNum });
                        }
                    }
                });
                return results;
            }""")

            old_count = len(captured_data)
            for item in current_batch:
                if item['text'] not in captured_data or item['likes'] > captured_data[item['text']]:
                    captured_data[item['text']] = item['likes']
            
            new_count = len(captured_data)
            
            # 滾動與點擊「查看更多」
            try:
                more_btn = page.get_by_text("查看更多", exact=False).first
                if await more_btn.is_visible():
                    await more_btn.click()
                    await asyncio.sleep(2)
            except: pass

            await page.evaluate("window.scrollBy(0, 2500)")
            await asyncio.sleep(2.5)

            # 停止條件判斷
            if new_count == old_count:
                no_new_data_streak += 1
            else:
                no_new_data_streak = 0
            
            if no_new_data_streak >= 15 or scroll_count > 400: break

        # 3. 排序、分析與資料整合
        if captured_data:
            # 依照讚數降序排序
            sorted_items = sorted(captured_data.items(), key=lambda x: x[1], reverse=True)
            df_base = pd.DataFrame(sorted_items, columns=['留言內容', '留言讚數'])

            print(f"✨ 正在進行 AI 分析 ({len(df_base)} 條)...")
            analysis_df = analyzer.analyze(df_base['留言內容'].tolist(), meta_data['title'])
            
            # 整合所有必要欄位
            analysis_df['留言讚數'] = df_base['留言讚數'].values
            analysis_df['文章標題'] = meta_data['title']
            analysis_df['文章內容'] = meta_data['content']
            analysis_df['文章讚數'] = meta_data['likes']
            analysis_df['留言數'] = meta_data['comment_total']
            analysis_df['URL'] = url
            
            # 確保輸出欄位順序正確
            cols = ['文章標題', '文章內容', '文章讚數', '留言數', '留言內容', '留言讚數', '語言', '情緒標籤', '信心值', 'URL','summary_keywords']
            return analysis_df[cols]
        
        return pd.DataFrame()

    except Exception as e:
        print(f"⚠️ 解析失敗 ({url}): {e}")
        return pd.DataFrame()
    finally:
        await page.close()