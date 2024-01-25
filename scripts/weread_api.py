import hashlib
from http.cookies import SimpleCookie
import os
import re

import requests
from requests.utils import cookiejar_from_dict
from http.cookies import SimpleCookie
from retrying import retry
WEREAD_URL = "https://weread.qq.com/"
WEREAD_NOTEBOOKS_URL = "https://i.weread.qq.com/user/notebooks"
WEREAD_BOOKMARKLIST_URL = "https://i.weread.qq.com/book/bookmarklist"
WEREAD_CHAPTER_INFO = "https://i.weread.qq.com/book/chapterInfos"
WEREAD_READ_INFO_URL = "https://i.weread.qq.com/book/readinfo"
WEREAD_REVIEW_LIST_URL = "https://i.weread.qq.com/review/list"
WEREAD_BOOK_INFO = "https://i.weread.qq.com/book/info"
WEREAD_READDATA_DETAIL = "https://i.weread.qq.com/readdata/detail"
WEREAD_HISTORY_URL = "https://i.weread.qq.com/readdata/summary?synckey=0"

class WeReadApi:
    def __init__(self):
        self.cookie = os.getenv("WEREAD_COOKIE")
        self.session = requests.Session()
        self.session.cookies = self.parse_cookie_string()

    def parse_cookie_string(self):
        cookie = SimpleCookie()
        cookie.load(self.cookie)
        cookies_dict = {}
        cookiejar = None
        for key, morsel in cookie.items():
            cookies_dict[key] = morsel.value
            cookiejar = cookiejar_from_dict(
                cookies_dict, cookiejar=None, overwrite=True
            )
        return cookiejar
    
    def get_bookshelf(self):
        self.session.get(WEREAD_URL)
        r = self.session.get("https://i.weread.qq.com/shelf/sync?synckey=0&teenmode=0&album=1&onlyBookid=0")
        if r.ok:
            return r.json()
        else:
            raise Exception(f"Could not get bookshelf {r.text}")

    @retry(stop_max_attempt_number=3, wait_fixed=5000)
    def get_notebooklist(self):
        """获取笔记本列表"""
        self.session.get(WEREAD_URL)
        r = self.session.get(WEREAD_NOTEBOOKS_URL)
        if r.ok:
            data = r.json()
            books = data.get("books")
            books.sort(key=lambda x: x["sort"])
            return books
        else:
            raise Exception(f"Could not get notebook list {r.text}")

    @retry(stop_max_attempt_number=3, wait_fixed=5000)
    def get_bookinfo(self, bookId):
        """获取书的详情"""
        self.session.get(WEREAD_URL)
        params = dict(bookId=bookId)
        r = self.session.get(WEREAD_BOOK_INFO, params=params)
        if r.ok:
            return r.json()
        else:
            return None

    @retry(stop_max_attempt_number=3, wait_fixed=5000)
    def get_bookmark_list(self, bookId):
        self.session.get(WEREAD_URL)
        params = dict(bookId=bookId)
        r = self.session.get(WEREAD_BOOKMARKLIST_URL, params=params)
        if r.ok:
            bookmarks = r.json().get("updated")
            return bookmarks
        else:
            raise Exception(f"Could not get {bookId} bookmark list")

    @retry(stop_max_attempt_number=3, wait_fixed=5000)
    def get_read_info(self, bookId):
        self.session.get(WEREAD_URL)
        params = dict(
            bookId=bookId, readingDetail=1, readingBookIndex=1, finishedDate=1
        )
        r = self.session.get(WEREAD_READ_INFO_URL, params=params)
        if r.ok:
            return r.json()
        else:
            raise Exception(f"get {bookId} read info failed {r.text}")

    @retry(stop_max_attempt_number=3, wait_fixed=5000)
    def get_review_list(self, bookId):
        self.session.get(WEREAD_URL)
        params = dict(bookId=bookId, listType=11, mine=1, syncKey=0)
        r = self.session.get(WEREAD_REVIEW_LIST_URL, params=params)
        if r.ok:
            reviews = r.json().get("reviews")
            reviews = list(map(lambda x: x.get("review"), reviews))
            reviews = [
                {"chapterUid": 1000000, **x} if x.get("type") == 4 else x
                for x in reviews
            ]
            return reviews
        else:
            raise Exception(f"get {bookId} review list failed {r.text}")
        
    @retry(stop_max_attempt_number=3, wait_fixed=5000) 
    def get_api_data(self):
        r = self.session.get(WEREAD_HISTORY_URL)
        if not r.ok:
            if r.json()["errcode"] == -2012:
                self.session.get(WEREAD_URL)
                r = self.session.get(WEREAD_HISTORY_URL)
            else:
                raise Exception("Can not get weread history data")
        return r.json()
    
    @retry(stop_max_attempt_number=3, wait_fixed=5000) 
    def get_chapter_info(self,bookId):
        self.session.get(WEREAD_URL)
        body = {"bookIds": [bookId], "synckeys": [0], "teenmode": 0}
        r = self.session.post(WEREAD_CHAPTER_INFO, json=body)
        if (
            r.ok
            and "data" in r.json()
            and len(r.json()["data"]) == 1
            and "updated" in r.json()["data"][0]
        ):
            update = r.json()["data"][0]["updated"]
            update.append(
                {
                    "chapterUid": 1000000,
                    "chapterIdx": 1000000,
                    "updateTime": 1683825006,
                    "readAhead": 0,
                    "title": "Comment",
                    "level": 1,
                }
            )
            return {item["chapterUid"]: item for item in update}
        else:
            raise Exception(f"get {bookId} chapter info failed {r.text}")
        
    def transform_id(self,book_id):
        id_length = len(book_id)
        if re.match("^\d*$", book_id):
            ary = []
            for i in range(0, id_length, 9):
                ary.append(format(int(book_id[i : min(i + 9, id_length)]), "x"))
            return "3", ary

        result = ""
        for i in range(id_length):
            result += format(ord(book_id[i]), "x")
        return "4", [result]


    def calculate_book_str_id(self,book_id):
        md5 = hashlib.md5()
        md5.update(book_id.encode("utf-8"))
        digest = md5.hexdigest()
        result = digest[0:3]
        code, transformed_ids = self.transform_id(book_id)
        result += code + "2" + digest[-2:]

        for i in range(len(transformed_ids)):
            hex_length_str = format(len(transformed_ids[i]), "x")
            if len(hex_length_str) == 1:
                hex_length_str = "0" + hex_length_str

            result += hex_length_str + transformed_ids[i]

            if i < len(transformed_ids) - 1:
                result += "g"

        if len(result) < 20:
            result += digest[0 : 20 - len(result)]

        md5 = hashlib.md5()
        md5.update(result.encode("utf-8"))
        result += md5.hexdigest()[0:3]
        return result
    def get_url(self,book_id):
        return f"https://weread.qq.com/web/reader/{self.calculate_book_str_id(book_id)}"
