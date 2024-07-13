import json
import random

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright._impl._errors import TimeoutError as PlaywrightTimeoutError

from urllib.parse import quote


def load_cookies_from_file(file_path):
    with open(file_path, "r") as file:
        return json.load(file)


def set_cookies(page, cookies):
    for cookie in cookies:
        page.context.add_cookies([cookie])


def scrape_with_playwright():
    with sync_playwright() as p:
        # 启动浏览器，headless=False 使浏览器界面可见，便于调试
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # 读取 cookies.json 文件并设置 cookies
        cookies = load_cookies_from_file("cookies.json")
        set_cookies(page, cookies)
        # 搜索关键词
        keyword = "mac软件"
        # 关键词转为 url 编码
        keyword_temp_code = quote(keyword.encode('utf-8'))
        keyword_encode = quote(keyword_temp_code.encode('gb2312'))
        # 打开目标网页
        page.goto("https://www.xiaohongshu.com/search_result?keyword={}&source=web_explore_feed".format(keyword_encode))


        page.wait_for_timeout(random.randint(5000, 10000))

        # 开始抓取数据
        data = []

        for _ in range(25):
            # 获取到feed流元素
            element = page.locator(
                "#global > div.main-container > div.with-side-bar.main-content > div > div.feeds-container"
            )

            # 使用 BeautifulSoup 解析 HTML
            soup = BeautifulSoup(element.inner_html(), "lxml")

            # 示例：获取所有的段落文本
            notes = soup.select(".note-item[data-width]")
            for note in notes:
                title_element = note.select_one(".title > span")
                title = ""
                # 解决标题为空的问题
                if title_element is not None:
                    title = title_element.get_text()

                author = note.select_one(".name").get_text()
                author_link = "https://www.xiaohongshu.com" + note.select_one(
                    ".author"
                ).get("href")
                note_link = "https://www.xiaohongshu.com" + note.select_one(
                    ".cover"
                ).get("href")

                data.append(
                    {
                        "title": title,
                        "author": author,
                        "author_link": author_link,
                        "note_link": note_link,
                    }
                )

            # 滚动下拉
            page.evaluate(
                "window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });"
            )
            page.wait_for_timeout(random.randint(2000, 5000))

        # 使用字典推导式进行去重，以 'note_link' 为键，保留最后一个重复项
        unique_items = {item["note_link"]: item for item in data}.values()

        print(len(unique_items))

        # 转换回列表格式
        data = list(unique_items)

        page.wait_for_timeout(random.randint(5000, 10000))

        # 抓取用户和笔记数据
        for i, item in enumerate(data):
            print(f"第{i}行，数据:{item}")
            # 打开作者页面
            try:
                page.goto(item["author_link"], timeout=60000)
            except PlaywrightTimeoutError as e:
                print(f"页面加载超时: {e}")

            # 获取到作者信息元素
            element = page.locator("#userPageContainer > div.user > div")
            # 使用 BeautifulSoup 解析 HTML
            soup = BeautifulSoup(element.inner_html(), "lxml")
            author_desc_element = soup.select_one(".user-desc")
            data[i]["author_desc"] = ""
            if author_desc_element is not None:
                data[i]["author_desc"] = author_desc_element.get_text()

            data[i]["author_follows"] = soup.select_one(
                ".user-interactions div:nth-child(1) .count"
            ).get_text()
            data[i]["author_following"] = soup.select_one(
                ".user-interactions div:nth-child(2) .count"
            ).get_text()
            data[i]["author_likes_and_collects"] = soup.select_one(
                ".user-interactions div:nth-child(3) .count"
            ).get_text()

            page.wait_for_timeout(random.randint(5000, 10000))

            # 打开笔记页面
            try:
                page.goto(item["note_link"], timeout=60000)
            except PlaywrightTimeoutError as e:
                print(f"页面加载超时: {e}")

            # 获取到笔记元素
            element = page.locator("#noteContainer > div.interaction-container")
            # 使用 BeautifulSoup 解析 HTML
            soup = BeautifulSoup(element.inner_html(), "lxml")

            collect_element = soup.select_one(".collect-wrapper .count")
            if collect_element.has_attr('selected-disabled-search'):
                data[i]["note_collects"] = None
            else:
                data[i]["note_collects"] = collect_element.get_text()

            # 处理评论数
            comment_element = soup.select_one(".chat-wrapper .count")
            if comment_element.has_attr('selected-disabled-search'):
                data[i]["note_comments"] = None
            else:
                data[i]["note_comments"] = comment_element.get_text()   
            like_element = soup.select_one(".like-wrapper.like-active .count")
            if like_element.has_attr('selected-disabled-search'):
                data[i]["note_likes"] = None
            else:
                data[i]["note_likes"] = like_element.get_text()
            
            data[i]["note_date"] = soup.select_one(".bottom-container .date").get_text()
            data[i]["note_content"] = soup.select_one("#detail-desc > span").get_text()
            tag_elements = soup.select("#detail-desc .tag")
            tag_list = []
            for _, tag_element in enumerate(tag_elements):
                tag = (
                    tag_element.get_text(strip=True)
                    .replace("话题可以点击搜索啦~", "")
                    .replace("#", "")
                )
                tag_list.append(tag)
            data[i]["tags"] = ",".join(tag_list)

            page.wait_for_timeout(random.randint(5000, 10000))

            df = pd.DataFrame(data)
            file_path = "/Users/yutian/Desktop/df_mac软件.csv"  
            df.to_csv(file_path, index=False, encoding='utf-8-sig')

        # 关闭浏览器
        browser.close()


if __name__ == "__main__":
    scrape_with_playwright()

    

