import calendar
from datetime import datetime
from datetime import timedelta
import hashlib
import os
import re
import requests
import base64
from config import (
    RICH_TEXT,
    URL,
    RELATION,
    NUMBER,
    DATE,
    FILES,
    STATUS,
    TITLE,
    SELECT,
)
import pendulum

NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_DATABASE_ID = os.getenv('NOTION_PAGE')

#灰色图标
NOTE_GRAY_ICON_URL = "https://www.notion.so/icons/thinking_lightgray.svg"
STRAIGHTLINE_GRAY_ICON_URL = "https://www.notion.so/icons/priority-mid_lightgray.svg"
WAVELINE_GRAY_ICON_URL = "https://www.notion.so/icons/aquarius_lightgray.svg"
FILLING_GRAY_ICON_URL = "https://www.notion.so/icons/die1_lightgray.svg"

#棕色图标（默认）
NOTE_BROWN_ICON_URL = "https://www.notion.so/icons/thinking_brown.svg"
STRAIGHTLINE_BROWN_ICON_URL = "https://www.notion.so/icons/priority-mid_brown.svg"
WAVELINE_BROWN_ICON_URL = "https://www.notion.so/icons/aquarius_brown.svg"
FILLING_BROWN_ICON_URL = "https://www.notion.so/icons/die1_brown.svg"

#红色图标
NOTE_RED_ICON_URL = "https://www.notion.so/icons/thinking_red.svg"
STRAIGHTLINE_RED_ICON_URL = "https://www.notion.so/icons/priority-mid_red.svg"
WAVELINE_RED_ICON_URL = "https://www.notion.so/icons/aquarius_red.svg"
FILLING_RED_ICON_URL = "https://www.notion.so/icons/die1_red.svg"

#紫色图标
NOTE_PURPLE_ICON_URL = "https://www.notion.so/icons/thinking_purple.svg"
STRAIGHTLINE_PURPLE_ICON_URL = "https://www.notion.so/icons/priority-mid_purple.svg"
WAVELINE_PURPLE_ICON_URL = "https://www.notion.so/icons/aquarius_purple.svg"
FILLING_PURPLE_ICON_URL = "https://www.notion.so/icons/die1_purple.svg"

#蓝色图标
NOTE_BLUE_ICON_URL = "https://www.notion.so/icons/thinking_blue.svg"
STRAIGHTLINE_BLUE_ICON_URL = "https://www.notion.so/icons/priority-mid_blue.svg"
WAVELINE_BLUE_ICON_URL = "https://www.notion.so/icons/aquarius_blue.svg"
FILLING_BLUE_ICON_URL = "https://www.notion.so/icons/die1_blue.svg"

#绿色图标
NOTE_GREEN_ICON_URL = "https://www.notion.so/icons/thinking_green.svg"
STRAIGHTLINE_GREEN_ICON_URL = "https://www.notion.so/icons/priority-mid_green.svg"
WAVELINE_GREEN_ICON_URL = "https://www.notion.so/icons/aquarius_green.svg"
FILLING_GREEN_ICON_URL = "https://www.notion.so/icons/die1_green.svg"

#黄色图标
NOTE_YELLOW_ICON_URL = "https://www.notion.so/icons/thinking_yellow.svg"
STRAIGHTLINE_YELLOW_ICON_URL = "https://www.notion.so/icons/priority-mid_yellow.svg"
WAVELINE_YELLOW_ICON_URL = "https://www.notion.so/icons/aquarius_yellow.svg"
FILLING_YELLOW_ICON_URL = "https://www.notion.so/icons/die1_yellow.svg"

MAX_LENGTH = (
    1024  # NOTION 2000个字符限制https://developers.notion.com/reference/request-limits
)


def get_heading(level, content):
    if level == 1:
        heading = "heading_1"
    elif level == 2:
        heading = "heading_2"
    else:
        heading = "heading_3"
    return {
        "type": heading,
        heading: {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": content[:MAX_LENGTH],
                    },
                }
            ],
            "color": "default",
            "is_toggleable": False,
        },
    }


def get_table_of_contents():
    """获取目录"""
    return {"type": "table_of_contents", "table_of_contents": {"color": "default"}}


def get_title(content):
    return {"title": [{"type": "text", "text": {"content": content[:MAX_LENGTH]}}]}


def get_rich_text(content):
    return {"rich_text": [{"type": "text", "text": {"content": content[:MAX_LENGTH]}}]}


def get_url(url):
    return {"url": url}


def get_file(url):
    return {"files": [{"type": "external", "name": "Cover", "external": {"url": url}}]}


def get_multi_select(names):
    return {"multi_select": [{"name": name} for name in names]}


def get_relation(ids):
    return {"relation": [{"id": id} for id in ids]}


def get_date(start, end=None):
    return {
        "date": {
            "start": start,
            "end": end,
            "time_zone": "Asia/Shanghai",
        }
    }


def get_icon(url):
    return {"type": "external", "external": {"url": url}}


def get_select(name):
    return {"select": {"name": name}}


def get_number(number):
    return {"number": number}


