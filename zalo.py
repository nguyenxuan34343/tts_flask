from flask import Flask, request
from flask import send_file
from underthesea import sent_tokenize
from underthesea import text_normalize
from pydub import AudioSegment
import os
import re
import subprocess
import time
import requests
import traceback
import json
from urllib.parse import quote
# import required modules
from time import sleep
import random
import subprocess
import nltk
nltk.download('punkt')

app = Flask(__name__)

app.config['idserver'] = ''
app.config['jwt'] = ''
app.config['refreshToken'] = ''

#-----------------------------------------

def split_text(payload):
    text = []
    MAX_LENGTH = 200

    payload = text_normalize(payload)

    if len(payload) <= MAX_LENGTH:
        return [payload]

    sentences = nltk.sent_tokenize(payload)
    sub_para = sentences[0]

    for sen in sentences[1:]:
        if len(sub_para) > 499:
            splits = sub_para.split(",")

            for split in splits:
                text.append(split)

            sub_para = sen
        elif len(sub_para) + len(sen) + 1 <= MAX_LENGTH:
            sub_para += " " + sen
        else:
            text.append(sub_para)
            sub_para = sen

    text.append(sub_para)

    return text

def contains_valid_characters(text):
    return any(char not in (',', '.', ' ', '!') for char in text)

def filter_elements_with_valid_characters(input_list):
    return [item for item in input_list if contains_valid_characters(item.strip())]

def progress_data(data):
    MAX_LENGTH = 499
    sentences = []
    current_sentence = data[0]

    for word in data[1:]:
        if len(current_sentence) + len(word) <= MAX_LENGTH:
            current_sentence += word
        else:
            sentences.append(current_sentence)
            current_sentence = word

    sentences.append(current_sentence)
    return sentences

def remove_meaningless_characters(text):
    meaningless_chars = ['-', '_', '(', ')', '[', ']', '{', '}', '<', '>', '*', '/', '\\',
                         '|', '@', '#', '$', '%', '^', '&', '=', '+', '~', '`', '"', "'", '\n', '\r', '\t']

    for char in meaningless_chars:
        text = text.replace(char, '')

    return text

def data_processor(text):
    lst = split_text(text)
    lst = list(map(remove_meaningless_characters, lst))
    lst = filter_elements_with_valid_characters(lst)
    sentence = progress_data(lst)

    return sentence

#-----------------------------------------------------------------------------------------

def zalo_api(data):
    # get proxies
    source = "https://zalo.ai/"
    url = "https://zalo.ai/api/demo/v1/tts/synthesize"

    f = open("output.txt", "w")
    cookie = ''
    for p in data:
        session = requests.Session()
        text = quote(str(p))
        response = session.get(source)
        cookie = response.cookies.get_dict()
        payload = "input=" + text + "&speaker_id=1&speed=0.9&dict_id=0&quality=1"
        for k, v in cookie.items():
            cookie = k + '=' + v

        headers = {
            "User-Agent" : "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
            "content-type": "application/x-www-form-urlencoded; charset=utf-8",
            "origin": "https://zalo.ai",
            "referer": "https://zalo.ai/experiments/text-to-audio-converter",
            "cookie": cookie,
        }

        response = requests.request("POST", url, data=payload.encode(
            'utf-8'), headers=headers)

        print(response.text)
        f.write(response.text + "\n")

        time.sleep(1)
    f.close()


def get_links():
    out = open('output.txt', 'r').read()
    links = re.findall(
        r'(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}.m3u8)', out)
    return links

def delete_files_with_extensions(path):
    for file_name in os.listdir(path):
        if file_name.endswith((".wav", ".mp3", ".txt")):
            file_path = os.path.join(path, file_name)
            os.remove(file_path)

def connect_audio(links):
    try:
        id = 0
        path = str(os.getcwd())
        full = path + '/tmp_audio/'

        delete_files_with_extensions(full)

        for i in links:
            url = i
            des_fol = str(os.getcwd()) + "/tmp_audio/"
            namefile = str(id) + ".mp3"
            command = ['ffmpeg', '-i', url, '-ab', '64k', des_fol + namefile, '-y']
            id = id + 1
            subprocess.run(command)
            time.sleep(1)
        print("Done processing audio files.")
    except Exception as e:
        error_message = f"Error processing audio: {str(e)}"
        raise Exception(error_message)

