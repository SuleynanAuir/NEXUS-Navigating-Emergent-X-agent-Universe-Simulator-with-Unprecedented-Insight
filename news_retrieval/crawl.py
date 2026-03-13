import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

def crawl_content(urls):
    """
    批量爬取URL内容，使用BeautifulSoup提取正文。
    添加重试和User-Agent。
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    articles = []
    for url_data in urls:
        try:
            response = requests.get(url_data['url'], headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # 尝试提取标题
            title = soup.find('title').get_text() if soup.find('title') else url_data.get('title', '未知标题')

            # 尝试提取正文（查找常见标签）
            text = ""
            for tag in soup.find_all(['p', 'div']):
                if tag.get_text().strip() and len(tag.get_text().strip()) > 20:  # 过滤短文本
                    text += tag.get_text().strip() + "\n"

            # 如果没有找到，提取body文本
            if not text:
                body = soup.find('body')
                text = body.get_text() if body else "无法提取内容"

            articles.append({
                'title': title,
                'text': text[:5000],  # 限制长度
                'url': url_data['url'],
                'publish_date': str(datetime.now()),  # 简化，实际可解析meta
                'authors': []  # 简化
            })
            time.sleep(1)  # 延时避免被封
        except Exception as e:
            print(f"爬取失败: {url_data['url']} - {e}")
            continue
    return articles

if __name__ == "__main__":
    urls = [{'url': 'https://example.com/news1'}, {'url': 'https://example.com/news2'}]
    contents = crawl_content(urls)
    print(contents)