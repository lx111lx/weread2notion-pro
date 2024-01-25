import argparse
import hashlib
import json
import os

import pendulum
import requests
from notion_helper import NotionHelper

from weread_api import WeReadApi
import utils
from config import (
    book_properties_type_dict,
)
from retrying import retry
from config import TAG_ICON_URL, USER_ICON_URL, BOOK_ICON_URL


rating = {"poor": "🟊", "fair": "🟊🟊🟊", "good": "🟊🟊🟊🟊🟊"}


@retry(stop_max_attempt_number=3, wait_fixed=5000)
def get_douban_url(isbn):
    print(f"get_douban_url {isbn} ")
    params = {"query": isbn, "page": "1", "category": "book"}
    r = requests.get("https://neodb.social/api/catalog/search", params=params)
    books = r.json().get("data")
    if books is None or len(books) == 0:
        return None
    results = list(filter(lambda x: x.get("isbn") == isbn, books))
    if len(results) == 0:
        return None
    result = results[0]
    urls = list(
        filter(
            lambda x: x.get("url").startswith("https://book.douban.com"),
            result.get("external_resources", []),
        )
    )
    if len(urls) == 0:
        return None
    return urls[0].get("url")


def insert_book_to_notion(books, index, bookId):
    """插入Book到Notion"""
    book = {}
    if bookId in archive_dict:
        book["BookShelf"] = archive_dict.get(bookId)
    if bookId in notion_books:
        book.update(notion_books.get(bookId))
    bookInfo = weread_api.get_bookinfo(bookId)
    if bookInfo != None:
        book.update(bookInfo)
    readInfo = weread_api.get_read_info(bookId)
    # 研究了下这个状态不知道什么情况有的虽然读了状态还是1 markedStatus = 1 想读 4 读完 其他为在读
    readInfo.update(readInfo.get("readDetail", {}))
    readInfo.update(readInfo.get("bookInfo", {}))
    book.update(readInfo)
    cover = book.get("cover")
    if cover.startswith("http"):
        if not cover.endswith(".jpg"):
            cover = utils.upload_cover(cover)
        else:
            cover = cover.replace("/s_", "/t7_")
    else:
        cover = BOOK_ICON_URL
    isbn = book.get("isbn")
    if isbn and isbn.strip():
        douban_url = get_douban_url(isbn)
        if douban_url:
            book["douban_url"] = douban_url
    book["Cover"] = cover
    book["Progress"] = (
        100 if (book.get("markedStatus") == 4) else book.get("readingProgress", 0)
    ) / 100
    markedStatus = book.get("markedStatus")
    status = "Wishlist"
    if markedStatus == 4:
        status = "Read"
    elif book.get("readingTime", 0) >= 60:
        status = "Reading"
    book["Status"] = status
    book["ReadTime"] = book.get("readingTime")
    book["ReadDays"] = book.get("totalReadDay")
    book["Scores"] = book.get("newRating")
    if book.get("newRatingDetail") and book.get("newRatingDetail").get("myRating"):
        book["Grade"] = rating.get(book.get("newRatingDetail").get("myRating"))
    elif status == "Read":
        book["Grade"] = "-"
    date = None
    if book.get("finishedDate"):
        date = book.get("finishedDate")
    elif book.get("lastReadingDate"):
        date = book.get("lastReadingDate")
    elif book.get("readingBookDate"):
        date = book.get("readingBookDate")
    book["Time"] = date
    book["Started Time"] = book.get("beginReadingDate")
    book["Last Time"] = book.get("lastReadingDate")
    if bookId not in notion_books:
        book["BooksName"] = book.get("title")
        book["BookId"] = book.get("bookId")
        book["ISBN"] = book.get("isbn")
        book["Resource"] = utils.get_weread_url(bookId)
        book["Synopsis"] = book.get("intro")
        book["Author"] = [
            notion_helper.get_relation_id(
                x, notion_helper.author_database_id, USER_ICON_URL
            )
            for x in book.get("author").split(" ")
        ]
        if book.get("categories"):
            book["Categories"] = [
                notion_helper.get_relation_id(
                    x.get("title"), notion_helper.category_database_id, TAG_ICON_URL
                )
                for x in book.get("categories")
            ]
    properties = utils.get_properties(book, book_properties_type_dict)
    if book.get("date"):
        notion_helper.get_date_relation(
            properties,
            pendulum.from_timestamp(book.get("date"), tz="Asia/Shanghai"),
        )

    print(f"正在插入《{book.get('title')}》,一共{len(books)}本，当前是第{index+1}本。")
    parent = {"database_id": notion_helper.book_database_id, "type": "database_id"}
    if bookId in notion_books:
        notion_helper.update_page(
            page_id=notion_books.get(bookId).get("pageId"),
            properties=properties,
            icon=utils.get_icon(book.get("cover")),
        )
    else:
        notion_helper.create_page(
            parent=parent,
            properties=properties,
            icon=utils.get_icon(book.get("cover")),
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    options = parser.parse_args()
    weread_cookie = os.getenv("WEREAD_COOKIE")
    branch = os.getenv("REF").split("/")[-1]
    repository = os.getenv("REPOSITORY")
    weread_api = WeReadApi()
    notion_helper = NotionHelper()
    notion_books = notion_helper.get_all_book()
    bookshelf_books = weread_api.get_bookshelf()
    bookProgress = bookshelf_books.get("bookProgress")
    bookProgress = {book.get("bookId"): book for book in bookProgress}
    archive_dict = {}
    for archive in bookshelf_books.get("archive"):
        name = archive.get("name")
        bookIds = archive.get("bookIds")
        archive_dict.update({bookId: name for bookId in bookIds})
    not_need_sync = []
    for key, value in notion_books.items():
        if (
            (
                key not in bookProgress
                or value.get("readingTime") == bookProgress.get(key).get("readingTime")
            )
            and (archive_dict.get(key) == value.get("category"))
            and value.get("cover")
            and (not value.get("cover").endswith("/0.jpg"))
            and (not value.get("cover").endswith("parsecover"))
            and (
                value.get("status") != "Read"
                or (value.get("status") == "Read" and value.get("myRating"))
            )
        ):
            not_need_sync.append(key)
    notebooks = weread_api.get_notebooklist()
    notebooks = [d["bookId"] for d in notebooks if "bookId" in d]
    books = bookshelf_books.get("books")
    books = [d["bookId"] for d in books if "bookId" in d]
    books = list((set(notebooks) | set(books)) - set(not_need_sync))
    for index, bookId in enumerate(books):
        insert_book_to_notion(books, index, bookId)
