import requests
from bs4 import BeautifulSoup


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

            content_tag = soup.find(id="content")

            if content_tag:
                for tag in content_tag.find_all(['a', 'div']):
                    if tag.name == 'a' or tag.name == 'div':
                        if 'c-c' not in tag.get('class', []):
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

                next_chapter_tag = soup.find(id="nextchap")
                next_chapter_link = next_chapter_tag.get(
                    'href') if next_chapter_tag else None

                if not next_chapter_link:
                    return list_chapter

                chapter_link = next_chapter_link

    return list_chapter


def create_authors(name):
    for author in Authors:
        if author["Name"] == name:
            return author["Id"]
    put_response = put_request(f'https://leech.audiotruyencv.org/api/authors', json={
                               "Id": "", "Name": name, "Created": "2023-11-01T02:18:08.419Z", "Biography": "", "Updated": "2023-11-01T02:18:08.419Z"})
    if put_response is None:
        return False
    return put_response["Id"]


def create_genres(name):
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


Genres = get_request(f'https://leech.audiotruyencv.org/api/genres')
Authors = get_request(f'https://leech.audiotruyencv.org/api/authors')
# Gọi hàm và truyền đường dẫn sách cần kiểm tra
book_link = "https://truyenconvert.net/truyen/nguyen-lai-ta-la-tu-tien-dai-lao-104856"
book_details = get_book_details(book_link)
ListChapters = get_chapter_details(
    "", book_details["first_chapter_link"], 1, 100)
Book = {"Booknm": book_details["Booknm"], "AuthorsId": create_authors(
    book_details["author_name"]), "Status": "0", "Description":  book_details["summary"], "ListGenres": create_genres(book_details["genre"]), "ListChapters": ListChapters}
book_post_request = post_request(
    f'https://leech.audiotruyencv.org/api/leech/insert-book', json=Book)

if book_post_request != False and book_post_request:
    process_chapters(book_post_request[-1]["Bookid"],
                     book_post_request[-1]["Seq"], book_post_request[-1]["Url"])
