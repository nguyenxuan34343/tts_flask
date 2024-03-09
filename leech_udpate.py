import requests
from bs4 import BeautifulSoup
import asyncio
import nest_asyncio
import time

nest_asyncio.apply()

def get_request(url, params=None, jwt=None):
    headers = {}
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print('GET request failed:', e)
        return None


def post_request(url, data=None, json=None):
    headers = {}
    try:
        response = requests.post(url, data=data, json=json, headers=headers)
        response.raise_for_status()
        print(response.status_code)
        try:
            return response.json()
        except ValueError as e:
            print('Failed to get JSON:', e)
    except requests.exceptions.RequestException as e:
        print('POST request failed:', e)
        return None
def put_request(url, data=None, json=None):
    headers = {}
    try:
        response = requests.put(url, data=data, json=json, headers=headers)
        response.raise_for_status()
        print(response.status_code)
        try:
            return response.json()
        except ValueError as e:
            print('Failed to get JSON:', e)
    except requests.exceptions.RequestException as e:
        print('PUT request failed:', e)
        return None

def get_next_chapter_link(chapter_link):
    response = requests.get(chapter_link)
    soup = BeautifulSoup(response.content, "html.parser")
    next_chapter_tag = soup.find(id="nextchap")
    next_chapter_link = next_chapter_tag.get(
        'href') if next_chapter_tag else None

    return next_chapter_link

def get_chapter_details(Bookid, chapter_link, Seq, success_count_max):
    list_chapter = []
    success_count = 0
    while chapter_link and success_count < success_count_max:
        empty_content_count = 0
        while empty_content_count < 5:
            response = requests.get(chapter_link)
            soup = BeautifulSoup(response.content, "html.parser")

            title_tag = soup.find('h1')
            chapter_title = title_tag.find('a').text
            next_chapter_tag = soup.find(id="nextchap")
            next_chapter_link = next_chapter_tag.get(
                    'href') if next_chapter_tag else None
            # Tìm và loại bỏ các phần tử có id là 'setting-box' hoặc 'list-drop' và class 'comments' hoặc 'chapter-notification'
            elements_to_remove = soup.find_all(lambda tag: (tag.has_attr('id') and (tag['id'] == 'setting-box' or tag['id'] == 'list-drop')) or (tag.has_attr('class') and ('chapter-header' in tag['class'] or 'comments' in tag['class'] or 'chapter-notification' in tag['class'])))

            # Loại bỏ các phần tử tìm thấy
            for element in elements_to_remove:
                element.extract()  # hoặc element.decompose()
            content_tag = soup.find(id="reading")
            #print(content_tag)

            if content_tag:
                for tag in content_tag.find_all(['a', 'div']):
                    if tag.name == 'a' or tag.name == 'div':
                        # Check if it's a 'div' tag and its class doesn't contain certain values
                        if tag.name == 'div' and 'content' not in tag.get('class', []) and 'c-c' not in tag.get('class', []):
                            # Check if it's a 'div' with id 'content'
                            if 'content' in tag.get('id', []):
                                continue  # Skip this 'div' as it has id 'content'
                            tag.extract()
                        # Check if it's an 'a' tag and its class doesn't contain certain values
                        elif tag.name == 'a' and 'content' not in tag.get('class', []) and 'c-c' not in tag.get('class', []):
                            tag.extract()


            full_text = "\n\n\n".join(content_tag.stripped_strings)

            chapter_content = full_text

            if not chapter_content:
                empty_content_count += 1
                if empty_content_count == 5:

                    return list_chapter
            else:
                new_chapter = {
                    "Name": chapter_title,
                    "Content": chapter_content,
                    "Seq": Seq,
                    "Url": chapter_link,
                    "Status": "0",
                    "Bookid": Bookid
                }

                # Kiểm tra xem chapter đã tồn tại trong list_chapter hay chưa
                exists = any(item["Name"] == new_chapter["Name"] and item["Content"]
                             == new_chapter["Content"] for item in list_chapter)

                if not exists:
                    #print(Bookid + ":" + chapter_link)
                    list_chapter.append(new_chapter)
                    Seq += 1
                    success_count += 1

                    if success_count >= success_count_max:
                        return list_chapter

                #print(next_chapter_link)
                if not next_chapter_link:
                    return list_chapter

                chapter_link = next_chapter_link

    return list_chapter

def process_chapters(book):
    try:
        Bookid = book['Bookid']
        Seq = book['Seq']
        initial_link = book['Url']
        next_chapter_link = get_next_chapter_link(initial_link)
        if next_chapter_link != None:
            list_chapter_ = get_chapter_details(
                Bookid, next_chapter_link, Seq + 1, 100)
            while len(list_chapter_) > 0:
                chapter_put_request = put_request(
                    f'https://leech.audiotruyencv.org/api/leech/insert-chapter-by-bookid/{Bookid}', json=list_chapter_)
                list_chapter_ = []
                if chapter_put_request != False and chapter_put_request:
                    print(Bookid + ": OK")
                    next_chapter_link = get_next_chapter_link(
                        chapter_put_request["Url"])
                    print(chapter_put_request["Url"])
                    print(next_chapter_link)
                    if next_chapter_link != None:
                        list_chapter_ = get_chapter_details(
                            Bookid, next_chapter_link, chapter_put_request["Seq"] + 1, 100)
    except:
      print(book['Bookid'] + "An exception occurred")

async def async_process_chapter(book):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, process_chapters, book)

def get_chapter_last(Books):
    chapters = []
    for book in Books["Rows"]:
        chapter = get_request(f'https://leech.audiotruyencv.org/api/chapter/{book["Id"]}/last')
        #print(chapter)
        chapters.append(chapter)
    return chapters

async def main():
    tasks = []
    index = 0
    Books = get_request(f'https://leech.audiotruyencv.org/api/book/paginated-app?Status=0&Page={index}&RowsPerPage=50&Sortby=1&Direction=desc')
    chapters = get_chapter_last(Books)
    while len(chapters) > 0:
           tasks = [async_process_chapter(chapter) for chapter in chapters]
           await asyncio.gather(*tasks)
           index = index + 1
           chapters = []
           #print(index)
           Books = get_request(f'https://leech.audiotruyencv.org/api/book/paginated-app?Status=0&Page={index}&RowsPerPage=50&Sortby=1&Direction=desc')
           chapters = get_chapter_last(Books)

# Chạy main() bất đồng bộ
asyncio.run(main())
