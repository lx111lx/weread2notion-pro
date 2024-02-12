import argparse
import os
import requests

from notion_helper import NotionHelper
from weread_api import WeReadApi

from utils import (
    get_callout,
    get_heading,
    get_number,
    get_number_from_result,
    get_quote,
    get_rich_text_from_result,
    get_table_of_contents,
)


def get_bookmark_list(page_id, bookId):
    """获取我的划线"""
    filter = {"property": "Books", "relation": {"contains": page_id}}

    """notion_helper.query_all_by_book函数传入了两个参数，一个是查询到的数据库id，另一个是筛选条件"""
    results = notion_helper.query_all_by_book(
        notion_helper.bookmark_database_id, filter
    )
    """
    从上面筛选到的结果中，以富文本的形式提取的"blockId"循环赋值给 同样提取到的"bookmarkId"，并将每次循环的键和值构建成一个临时字典
    """
    dict1 = {
        get_rich_text_from_result(x, "bookmarkId"): get_rich_text_from_result(
            x, "blockId"
        )
        for x in results
    }
    """
    将通过notion API获取到的"id"循环赋值给上面以富文本的形式提取的"blockId"，并将每次循环的键和值构建成一个临时字典
    """
    dict2 = {get_rich_text_from_result(x, "blockId"): x.get("id") for x in results}
    bookmarks = weread_api.get_bookmark_list(bookId)
    for i in bookmarks:
        """
        如果notion API获取到的"bookmarkId"键存在临时字典dict1的键中，则从dict1中移除这个对应的键值对，
        并且把这个键对值添加到临时的"i"字典中，其中键是"blockId"，值是从dict1中移除的值。
        """
        if i.get("bookmarkId") in dict1:
            i["blockId"] = dict1.pop(i.get("bookmarkId"))
    # 到这一步，dict1中剩余的都是Notion API没有获取到的blockID，接下来的循环就是把这些dict1里剩余的都从Notion里删除
    """ 原始代码
    for blockId in dict1.values():
        notion_helper.delete_block(blockId)
        notion_helper.delete_block(dict2.get(blockId))
    """
    # 我修改的，加了条件判断：在dict1中已经删除的，dict2不会再次删除
    for blockId in dict1.values():
        notion_helper.delete_block(blockId)
        # 检查dict2中的blockId是否已经在dict1的删除操作中被处理
        correspondingBlockId = dict2.get(blockId)
        if correspondingBlockId and correspondingBlockId not in dict1.values():
            notion_helper.delete_block(correspondingBlockId)
    return bookmarks


def get_review_list(page_id,bookId):
    """获取笔记"""
    filter = {"property": "Books", "relation": {"contains": page_id}}
    results = notion_helper.query_all_by_book(notion_helper.review_database_id, filter)
    dict1 = {
        get_rich_text_from_result(x, "reviewId"): get_rich_text_from_result(
            x, "blockId"
        )
        for x in results
    }
    dict2 = {get_rich_text_from_result(x, "blockId"): x.get("id") for x in results}
    reviews = weread_api.get_review_list(bookId)
    for i in reviews:
        if i.get("reviewId") in dict1:
            i["blockId"] = dict1.pop(i.get("reviewId"))
    """ 原始代码 
    for blockId in dict1.values():
        notion_helper.delete_block(blockId)
        notion_helper.delete_block(dict2.get(blockId))
    """
    # 我修改的，加了条件判断：在dict1中已经删除的，dict2不会再次删除
    for blockId in dict1.values():
        notion_helper.delete_block(blockId)
        # 检查dict2中的blockId是否已经在dict1的删除操作中被处理
        correspondingBlockId = dict2.get(blockId)
        if correspondingBlockId and correspondingBlockId not in dict1.values():
            notion_helper.delete_block(correspondingBlockId)
    return reviews


def check(bookId):
    """检查是否已经插入过"""
    filter = {"property": "BookId", "rich_text": {"equals": bookId}}
    response = notion_helper.query(
        database_id=notion_helper.book_database_id, filter=filter
    )
    if len(response["results"]) > 0:
        return response["results"][0]["id"]
    return None


def get_sort():
    """获取database中的最新时间"""
    filter = {"property": "Sort", "number": {"is_not_empty": True}}
    sorts = [
        {
            "property": "Sort",
            "direction": "descending",
        }
    ]
    response = notion_helper.query(
        database_id=notion_helper.book_database_id,
        filter=filter,
        sorts=sorts,
        page_size=1,
    )
    if len(response.get("results")) == 1:
        return response.get("results")[0].get("properties").get("Sort").get("number")
    return 0


def download_image(url, save_dir="cover"):
    # 确保目录存在，如果不存在则创建
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # 获取文件名，使用 URL 最后一个 '/' 之后的字符串
    file_name = url.split("/")[-1] + ".jpg"
    save_path = os.path.join(save_dir, file_name)

    # 检查文件是否已经存在，如果存在则不进行下载
    if os.path.exists(save_path):
        print(f"File {file_name} already exists. Skipping download.")
        return save_path

    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(save_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=128):
                file.write(chunk)
        print(f"Image downloaded successfully to {save_path}")
    else:
        print(f"Failed to download image. Status code: {response.status_code}")
    return save_path