def mer_audio(id, links):
    try:
        path_final_audio = os.path.join(os.getcwd(), "final_audio")
        path_tmp_audio = os.path.join(os.getcwd(), "tmp_audio")

        # Xóa toàn bộ tệp trong thư mục đích trước khi bắt đầu
        delete_files_with_extensions(path_final_audio)

        mp3_path = os.path.join(path_final_audio, f'{id}.mp3')
        combined_sounds = AudioSegment.from_mp3(os.path.join(path_tmp_audio, f'0.mp3'))
        for i in range(len(links)):
            if i > 0 :
                sound = AudioSegment.from_mp3(os.path.join(path_tmp_audio, f'{i}.mp3'))
                combined_sounds += sound

        combined_sounds.export(mp3_path, format="mp3")

        mp3_path = mp3_path.replace(os.getcwd(), '.')
        return mp3_path
    except Exception as e:
        error_message = f"Error merging audio: {str(e)}"
        raise Exception(error_message)


def delete_all_file():
    for file_name in os.listdir("./"):
        if file_name.endswith((".wav", ".mp3", ".txt")):
            file_path = os.path.join("./", file_name)
            os.remove(file_path)
    for file_name in os.listdir("./tmp_audio"):
        if file_name.endswith((".wav", ".mp3", ".txt")):
            file_path = os.path.join("./tmp_audio/", file_name)
            os.remove(file_path)
    for file_name in os.listdir("./final_audio"):
        if file_name.endswith((".wav", ".mp3", ".txt")):
            file_path = os.path.join("./final_audio/", file_name)
            os.remove(file_path)

def add_guide(text, id):
    try:
        os.system("windscribe connect")
        time.sleep(10)
        path = str(os.getcwd()) + "/tmp_audio/"
        if os.path.exists(path) == False:
            os.system("mkdir tmp_audio")

        path = str(os.getcwd()) + "/final_audio/"
        if os.path.exists(path) == False:
            os.system("mkdir final_audio")

        lst = data_processor(text)
        zalo_api(lst)
        links = get_links()
        connect_audio(links)
        path = mer_audio(id, links)
        time.sleep(10)
    except Exception as e:
        os.system("windscribe disconnect")
        return str(e)
    finally:
        os.system("windscribe disconnect")

    return "success"

def get_request(url, params=None, jwt=None):
    headers = {}
    if app.config['jwt']:
        headers['Authorization'] = f'Bearer {app.config["jwt"]}'
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print('GET request failed:', e)
        return None

def post_request(url, data=None, json=None):
    headers = {}
    if app.config['jwt']:
        headers['Authorization'] = f'Bearer {app.config["jwt"] }'
        headers['refreshToken'] = app.config["refreshToken"]
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
    if app.config['jwt']:
        headers['Authorization'] = f'Bearer {app.config["jwt"] }'
    
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

def upload_audio_on_folder_id(file_name, folder_id):
    access_token = get_request('https://server.audiotruyencv.org/api/ggdrive/get-access-token')
    access_token = access_token["Token"]
    endpoint = 'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    metadata = {
        'name': f'{file_name}.mp3',
        'parents': [f'{folder_id}']
    }

    file_path = os.path.join(os.getcwd(), f'final_audio/{file_name}.mp3')

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

    file_path = './chapter.txt'

    try:
        os.remove(file_path)
    except OSError:
        pass

    with open('chapter.txt', 'w') as f:
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

def get_all_folder():
    access_token = get_request('https://server.audiotruyencv.org/api/ggdrive/get-access-token')
    access_token = access_token["Token"]
    endpoint = 'https://www.googleapis.com/drive/v3/files'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(endpoint, headers=headers)
    if response.status_code == 200:
        files_data = response.json()
        files = files_data.get('files', [])
        if files:
            print('Files in Drive:')
            for file in files:
                print(file['name'])
        else:
            print('No files found in Drive.')
    else:
        print('Failed to list files.')