def get_quote(content):
    return {
        "type": "quote",
        "quote": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": content[:MAX_LENGTH]},
                }
            ],
            "color": "default",
        },
    }

#加入划线样式更新逻辑
def get_database_pages(database_id, notion_token):
    """查询数据库获取所有页面的ID"""
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
    }
    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        return [page["id"] for page in response.json()["results"]]
    else:
        print("Error fetching database pages")
        return []

def get_page_callouts(page_id, notion_token):
    """获取页面中所有Callout块的ID"""
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        # 筛选出类型为callout的块
        callouts = [block["id"] for block in response.json()["results"] if block["type"] == "callout"]
        return callouts
    else:
        print("Error fetching page callouts")
        return []

# 先在for循环外部定义get_callout函数，否则其他文件导入不了这个函数

def get_callout(content, style, colorStyle, reviewId):
callout_block = get_callout(callout_content, callout_style, callout_colorStyle, callout_reviewId)

# 遍历数据库中的所有页面，获取并更新Callout块，根据不同的划线样式设置不同的emoji 直线type=0 背景颜色是1 波浪线是2
page_ids = get_database_pages(NOTION_DATABASE_ID, NOTION_TOKEN)
for page_id in page_ids:
    callout_ids = get_page_callouts(page_id, NOTION_TOKEN)
    for callout_id in callout_ids:
        # 在这里实现更新Callout样式的逻辑
        # 初始设置默认图标为棕色背景对应的图标
        icon = get_icon(FILLING_BROWN_ICON_URL)  #默认样式为填充
        
        # 根据划线颜色设置文字的颜色和默认图标
        if callout_colorStyle == 1:
            color = "red_background"
            icon = get_icon(WAVELINE_RED_ICON_URL)
        elif callout_colorStyle == 2:
            color = "purple_background"
            icon = get_icon(WAVELINE_PURPLE_ICON_URL)
        elif callout_colorStyle == 3:
            color = "blue_background"
            icon = get_icon(WAVELINE_BLUE_ICON_URL)
        elif callout_colorStyle == 4:
            color = "green_background"
            icon = get_icon(WAVELINE_GREEN_ICON_URL)
        elif callout_colorStyle == 5:
            color = "yellow_background"
            icon = get_icon(WAVELINE_YELLOW_ICON_URL)
        else:
            color = "gray_background"  # 如果没有匹配的colorStyle，使用默认的灰色背景
        
        # 根据style调整图标
        if style == 0:
            if callout_colorStyle == 1:
                icon = get_icon(STRAIGHTLINE_RED_ICON_URL)
            elif callout_colorStyle == 2:
                icon = get_icon(STRAIGHTLINE_PURPLE_ICON_URL)
            elif callout_colorStyle == 3:
                icon = get_icon(STRAIGHTLINE_BLUE_ICON_URL)
            elif callout_colorStyle == 4:
                icon = get_icon(STRAIGHTLINE_GREEN_ICON_URL)
            elif callout_colorStyle == 5:
                icon = get_icon(STRAIGHTLINE_YELLOW_ICON_URL)
            else:
                # 默认棕色图标已经在最初设置，这里不需要再次设置
                pass
        elif callout_style == 1:
            if callout_colorStyle == 1:
                icon = get_icon(FILLING_RED_ICON_URL)
            elif callout_colorStyle == 2:
                icon = get_icon(FILLING_PURPLE_ICON_URL)
            elif callout_colorStyle == 3:
                icon = get_icon(FILLING_BLUE_ICON_URL)
            elif callout_colorStyle == 4:
                icon = get_icon(FILLING_GREEN_ICON_URL)
            elif callout_colorStyle == 5:
                icon = get_icon(FILLING_YELLOW_ICON_URL)
            else:
                icon = get_icon(FILLING_BROWN_ICON_URL)
        
        # 如果reviewId不是空说明是笔记，根据颜色调整图标
        if callout_reviewId is not None:
            if callout_colorStyle == 1:
                icon = get_icon(NOTE_RED_ICON_URL)
            elif callout_colorStyle == 2:
                icon = get_icon(NOTE_PURPLE_ICON_URL)
            elif callout_colorStyle == 3:
                icon = get_icon(NOTE_BLUE_ICON_URL)
            elif callout_colorStyle == 4:
                icon = get_icon(NOTE_GREEN_ICON_URL)
            elif callout_colorStyle == 5:
                icon = get_icon(NOTE_YELLOW_ICON_URL)
            else:
                icon = get_icon(NOTE_BROWN_ICON_URL)
        
        
            
        return {
            "type": "callout",
            "callout": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": content[:MAX_LENGTH],
                        },
                    }
                ],
                "icon": icon,
                "color": color,
            },
        }
        print(f"Found Callout block with ID {callout_id} in page {page_id}")


def get_rich_text_from_result(result, name):
    return result.get("properties").get(name).get("rich_text")[0].get("plain_text")


def get_number_from_result(result, name):
    return result.get("properties").get(name).get("number")


