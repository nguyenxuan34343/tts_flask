import requests
from bs4 import BeautifulSoup
import nest_asyncio
import asyncio
import os
import json
from urllib.parse import urlparse, parse_qs, urlunparse

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

def create_folder_id(folder_name):
    access_token = get_request('https://server.audiotruyencv.org/api/ggdrive/get-access-token')
    access_token = access_token["Token"]
    endpoint = 'https://www.googleapis.com/drive/v3/files'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    folder_metadata = {
        'name': f'{folder_name}',
        'mimeType': 'application/vnd.google-apps.folder'
    }
    response = requests.post(endpoint, headers=headers, json=folder_metadata)
    if response.status_code == 200:
        folder_data = response.json()
        folder_id = folder_data['id']
        return folder_id
    else:
        return None

def create_child_folder_id(folder_name, folder_id):
    access_token = get_request('https://server.audiotruyencv.org/api/ggdrive/get-access-token')
    access_token = access_token["Token"]
    endpoint = 'https://www.googleapis.com/drive/v3/files'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    folder_metadata = {
        'name': f'{folder_name}',
        'parents': [f'{folder_id}'],
        'mimeType': 'application/vnd.google-apps.folder'
    }
    response = requests.post(endpoint, headers=headers, json=folder_metadata)
    if response.status_code == 200:
        folder_data = response.json()
        folder_id = folder_data['id']
        return folder_id
    else:
        return None

def create_up_chapter_by_book_id(id):
    folder_id = ""
    text_folder_id = ""
    book = get_request(f'https://server.audiotruyencv.org/api/book/{id}')
    if book is not None:
        if book["Folderid"] is None:
            folder_id = create_folder_id(book["Booknm"])
            if folder_id is not None:
                text_folder_id = create_child_folder_id("text", folder_id)
                if text_folder_id is not None:
                    post_response = put_request('https://server.audiotruyencv.org/api/book/update-folder-id', json={"Id": book["Id"], "Folderid": folder_id, "Textfolderid": text_folder_id, "Audiofolderid": book["AudioFolderId"]})
                    if post_response is None:
                        print("Lỗi khi update Textfolderid lên Book : " + book["Booknm"])
                        return False
                else:
                    print("Lỗi khi tạo Textfolderid của Book : " + book["Booknm"])
                    return False
            else:
                print("không tạo được folder_id của Book : " + book["Booknm"])
                return False
        else:
              folder_id = book["Folderid"]
              text_folder_id = book["TextFolderId"]

        if folder_id is not None:
              chapters = get_request(f'https://server.audiotruyencv.org/api/chapter/{book["Id"]}/chapter-not-run')

              if chapters is not None:
                  for chapter in chapters:
                      chapter_data = get_request(f'https://server.audiotruyencv.org/api/chapter/{chapter["Id"]}')
                      if chapter_data is not None:
                          if chapter_data["Status"] == '1':
                              continue
                          if chapter_data["Status"] == '3':
                              continue

                          upload_file(chapter_data, text_folder_id)


def replace_source(text):
    return text.replace("truyenfull.vn", "audiotruyencv.org")

def upload_text_on_folder_id(file_name, folder_id, text):
    access_token = get_request('https://server.audiotruyencv.org/api/ggdrive/get-access-token')
    access_token = access_token["Token"]
    endpoint = 'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    metadata = {
        'name': f'{file_name}.txt',
        'parents': [f'{folder_id}']
    }

    file_path = './chapter_leech.txt'

    try:
        os.remove(file_path)
    except OSError:
        pass

    with open('chapter_leech.txt', 'w') as f:
        f.write(text)
    files = {
        'data': ('metadata', json.dumps(metadata), 'application/json; charset=UTF-8'),
        'file': open(file_path, "rb")
    }
    response = requests.post(endpoint, headers=headers, files=files)
    if response.status_code == 200:
        uploaded_file_data = response.json()
        file_id = uploaded_file_data['id']
        return file_id
    else:
        return None

def upload_file(chapter, text_folder_id):

    try:
        chapter_content = chapter["Content"]
        if chapter_content is not None:

            chapter_content = replace_source(chapter_content)

            status_upload_text_on_folder_id = upload_text_on_folder_id(chapter['Name'] + "-" + chapter["Id"], text_folder_id, chapter_content)
            #print(status_upload_text_on_folder_id)
            if status_upload_text_on_folder_id is not None:
                #print(status_upload_text_on_folder_id)
                post_response = put_request('https://server.audiotruyencv.org/api/chapter/update-info', json={"Id": chapter["Id"], "Status": "3", "Audiofileid": chapter["AudioFileid"], "Textfileid": status_upload_text_on_folder_id})
                #print(post_response)
                #return False
                if post_response is None:
                    return "lỗi khi cập nhật Textfileid ở Chapter"
                else:
                    print(chapter["Id"] + chapter['Name'] + ": Thành Công")
            else:
                return "lỗi khi tạo  Textfileid"
            return "success"
        else:
            return False
    except Exception as e:
        return str(e)