def get_all_file_folder_id(folder_id):
    access_token = get_request('https://server.audiotruyencv.org/api/ggdrive/get-access-token')
    access_token = access_token["Token"]
    endpoint = 'https://www.googleapis.com/drive/v3/files'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    params = {
        'q': f"'{folder_id}' in parents",
        'fields': 'files(id, name)'
    }
    response = requests.get(endpoint, headers=headers, params=params)
    if response.status_code == 200:
        files_data = response.json()
        files = files_data.get('files', [])
        if files:
            print('Files in the folder:')
            for file in files:
                print(f"File ID: {file['id']}, File Name: {file['name']}")
        else:
            print('No files found in the folder.')
    else:
        print('Failed to retrieve files.')

def create_file_audio(chapter, audio_folder_id, text_folder_id):
    print("start chapter")
    try:
        chapter_content = chapter["Content"]
        if chapter_content is not None:

            chapter_content = replace_source(chapter_content)

            status_add_guide = add_guide(chapter_content, chapter["Id"])

            if status_add_guide == "success":
                if chapter["TextFileid"] is not None:
                    status_upload_text_on_folder_id = chapter["TextFileid"]
                else : 
                    status_upload_text_on_folder_id = upload_text_on_folder_id(chapter['Name'] + "-" + chapter["Id"], text_folder_id, chapter_content)
                status_upload_audio_on_folder_id = upload_audio_on_folder_id(chapter["Id"], audio_folder_id)
            else:
                return status_add_guide
            if status_upload_audio_on_folder_id is not None and status_upload_text_on_folder_id is not None:
                post_response = put_request('https://server.audiotruyencv.org/api/chapter/update-info', json={"Id": chapter["Id"], "Status": "1", "AudioFileid": status_upload_audio_on_folder_id, "TextFileid": status_upload_text_on_folder_id})
                print("end chapter")
                if post_response is None:
                    return "lỗi khi cập nhật AudioFileid và TextFileid ở Chapter"
            else:
                return "lỗi khi tạo AudioFileid và TextFileid"

            time.sleep(5)

            return "success"
        else:
            #post_response = put_request('https://server.audiotruyencv.org/api/chapter/update-info', json={"Id": chapter["Id"], "Status": "2"})
            return "lỗi lấy nội dung chương None"
    except Exception as e:
        #post_response = put_request('https://server.audiotruyencv.org/api/chapter/update-info', json={"Id": chapter["Id"], "Status": "2"})
        return str(e)

def replace_source(text):
    return text.replace("truyenfull.vn", "audiotruyencv.org")

