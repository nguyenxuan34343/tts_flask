import requests
from bs4 import BeautifulSoup
import asyncio
import nest_asyncio
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
    li_status_tag = detail_info_tags[0].find_all('li')
    status_name =  li_status_tag[2].find('span').text
    if status_name == 'Full':
        status = '1'
    else:
        status = '0'

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
        'first_chapter_link': first_chapter_link,
        'status': status
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
                    #print(chapter_link)
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

def process_book(book_link):
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
    book_post_request = post_request('https://leech.audiotruyencv.org/api/leech/insert-book', json=Book)
    
    if book_post_request and book_post_request != False:
        last_item = book_post_request[-1]
        process_chapters(last_item["Bookid"], last_item["Seq"], last_item["Url"])

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
        if not check_book_exists(book_nm) and int(chapter_count) > 0:
            book_link = book_link_tag.get('href')
            list_books.append(book_link)
    
    return list_books

def check_book_exists(book_nm):
    book = get_request(f'https://leech.audiotruyencv.org/api/book/paginated-app?Keyword={book_nm}')
    rows = book['Rows']
    if len(rows) > 0:
        for b in rows:
            if b['Booknm'].strip().lower() == book_nm.lower():
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

async def async_process_book(book_link):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, process_book, book_link)

async def main():

    book_links =['https://truyenconvert.net/truyen/than-hao-tu-thi-d-i-h-c-sau-bat-dau-28911',
                'https://truyenconvert.net/truyen/60-trong-sinh-cam-nham-kich-ban-nu-phu-muon-lam-giau-38482',
                'https://truyenconvert.net/truyen/do-thi-co-tien-y-33711',
                'https://truyenconvert.net/truyen/ta-moi-ngay-tuy-co-mot-cai-moi-he-thong-28057',
                'https://truyenconvert.net/truyen/nhan-dao-dai-thanh-31494',
                'https://truyenconvert.net/truyen/bat-dau-tro-thanh-phong-chu-danh-dau-thanh-canh-tu-vi-35864',
                'https://truyenconvert.net/truyen/ngoai-that-khong-de-lam-37455',
                'https://truyenconvert.net/truyen/ren-sat-lien-co-the-truong-sinh-bat-tu-36103',
                'https://truyenconvert.net/truyen/bao-ho-ben-ta-toc-truong-29534',
                'https://truyenconvert.net/truyen/cuu-vuc-kiem-de-10740',
                'https://truyenconvert.net/truyen/van-tuong-chi-vuong-30362',
                'https://truyenconvert.net/truyen/ta-tai-pham-nhan-khoa-hoc-tu-tien-29748',
                'https://truyenconvert.net/truyen/thu-do-de-lien-tro-nen-manh-me-che-tao-van-co-de-nhat-than-tong-37152',
                'https://truyenconvert.net/truyen/tu-tien-bac-si-106196',
                'https://truyenconvert.net/truyen/xuyen-khong-song-mot-cuoc-doi-khac-du-ky-full',
                'https://truyenconvert.net/truyen/vo-mong-tien-do-1549',
                'https://truyenconvert.net/truyen/giao-chu-ve-huu-thuong-ngay-29542',
                'https://truyenconvert.net/truyen/vong-du-1-level-ta-day-chung-ket-than-minh-29955',
                'https://truyenconvert.net/truyen/tien-de-trong-sinh-hon-do-thi-28407',
                'https://truyenconvert.net/truyen/doan-sat-thu-tien-hoa-than-cap-lam-lang-full',
                'https://truyenconvert.net/truyen/hai-duong-cau-sinh-vo-han-thang-cap-tien-hoa-36873',
                'https://truyenconvert.net/truyen/khai-cuoc-kim-phong-te-vu-lau-ch-mot-dao-kinh-thien-ha-33411',
                'https://truyenconvert.net/truyen/thon-phe-co-de-32427',
                'https://truyenconvert.net/truyen/vu-than-thien-ha-101271',
                'https://truyenconvert.net/truyen/viet-nam-ly-tran-tinh-han-22497',
                'https://truyenconvert.net/truyen/nien-dai-van-nam-phu-cuc-pham-vo-truoc-trong-sinh-35024',
                'https://truyenconvert.net/truyen/luan-hoi-nhac-vien-29658',
                'https://truyenconvert.net/truyen/tu-tien-tu-to-tien-hien-linh-bat-dau-34415',
                'https://truyenconvert.net/truyen/bi-doat-tat-thay-sau-nang-phong-than-tro-ve-32908',
                'https://truyenconvert.net/truyen/ly-tri-nguoi-cho-kinh-so-31907',
                'https://truyenconvert.net/truyen/thien-dao-bang-cau-thanh-kiem-than-dich-nga-bi-boc-quang-34934',
                'https://truyenconvert.net/truyen/kiem-dao-de-nhat-tien-27843',
                'https://truyenconvert.net/truyen/toan-dan-linh-chu-bat-dau-che-tao-bat-hu-tien-vuc-31403',
                'https://truyenconvert.net/truyen/than-thoai-ky-nguyen-ta-tien-hoa-thanh-hang-tinh-cap-cu-thu-37624',
                'https://truyenconvert.net/truyen/cu-long-thuc-tinh-luc-hi-truyen-full',
                'https://truyenconvert.net/truyen/con-duong-ba-chu-akay-hau-truyen-full-dai-cuc-hay-59e24ef7-5fbb-47d0-8147-a8e1f8192cfd',
                'https://truyenconvert.net/truyen/luan-hoi-dan-de-28665',
                'https://truyenconvert.net/truyen/luc-dia-kien-tien-28542',
                'https://truyenconvert.net/truyen/kiem-trung-tien-100569',
                'https://truyenconvert.net/truyen/dau-la-dai-luc-iv-chung-cuc-dau-la-101403',
                'https://truyenconvert.net/truyen/kiem-dao-cuong-than-32922',
                'https://truyenconvert.net/truyen/vo-dao-than-ma-ly-tan-full',
                'https://truyenconvert.net/truyen/ta-chinh-la-than-31031',
                'https://truyenconvert.net/truyen/cuong-vo-than-de-100350',
                'https://truyenconvert.net/truyen/do-thi-cuc-pham-y-than-24736',
                'https://truyenconvert.net/truyen/ta-tru-than-tong-mon-tren-duoi-bi-them-khoc-roi-35162',
                'https://truyenconvert.net/truyen/van-co-de-te-29867',
                'https://truyenconvert.net/truyen/bao-thu-cua-re-phe-vat-lam-hien-full',
                'https://truyenconvert.net/truyen/du-hi-giang-lam-di-the-gioi-19896',
                'https://truyenconvert.net/truyen/hon-trom-35872',
                'https://truyenconvert.net/truyen/toan-dan-thuc-tinh-bat-dau-than-thoai-cap-thien-phu-37151',
                'https://truyenconvert.net/truyen/metaverse-xuyen-viet-hau-tu-ky-to-he-thong-36334',
                'https://truyenconvert.net/truyen/dinh-phong-vo-thuat-duong-khai-full',
                'https://truyenconvert.net/truyen/mang-theo-khong-kho-hang-hoi-80-37040',
                'https://truyenconvert.net/truyen/tham-hai-du-tan-33910',
                'https://truyenconvert.net/truyen/quyen-khuynh-vay-ha-37082',
                'https://truyenconvert.net/truyen/toan-tay-du-deu-luong-cuong-do-de-cua-ta-deu-thanh-thanh-31800',
                'https://truyenconvert.net/truyen/hon-don-thien-de-quyet-17290',
                'https://truyenconvert.net/truyen/nhat-dao-9999-24024',
                'https://truyenconvert.net/truyen/ta-moi-tuan-tuy-co-mot-cai-moi-chuc-nghiep-28958',
                'https://truyenconvert.net/truyen/cuc-pham-o-re-full-lam-vu-giang-nhan-truyen-hay-moi',
                'https://truyenconvert.net/truyen/ta-co-9-trieu-ty-liem-cau-tien-32251',
                'https://truyenconvert.net/truyen/thien-kieu-tu-hon-ta-rut-ra-tien-to-tu-hanh-37488',
                'https://truyenconvert.net/truyen/tinh-tai-mat-the-599',
                'https://truyenconvert.net/truyen/truyen-12-nu-than-slaydark',
                'https://truyenconvert.net/truyen/lanh-chua-cau-sinh-tu-tan-ta-tieu-vien-bat-dau-cong-luoc-30752',
                'https://truyenconvert.net/truyen/hom-nay-ta-co-the-thua-ke-phu-quan-di-san-sao-35592',
                'https://truyenconvert.net/truyen/70-tieu-kieu-the-me-ke-37356',
                'https://truyenconvert.net/truyen/tao-hoa-chi-vuong-101111',
                'https://truyenconvert.net/truyen/ban-si-18951',
                'https://truyenconvert.net/truyen/huyen-huyen-ta-thien-menh-dai-nhan-vat-phan-phai-28132',
                'https://truyenconvert.net/truyen/sieu-cap-bao-an-tai-do-thi-7221',
                'https://truyenconvert.net/truyen/nhat-kiem-tuyet-the-31844',
                'https://truyenconvert.net/truyen/co-vo-diu-dang-cua-tong-tai-ba-dao-duong-uyen-dinh-truyen-full',
                'https://truyenconvert.net/truyen/theo-dai-thu-bat-dau-tien-hoa-25385',
                'https://truyenconvert.net/truyen/tro-lai-1982-lang-chai-nho-37999',
                'https://truyenconvert.net/truyen/pha-quan-menh-chang-re-bat-pham-diep-pham-tac-gia-tu-pham',
                'https://truyenconvert.net/truyen/tuyet-the-than-hoang-107356',
                'https://truyenconvert.net/truyen/ca-nha-nhan-vat-phan-dien-dien-phe-chi-co-su-muoi-dau-bi-37374',
                'https://truyenconvert.net/truyen/toan-dan-chuyen-chuc-ngu-long-su-ta-co-the-tram-than-38367',
                'https://truyenconvert.net/truyen/mink-duong-pho-so-13-31766',
                'https://truyenconvert.net/truyen/hac-lien-hoa-cong-luoc-so-tay-37036',
                'https://truyenconvert.net/truyen/toan-bo-vi-dien-deu-quy-cau-nhan-vat-phan-dien-nu-chinh-lam-nguoi-30429',
                'https://truyenconvert.net/truyen/than-kiem-vo-dich-35584',
                'https://truyenconvert.net/truyen/thuc-su-ta-khong-muon-vo-dich-25953',
                'https://truyenconvert.net/truyen/do-thi-tu-chan-y-thanh-7545',
                'https://truyenconvert.net/truyen/chien-ham-cua-ta-co-the-thang-cap-29431',
                'https://truyenconvert.net/truyen/phu-nhan-nang-ao-choang-lai-nao-dong-toan-thanh-31623',
                'https://truyenconvert.net/truyen/tu-ly-hon-bat-dau-vui-choi-giai-tri-30483',
                'https://truyenconvert.net/truyen/toi-cuong-than-thoai-de-hoang-nham-nga-tieu-full',
                'https://truyenconvert.net/truyen/trung-sinh-nien-dai-phao-hoi-truong-ty-mang-muoi-phan-cong-32925',
                'https://truyenconvert.net/truyen/truyen-an-hon-ngot-sung-vo-yeu-cua-tai-phiet-co-vy-vy-full',
                'https://truyenconvert.net/truyen/toan-cau-sat-luc-bat-dau-giac-tinh-sss-cap-thien-phu-33658',
                'https://truyenconvert.net/truyen/thi-than-chien-de-100006',
                'https://truyenconvert.net/truyen/hong-mong-thien-de-25733',
                'https://truyenconvert.net/truyen/quoc-vuong-34654',
                'https://truyenconvert.net/truyen/tu-phan-tich-thai-duong-bat-dau-35704',
                'https://truyenconvert.net/truyen/bay-tuoi-ta-xin-phep-nghi-ve-thon-chu-tri-hon-tang-su-tinh-37157',
                'https://truyenconvert.net/truyen/bat-diet-chien-than-7388',
                'https://truyenconvert.net/truyen/van-co-toi-cuong-tong-23003',
                'https://truyenconvert.net/truyen/dai-duong-de-nhat-nghich-tu-30404',
                'https://truyenconvert.net/truyen/kiem-dao-thong-than-191',
                'https://truyenconvert.net/truyen/tot-nhat-con-re-25014',
                'https://truyenconvert.net/truyen/vong-du-ta-co-the-tien-hoa-het-thay-25847',
                'https://truyenconvert.net/truyen/vo-thuong-sat-than-100358',
                'https://truyenconvert.net/truyen/nghich-thien-tieu-y-tien-34955',
                'https://truyenconvert.net/truyen/toan-dan-cau-sinh-mo-dau-gap-tram-lan-toc-do-tu-luyen-35538',
                'https://truyenconvert.net/truyen/than-quy-the-gioi-ta-dua-vao-treo-may-cau-truong-sinh-36348',
                'https://truyenconvert.net/truyen/thai-hoang-thon-thien-quyet-32503',
                'https://truyenconvert.net/truyen/khai-truong-nguoi-tai-trong-cua-hang-lao-ban-co-uc-diem-cuong-31302',
                'https://truyenconvert.net/truyen/bat-da-truy-ngoc-35702',
                'https://truyenconvert.net/truyen/chien-than-tu-la-giang-nghia-truyen-full',
                'https://truyenconvert.net/truyen/di-gioi-he-thong-cua-hang-33201',
                'https://truyenconvert.net/truyen/cong-phap-bi-pha-mat-ta-cang-manh-hon-35366',
                'https://truyenconvert.net/truyen/ta-thuc-su-la-phan-phai-a-25835',
                'https://truyenconvert.net/truyen/van-co-thien-de-6450',
                'https://truyenconvert.net/truyen/cuong-phi-sung-vuong-thanh-hy-mac-uyen-truyen-full',
                'https://truyenconvert.net/truyen/thien-dao-do-thu-quan-14540',
                'https://truyenconvert.net/truyen/vut-bo-chang-re-ngoc-so-tran-truyen-full',
                'https://truyenconvert.net/truyen/hoa-hong-do-37268',
                'https://truyenconvert.net/truyen/hoa-ly-sau-ta-bi-thai-tu-kieu-duong-33742',
                'https://truyenconvert.net/truyen/vua-tot-nghiep-co-cai-than-hao-he-thong-binh-thuong-a-36887',
                'https://truyenconvert.net/truyen/tien-vo-de-ton-106532',
                'https://truyenconvert.net/truyen/than-hao-moi-ngay-danh-dau-1-uc-37061',
                'https://truyenconvert.net/truyen/huan-luyen-quan-su-ngay-thu-nhat-cao-lanh-giao-hoa-dua-nuoc-cho-ta-33731',
                'https://truyenconvert.net/truyen/trong-sinh-80-mang-theo-ca-nha-qua-ngay-lanh-37920',
                'https://truyenconvert.net/truyen/ta-phat-song-truc-tiep-thong-thanh-trieu-37429',
                'https://truyenconvert.net/truyen/ma-mon-bai-hoai-3293',
    # Limit the number of concurrent tasks to 10
    concurrency = 10
    semaphore = asyncio.Semaphore(concurrency)

    async def limited_task(link):
        async with semaphore:
            await async_process_book(link)

    # Create tasks in batches of 10
    for i in range(0, len(book_links), concurrency):
        batch = book_links[i:i + concurrency]
        tasks = [limited_task(link) for link in batch]
        await asyncio.gather(*tasks)

# Chạy main() bất đồng bộ
asyncio.run(main())
