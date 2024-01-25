import json
import os
import pendulum

import requests
from notion_helper import NotionHelper
from config import TAG_ICON_URL, USER_ICON_URL, BOOK_ICON_URL, book_properties_type_dict
import utils

DOUBAN_API_HOST = os.getenv("DOUBAN_API_HOST", "frodo.douban.com")
DOUBAN_API_KEY = os.getenv("DOUBAN_API_KEY", "0ac44ae016490db2204ce0a042db2916")
rating = {
    1: "⭐️",
    2: "⭐️⭐️",
    3: "⭐️⭐️⭐️",
    4: "⭐️⭐️⭐️⭐️",
    5: "⭐️⭐️⭐️⭐️⭐️",
}
status = {
    "mark": "想读",
    "doing": "在读",
    "done": "已读",
}
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
headers = {
    "host": DOUBAN_API_HOST,
    "authorization": f"Bearer {AUTH_TOKEN}" if AUTH_TOKEN else "",
    "user-agent": "User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 15_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.16(0x18001023) NetType/WIFI Language/zh_CN",
    "referer": "https://servicewechat.com/wx2f9b06c1de1ccfca/84/page-frame.html",
}


def fetch_subjects(user, type_, status):
    offset = 0
    page = 0
    url = f"https://{DOUBAN_API_HOST}/api/v2/user/{user}/interests"
    total = 0
    results = []
    has_next = True
    while has_next:
        params = {
            "type": type_,
            "count": 50,
            "status": status,
            "start": offset,
            "apiKey": DOUBAN_API_KEY,
        }
        response = requests.get(url, headers=headers, params=params)
        response = response.json()
        results.extend(response.get("interests"))
        total = response.get("total")
        print(total)
        page += 1
        offset = page * 50
        has_next = len(results) < total
    return results


if __name__ == "__main__":
    douban_name = os.getenv("DOUBAN_NAME",None)
    if douban_name and douban_name.strip():
        notion_helper = NotionHelper()
        results = []
        notion_books = notion_helper.get_all_book()
        notion_books = {value.get("douban_url"):value for value in notion_books.values()}
        for i in status.keys():
            results.extend(fetch_subjects(douban_name, "book", i))
        for result in results:
            book = {}
            subject = result.get("subject")
            url = subject.get("url")
            """获取评论"""
            comment = result.get("comment")
            if url in notion_books:
                """如果评论不为空并且和notion中的豆瓣短评不同则更新"""
                if (comment and comment.strip()) and comment != notion_books.get(url).get("comment"):
                    book["豆瓣短评"] = result.get("comment")
                    properties = utils.get_properties(book, book_properties_type_dict)
                    notion_helper.update_pag2(
                        page_id=notion_books.get(url).get("pageId"),
                        properties=properties,
                    )
                    continue
            book["豆瓣链接"] = url
            book["书名"] = subject.get("title")
            book["简介"] = subject.get("intro")
            book["豆瓣短评"] = comment
            book["阅读状态"] = status.get(subject.get("status"))
            if result.get("rating"):
                book["我的评分"] = rating(result.get("rating").get("value"))
            book["作者"] = [
                notion_helper.get_relation_id(
                    x, notion_helper.author_database_id, USER_ICON_URL
                )
                for x in subject.get("author")
            ]
            if len(result.get("tags")) > 0:
                book["分类"] = [
                    notion_helper.get_relation_id(
                        x, notion_helper.category_database_id, TAG_ICON_URL
                    )
                    for x in result.get("tags")
                ]
            date_format = "YYYY-MM-DD HH:mm:ss"
            dt = pendulum.from_format(
                result.get("create_time"), date_format, tz="Asia/Shanghai"
            )
            book["日期"] = dt.int_timestamp
            book["封面"] = subject.get("cover_url")
            properties = utils.get_properties(book, book_properties_type_dict)
            if book.get("日期"):
                notion_helper.get_date_relation(
                    properties,
                    pendulum.from_timestamp(book.get("日期"), tz="Asia/Shanghai"),
                )
            parent = {"database_id": notion_helper.book_database_id, "type": "database_id"}
            notion_helper.create_page(
                parent=parent,
                properties=properties,
                icon=utils.get_icon(subject.get("cover_url")),
            )
