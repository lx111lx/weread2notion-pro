
RICH_TEXT = "rich_text"
URL = "url"
RELATION = "relation"
NUMBER = "number"
DATE = "date"
FILES = "files"
STATUS = "status"
TITLE = "title"
SELECT = "select"

TAG_ICON_URL = "https://www.notion.so/icons/tag_gray.svg"
USER_ICON_URL = "https://www.notion.so/icons/user-circle-filled_gray.svg"
BOOK_ICON_URL = "https://www.notion.so/icons/book_gray.svg"
"""
TAG_ICON_URL = None
USER_ICON_URL = None
BOOK_ICON_URL = None
"""

book_properties_type_dict = {
    "BooksName":TITLE,
    "BookId":RICH_TEXT,
    "ISBN":RICH_TEXT,
    "Resource":URL,
    "Author":RELATION,
    "Sort":NUMBER,
    "Scores":NUMBER,
    "Cover":FILES,
    "Categories":RELATION,
    "Status":STATUS,
    "ReadTime":NUMBER,
    "Progress":NUMBER,
    "ReadDays":NUMBER,
    "Time":DATE,
    "Started Time":DATE,
    "Last Time":DATE,
    "Synopsis":RICH_TEXT,
    "BookShelf":SELECT,
    "Grade":SELECT,
    "Douban":URL,
}