def format_time(time):
    """将秒格式化为 xx时xx分格式"""
    result = ""
    hour = time // 3600
    if hour > 0:
        result += f"{hour}h"
    minutes = time % 3600 // 60
    if minutes > 0:
        result += f"{minutes}min"
    return result


def format_date(date, format="%Y-%m-%d %H:%M:%S"):
    return date.strftime(format)


def timestamp_to_date(timestamp):
    """时间戳转化为date"""
    return datetime.utcfromtimestamp(timestamp) + timedelta(hours=8)


def get_first_and_last_day_of_month(date):
    # 获取给定日期所在月的第一天
    first_day = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # 获取给定日期所在月的最后一天
    _, last_day_of_month = calendar.monthrange(date.year, date.month)
    last_day = date.replace(
        day=last_day_of_month, hour=0, minute=0, second=0, microsecond=0
    )

    return first_day, last_day


def get_first_and_last_day_of_year(date):
    # 获取给定日期所在年的第一天
    first_day = date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    # 获取给定日期所在年的最后一天
    last_day = date.replace(month=12, day=31, hour=0, minute=0, second=0, microsecond=0)

    return first_day, last_day


def get_first_and_last_day_of_week(date):
    # 获取给定日期所在周的第一天（星期一）
    first_day_of_week = (date - timedelta(days=date.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # 获取给定日期所在周的最后一天（星期日）
    last_day_of_week = first_day_of_week + timedelta(days=6)

    return first_day_of_week, last_day_of_week


def get_properties(dict1, dict2):
    properties = {}
    for key, value in dict1.items():
        type = dict2.get(key)
        if value == None:
            continue
        property = None
        if type == TITLE:
            property = {
                "title": [
                    {"type": "text", "text": {"content": value[:MAX_LENGTH]}}
                ]
            }
        elif type == RICH_TEXT:
            property = {
                "rich_text": [
                    {"type": "text", "text": {"content": value[:MAX_LENGTH]}}
                ]
            }
        elif type == NUMBER:
            property = {"number": value}
        elif type == STATUS:
            property = {"status": {"name": value}}
        elif type == FILES:
            property = {"files": [{"type": "external", "name": "Cover", "external": {"url": value}}]}
        elif type == DATE:
            property = {
                "date": {
                    "start": pendulum.from_timestamp(
                        value, tz="Asia/Shanghai"
                    ).to_datetime_string(),
                    "time_zone": "Asia/Shanghai",
                }
            }
        elif type==URL:
            property = {"url": value}        
        elif type==SELECT:
            property = {"select": {"name": value}}
        elif type == RELATION:
            property = {"relation": [{"id": id} for id in value]}
        if property:
            properties[key] = property
    return properties


def get_property_value(property):
    """从Property中获取值"""
    type = property.get("type")
    content = property.get(type)
    if content is None:
        return None
    if type == "title" or type == "rich_text":
        if(len(content)>0):
            return content[0].get("plain_text")
        else:
            return None
    elif type == "status" or type == "select":
        return content.get("name")
    elif type == "files":
        # 不考虑多文件情况
        if len(content) > 0 and content[0].get("type") == "external":
            return content[0].get("external").get("url")
        else:
            return None
    elif type == "date":
        return str_to_timestamp(content.get("start"))
    else:
        return content


def calculate_book_str_id(book_id):
    md5 = hashlib.md5()
    md5.update(book_id.encode("utf-8"))
    digest = md5.hexdigest()
    result = digest[0:3]
    code, transformed_ids = transform_id(book_id)
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

def transform_id(book_id):
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

def get_weread_url(book_id):
    return f"https://weread.qq.com/web/reader/{calculate_book_str_id(book_id)}"

def str_to_timestamp(date):
    if date == None:
        return 0
    dt = pendulum.parse(date)
    # 获取时间戳
    return int(dt.timestamp())

upload_url = 'https://wereadassets.malinkang.com/'


def upload_image(folder_path, filename,file_path):
    # 将文件内容编码为Base64
    with open(file_path, 'rb') as file:
        content_base64 = base64.b64encode(file.read()).decode('utf-8')

    # 构建请求的JSON数据
    data = {
        'file': content_base64,
        'filename': filename,
        'folder': folder_path
    }

    response = requests.post(upload_url, json=data)

    if response.status_code == 200:
        print('File uploaded successfully.')
        return response.text
    else:
        return None

def url_to_md5(url):
    # 创建一个md5哈希对象
    md5_hash = hashlib.md5()

    # 对URL进行编码，准备进行哈希处理
    # 默认使用utf-8编码
    encoded_url = url.encode('utf-8')

    # 更新哈希对象的状态
    md5_hash.update(encoded_url)

    # 获取十六进制的哈希表示
    hex_digest = md5_hash.hexdigest()

    return hex_digest

def download_image(url, save_dir="cover"):
    # 确保目录存在，如果不存在则创建
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    file_name = url_to_md5(url) + ".jpg"
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

def upload_cover(url):
    cover_file = download_image(url)
    return upload_image("cover",f"{cover_file.split('/')[-1]}",cover_file)