def create_audio_all_chapter_by_book_id(id):
    folder_id = ""
    audio_folder_id = ""
    text_folder_id = ""
    book = get_request(f'https://server.audiotruyencv.org/api/book/{id}')
    if book is not None:
        if book["Folderid"] is None:
            folder_id = create_folder_id(book["Booknm"])
            if folder_id is not None:
                audio_folder_id = create_child_folder_id("audio", folder_id)
                text_folder_id = create_child_folder_id("text", folder_id)
                if audio_folder_id is not None and text_folder_id is not None:
                    post_response = put_request('https://server.audiotruyencv.org/api/book/update-folder-id', json={"Id": book["Id"], "Folderid": folder_id, "Textfolderid": text_folder_id, "Audiofolderid": audio_folder_id})
                    if post_response is None:
                        log_server("Lỗi khi update Textfolderid và Audiofolderid lên Book", "error")
                        return False
                else:
                    log_server("Lỗi khi tạo Textfolderid và Audiofolderid", "error")
                    return False     
            else: 
                log_server("không tạo được folder_id", "error")
                return False
        else:
            if book["AudioFolderId"] is None:
                audio_folder_id = create_child_folder_id("audio", book["Folderid"])
                if audio_folder_id is not None:
                    post_response = put_request('https://server.audiotruyencv.org/api/book/update-folder-id', json={"Id": book["Id"], "Folderid": book["Folderid"], "Textfolderid": book["TextFolderId"], "Audiofolderid": audio_folder_id})
                    if post_response is None:
                        log_server("Lỗi khi update Audiofolderid lên Book", "error")
                        return False
                else:
                    log_server("Lỗi khi tạo Audiofolderid", "error")
                    return False     
            else: 
                audio_folder_id = book["AudioFolderId"]

            folder_id = book["Folderid"]
            text_folder_id = book["TextFolderId"]
            
        if folder_id is not None:
            chapters = get_request(f'https://server.audiotruyencv.org/api/chapter/{book["Id"]}/chapter-not-run')
           
            if chapters is not None:
                
                for chapter in chapters:
                    #refreshToken()
                    server = get_request(f'https://server.audiotruyencv.org/api/server/{app.config["idserver"]}')
                    if server is None:
                        log_server(f'Không tìm thấy server{app.config["idserver"]}', "error")
                        return False    
                    elif server["Status"] == "stop":
                        log_server("Đã đóng server theo yêu cầu")
                        return False
                    elif server["Status"] == "error":  
                        time.sleep(60)
                        # log_server("Server đang ở trạng thái error. Xin hãy kiểm tra hoặc chuyển sang start trước khi chạy")
                        # return False 
                    
                    chapter_data = get_request(f'https://server.audiotruyencv.org/api/chapter/{chapter["Id"]}')
                    if chapter_data is not None:
                        if chapter_data["Status"] == '1':
                            continue
                        statusx = create_file_audio(chapter_data, audio_folder_id, text_folder_id)
                        if statusx != "success":
                            log_server(book["Booknm"] + "-" + chapter_data["Name"] + " - Lỗi khi tạo file audio-" + statusx, "error", book["Id"], chapter_data["Id"])
                            #return False
                        else:
                            log_server(book["Booknm"] + "-" + chapter_data["Name"] + " - Tạo file audio thành công", None, book["Id"], chapter_data["Id"])
                    else:
                        log_server(book["Booknm"] + "-" + chapter["Name"] + " - không tìm thấy chapter", "error", book["Id"], chapter["Id"])
            else:
                log_server("Không tìm thấy chapters chưa tạo audio", "error")
        else: 
            log_server("Không tìm thấy folder_id", "error")

        log_server(book["Booknm"] + "-" + "- Tạo all audio thành công", "stop")

    else:
        log_server(f'không tìm thấy bookId-{id}', "error")
    


def create_audio_chapter_book(bookid, chapterid):
    folder_id = ""
    audio_folder_id = ""
    text_folder_id = ""
    book = get_request(f'https://server.audiotruyencv.org/api/book/{bookid}')

    if book is not None:
        if book["Folderid"] is None:
            folder_id = create_folder_id(book["Booknm"])
            if folder_id is not None:
                audio_folder_id = create_child_folder_id("audio", folder_id)
                text_folder_id = create_child_folder_id("text", folder_id)
                if audio_folder_id is not None and text_folder_id is not None:
                    post_response = put_request('https://server.audiotruyencv.org/api/book/update-folder-id', json={"Id": book["Id"], "Folderid": folder_id, "Textfolderid": text_folder_id, "Audiofolderid": audio_folder_id})
                    if post_response is None:
                        log_server("Lỗi khi update Textfolderid và Audiofolderid lên Book", "error")
                        return False
                else:
                    log_server("Lỗi khi tạo Textfolderid và Audiofolderid", "error")
                    return False     
            else: 
                log_server("không tạo được folder_id", "error")
                return False
        else:
            if book["AudioFolderId"] is None:
                audio_folder_id = create_child_folder_id("audio", book["Folderid"])
                if audio_folder_id is not None:
                    post_response = put_request('https://server.audiotruyencv.org/api/book/update-folder-id', json={"Id": book["Id"], "Folderid": book["Folderid"], "Textfolderid": book["TextFolderId"], "Audiofolderid": audio_folder_id})
                    if post_response is None:
                        log_server("Lỗi khi update Audiofolderid lên Book", "error")
                        return False
                else:
                    log_server("Lỗi khi tạo Audiofolderid", "error")
                    return False     
            else: 
                audio_folder_id = book["AudioFolderId"]
            folder_id = book["Folderid"]
            text_folder_id = book["TextFolderId"]
            
        if folder_id is not None:
            server = get_request(f'https://server.audiotruyencv.org/api/server/{app.config["idserver"]}')
            if server is None:
                log_server(f'Không tìm thấy server{app.config["idserver"]}', "error")
                return False    
            elif server["Status"] == "stop":
                log_server("Đã đóng server theo yêu cầu")
                return False  
            elif server["Status"] == "error":  
                log_server("Server đang ở trạng thái error. Xin hãy kiểm tra hoặc chuyển sang start trước khi chạy")
                return False   
            
            chapter_data = get_request(f'https://server.audiotruyencv.org/api/chapter/{chapterid}')
            if chapter_data is not None:
                if chapter_data["Status"] == '1':
                    log_server(book["Booknm"] + "-" + chapter_data["Name"] + " - chương đã được tạo audio trước" + statusx, "error", book["Id"], chapter_data["Id"])
                    return False
                statusx = create_file_audio(chapter_data, audio_folder_id, text_folder_id)
                if statusx != "success":
                    log_server(book["Booknm"] + "-" + chapter_data["Name"] + " - Lỗi khi tạo file audio-" + statusx, "error", book["Id"], chapter_data["Id"])
                else:
                    log_server(book["Booknm"] + "-" + chapter_data["Name"] + " - Tạo file audio thành công ", "stop")
                
            else:
                log_server(book["Booknm"] + "-" + chapter_data["Name"] + " - không tìm thấy chapter", "error", book["Id"], chapter_data["Id"])
        else: 
            log_server("Không tìm thấy folder_id", "error")
    else:
        log_server(f'không tìm thấy bookId-{bookid}', "error")