def get_book_details(book_link):
    response = requests.get(book_link)
    soup = BeautifulSoup(response.content, "html.parser")

    # Lấy thông tin tiêu đề, tác giả, thể loại và nội dung tóm tắt
    title_tag = soup.find('h1')
    book_title = title_tag.find('a').text

    detail_info_tags = soup.find_all(class_="detail-info")
    a_info_tags = detail_info_tags[0].find_all('a')
    author_name = a_info_tags[0].text.strip()
    genre = a_info_tags[1].text.strip()

    summary_tags = [element.text.strip()
                    for element in soup.find_all(class_="summary")]
    # Gộp tất cả các đoạn tóm tắt thành một chuỗi
    full_summary = ' '.join(summary_tags)

    div_tab_tag = soup.find(id="divtab")
    first_chapter_tag = div_tab_tag.find_all('a')[0]
    first_chapter_link = first_chapter_tag.get('href')

    return {
        'Booknm': book_title,
        'author_name': author_name,
        'genre': genre,
        'summary': full_summary,  # Trả về chuỗi đơn về nội dung tóm tắt
        'first_chapter_link': first_chapter_link
    }


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
                    print(chapter_link)
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


def create_authors(name, Authors):
    for author in Authors:
        if author["Name"] == name:
            return author["Id"]
    put_response = put_request(f'https://leech.audiotruyencv.org/api/authors', json={
                               "Id": "", "Name": name, "Created": "2023-11-01T02:18:08.419Z", "Biography": "", "Updated": "2023-11-01T02:18:08.419Z"})
    if put_response is None:
        return False
    return put_response["Id"]


def create_genres(name, Genres):
    for genre in Genres:
        if genre["Name"] == name:
            return [genre]
    return []


def process_chapters(Bookid, Seq, initial_link):
    next_chapter_link = get_next_chapter_link(initial_link)
    if next_chapter_link != None:
        list_chapter_ = get_chapter_details(
            Bookid, next_chapter_link, Seq + 1, 100)
        while len(list_chapter_) > 0:
            chapter_put_request = put_request(
                f'https://leech.audiotruyencv.org/api/leech/insert-chapter-by-bookid/{Bookid}', json=list_chapter_)

            list_chapter_ = []
            if chapter_put_request != False and chapter_put_request:
                next_chapter_link = get_next_chapter_link(
                    chapter_put_request["Url"])

                if next_chapter_link != None:
                    list_chapter_ = get_chapter_details(
                        Bookid, next_chapter_link, chapter_put_request["Seq"] + 1, 100)

        create_up_chapter_by_book_id(Bookid)

        print(Bookid + " : Hoàn thành")

def process_book(book_link):
    try:
        Genres = get_request(f'https://leech.audiotruyencv.org/api/genres')
        Authors = get_request(f'https://leech.audiotruyencv.org/api/authors')
        book_details = get_book_details(book_link)
        ListChapters = get_chapter_details("", book_details["first_chapter_link"], 1, 100)

        Book = {
            "Booknm": book_details["Booknm"],
            "AuthorsId": create_authors(book_details["author_name"], Authors),
            "Status": "0",
            "Description": book_details["summary"],
            "ListGenres": create_genres(book_details["genre"], Genres),
            "ListChapters": ListChapters
        }

        if check_book_exists(book_details["Booknm"].split('-')[0].strip()):
            return False
           
        book_post_request = post_request('https://leech.audiotruyencv.org/api/leech/insert-book', json=Book)

        if book_post_request and book_post_request != False:
            last_item = book_post_request[-1]
            process_chapters(last_item["Bookid"], last_item["Seq"], last_item["Url"])
    except:
      print("An exception occurred")

def get_link_books_in_page(page_link):
    list_books = []

    response = requests.get(page_link)
    soup = BeautifulSoup(response.content, "html.parser")
    content_tag = soup.find_all(class_="list-content")
    book_tag = content_tag[0].find_all('h3')

    chapter_tags = soup.find_all('span', class_="row-chapter")

    for book in book_tag:
        chapter_count = chapter_tags[book_tag.index(book)].text.split('.')[1]

        book_link_tag = book.find('a')
        book_nm = book_link_tag.text.split('-')[0].strip()
        if not check_book_exists(book_nm) and int(chapter_count) > 100:
            book_link = book_link_tag.get('href')
            list_books.append(book_link)

    return list_books

def check_book_exists(book_nm):
    book = get_request(f'https://leech.audiotruyencv.org/api/book/paginated-app?Keyword={book_nm}')
    rows = book['Rows']
    if len(rows) > 0:
        for b in rows:
            if b['Booknm'].split('-')[0].strip().lower() == book_nm.strip().lower():
                return True
    return False

def get_next_page(page_link):
    parsed_url = urlparse(page_link)
    query_parameters = parse_qs(parsed_url.query)

    next_page = query_parameters.get('trang', ['0'])
    next_page_value = int(next_page[0]) + 1
    query_parameters['trang'] = [str(next_page_value)]

    next_page_link = urlunparse(parsed_url._replace(query="&".join([f"{k}={v[0]}" for k, v in query_parameters.items()])))

    return next_page_link

def get_all_link_books(page_link, max_page=10):
    page_count = 1
    list_books = get_link_books_in_page(page_link)
    next_page_link = get_next_page(page_link)
    while next_page_link:
        list_books.extend(get_link_books_in_page(next_page_link))
        page_count += 1
        if page_count > max_page:
            break
        next_page_link = get_next_page(next_page_link)
    return list_books

def main():
    for x in range(181, 190):
        list_books =get_all_link_books(f"https://truyenconvert.net/the-loai/truyen-duoc-xem-nhieu-nhat?trang={x}", 1)
        for link in list_books:
            process_book(link)

# Chạy main() bất đồng bộ
main()