def sort_notes(page_id, chapter, bookmark_list):
    """对笔记进行排序"""
    bookmark_list = sorted(
        bookmark_list,
        key=lambda x: (
            x.get("chapterUid", 1),
            0
            if (x.get("range", "") == "" or x.get("range").split("-")[0] == "")
            else int(x.get("range").split("-")[0]),
        ),
    )

    notes = []
    if chapter != None:
        filter = {"property": "Books", "relation": {"contains": page_id}}
        results = notion_helper.query_all_by_book(
            notion_helper.chapter_database_id, filter
        )
        dict1 = {
            get_number_from_result(x, "chapterUid"): get_rich_text_from_result(
                x, "blockId"
            )
            for x in results
        }
        dict2 = {get_rich_text_from_result(x, "blockId"): x.get("id") for x in results}
        d = {}
        for data in bookmark_list:
            chapterUid = data.get("chapterUid", 1)
            if chapterUid not in d:
                d[chapterUid] = []
            d[chapterUid].append(data)
        for key, value in d.items():
            if key in chapter:
                if key in dict1:
                    chapter.get(key)["blockId"] = dict1.pop(key)
                notes.append(chapter.get(key))
            notes.extend(value)
        for blockId in dict1.values():
            notion_helper.delete_block(blockId)
            notion_helper.delete_block(dict2.get(blockId))
    else:
        notes.extend(bookmark_list)
    return notes


def append_blocks(id, contents):
    print(f"笔记数{len(contents)}")
    #插入目录？
    before_block_id = ""
    block_children = notion_helper.get_block_children(id)
    if len(block_children) > 0 and block_children[0].get("type") == "table_of_contents":
        before_block_id = block_children[0].get("id")
    else:
        response = notion_helper.append_blocks(
            block_id = id, children = [get_table_of_contents()]
        )
        before_block_id = response.get("results")[0].get("id")

    #插入callout block内容？
    blocks = []
    sub_contents = []
    l = []
    for content in contents:
        if len(blocks) == 100:
            results = append_blocks_to_notion(id, blocks, before_block_id, sub_contents)
            before_block_id = results[-1].get("blockId")
            l.extend(results)
            blocks.clear()
            sub_contents.clear()
            blocks.append(content_to_block(content))
            sub_contents.append(content)
        elif "blockId" in content:
            if len(blocks) > 0:
                l.extend(
                    append_blocks_to_notion(id, blocks, before_block_id, sub_contents)
                )
                blocks.clear()
                sub_contents.clear()
            before_block_id = content["blockId"]
        else:
            blocks.append(content_to_block(content))
            sub_contents.append(content)

    if len(blocks) > 0:
        l.extend(append_blocks_to_notion(id, blocks, before_block_id, sub_contents))

    for index, value in enumerate(l):
        print(f"正在插入第{index+1}条笔记，共{len(l)}条")
        if "bookmarkId" in value:
            notion_helper.insert_bookmark(id, value)
        elif "reviewId" in value:
            notion_helper.insert_review(id, value)
        else:
            notion_helper.insert_chapter(id, value)

# 把获取到的划线内容，转成callout block
def content_to_block(content):
    if "bookmarkId" in content:
        return get_callout(
            content.get("markText",""),
            content.get("style"),
            content.get("colorStyle"),
            content.get("reviewId"),
        )
    elif "reviewId" in content:
        return get_callout(
            content.get("content",""),
            content.get("style"),
            content.get("colorStyle"),
            content.get("reviewId"),
        )
    else:
        return get_heading(content.get("level"), content.get("title"))

# 把转换好的callout block，添加到notion
def append_blocks_to_notion(id, blocks, after, contents):
    response = notion_helper.append_blocks_after(
        block_id=id, children=blocks, after=after
    )
    results = response.get("results")
    l = []
    #检查是否有摘要（笔记？）
    for index, content in enumerate(contents):
        result = results[index]
        if content.get("abstract") != None and content.get("abstract") != "":
            notion_helper.append_blocks(
                block_id=result.get("id"), children=[get_quote(content.get("abstract"))]
            )
        content["blockId"] = result.get("id")
        l.append(content)
    return l


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    options = parser.parse_args()
    weread_cookie = os.getenv("WEREAD_COOKIE")
    branch = os.getenv("REF").split("/")[-1]
    repository =  os.getenv("REPOSITORY")
    weread_api = WeReadApi()
    notion_helper = NotionHelper()
    notion_books = notion_helper.get_all_book()
    books = weread_api.get_notebooklist()
    print(len(books))
    if books != None:
        for index, book in enumerate(books):
            bookId = book.get("bookId")
            title = book.get("book").get("title")
            sort = book.get("sort")
            if bookId not in notion_books:
                continue
            if sort == notion_books.get(bookId).get("Sort"):
                continue
            pageId = notion_books.get(bookId).get("pageId")
            print(f"正在同步《{title}》,一共{len(books)}本，当前是第{index+1}本。{pageId}")
            chapter = weread_api.get_chapter_info(bookId)
            bookmark_list = get_bookmark_list(pageId, bookId)
            reviews = get_review_list(pageId,bookId)
            bookmark_list.extend(reviews)
            content = sort_notes(pageId, chapter, bookmark_list)
            append_blocks(pageId, content)
            properties = {
                "Sort":get_number(sort)
            }
            notion_helper.update_book_page(page_id=pageId,properties=properties)