def log_server(Log, Status=None, Bookid=None, Chapterid=None):
    server = get_request(f'https://server.audiotruyencv.org/api/server/{app.config["idserver"]}')
    if Bookid is not None:
        server["Bookid"] = Bookid
    if Chapterid is not None:
        server["Chapterid"] = Chapterid
    if Status is not None:
        server["Status"] = Status
    server["Log"] = Log
    put_response = put_request(f'https://server.audiotruyencv.org/api/server/{server["Id"]}', json=server)
    if put_response is None:
        return False
    return True

def refreshToken():
    dataJwt = post_request(f'https://server.audiotruyencv.org/account/refresh-token')
    app.config['jwt'] = dataJwt['JwtToken']
    refreshToken = get_request(f'https://server.audiotruyencv.org/account/refresh-token-cookie')
    app.config['refreshToken'] = refreshToken['RefreshToken']

@app.route('/create_audio_all_chapter_by_book_id', methods=["GET"])
def create_audio_all_chapter_by_book_id_api():
    try:
        id = request.args.get('id')
        app.config['idserver'] = request.args.get('idserver')
        app.config['jwt'] = request.args.get('jwt')
        app.config['refreshToken'] = request.args.get('refreshtoken')

        if id is not None and app.config['idserver'] is not None:
           delete_all_file()
           create_audio_all_chapter_by_book_id(id)
    except Exception as e:
        exception_info = {
        "type": type(e).__name__,
        "message": str(e),
        "traceback": traceback.format_exc()
        }
        log_server("Lỗi api create_audio_all_chapter_by_book_id" + str(exception_info), "error")

    return "đã hoàn thành tất cả các chapter của book"

@app.route('/create_audio_chapter', methods=["GET"])
def create_audio_chapter():
    try:
        bookid = request.args.get('bookid')
        chapterid = request.args.get('chapterid')
        app.config['idserver'] = request.args.get('idserver')
        app.config['jwt'] = request.args.get('jwt')
        app.config['refreshToken'] = request.args.get('refreshtoken')
        if bookid is not None and chapterid is not None and app.config['idserver'] is not None:
           delete_all_file()
           create_audio_chapter_book(bookid, chapterid)
    except Exception as e:
        print(e)

    return "đã hoàn thành chapter"

@app.route('/')
def hello_world():
    return 'hello_world!'


# $ export FLASK_APP="app.py"
# $ export FLASK_ENV=development
# $ export FLASK_RUN_CERT=adhoc

# $ flask run
#  * Serving Flask app "app.py" (lazy loading)
#  * Environment: development
#  * Debug mode: on
#  * Running on https://127.0.0.1:5000/ (Press CTRL+C to quit)
#  * Restarting with stat
#  * Debugger is active!
#  * Debugger PIN: 329-665-000
