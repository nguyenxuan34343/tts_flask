from flask import Flask, request
from flask import send_file
from underthesea import sent_tokenize
from underthesea import text_normalize
from pydub import AudioSegment
from vietnam_number import n2w
from pyvi import ViTokenizer
from gtts import gTTS
import os
import re
import subprocess
import time
import requests
import json

app = Flask(__name__)


def change_speed(input_file, output_file, speed):
    # Sử dụng ffmpeg để thay đổi tốc độ âm thanh của file WAV
    cmd = f'ffmpeg -i {input_file} -filter:a "atempo={speed}" -vn {output_file}'
    subprocess.call(cmd, shell=True)


def remove_meaningless_characters(text):
    meaningless_chars = ['-', '_', '(', ')', '[', ']', '{', '}', '<', '>', '*', '/', '\\', '|', '@', '#', '$', '%', '^', '&', '=', '+', '~', '`', '"', "'", '\n', '\r', '\t']

    for char in meaningless_chars:
        text = text.replace(char, '')

    return text

def text_to_speech(text, filename):
    tts = gTTS(text=text, lang='vi')
    tts.save(filename)

def delete_all_file():
    for file_name in os.listdir("./"):
        if file_name.endswith((".wav", ".mp3",".txt")):
            file_path = os.path.join("./", file_name)
            os.remove(file_path)

def contains_valid_characters(text):
    return any(char not in (',', '.', ' ') for char in text)

def filter_elements_with_valid_characters(input_list):
    return [item for item in input_list if contains_valid_characters(item.strip())]

def add_guide(text):
    command_tts = ""
    step = ""
    text_cut = ""
    try:
        text_cut_nomal = sent_tokenize(text)
        text_cut_nomal = list(map(remove_meaningless_characters, text_cut_nomal))
        text_cut = list(map(text_normalize, text_cut_nomal))
        text_cut = filter_elements_with_valid_characters(text_cut)
        for i in range(len(text_cut)):
            text_to_speech(text_cut[i], f'clip{i}.mp3')
            print(i)
            print(text_cut[i])
            time.sleep(3)
            AudioSegment.from_file(f'./clip{i}.mp3', format="mp3").export(f'./clip{i}.wav', format="wav")

        combined_sounds = AudioSegment.from_wav(f'clip0.wav')
        for i in range(len(text_cut)):
            if i > 0 :
                sound = AudioSegment.from_wav(f'clip{i}.wav')
                combined_sounds += sound

        combined_sounds.export("clipinput.wav", format="wav")

        change_speed("clipinput.wav", "clip.wav", 1.45)

        AudioSegment.from_wav("clip.wav").export("clip.mp3", format="mp3")

    except Exception as e:
        print(e)
        return None

    return True


def get_request(url, params=None):
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Nếu có lỗi, raise exception
        return response.json()
    except requests.exceptions.RequestException as e:
        print('Yêu cầu GET không thành công:', e)
        return None

def post_request(url, data=None, json=None):
    try:
        response = requests.post(url, data=data, json=json)
        response.raise_for_status()  # Nếu có lỗi, raise exception
        print(response.status_code)
        try:
            return response.json()
        except ValueError as e:
            print('Lấy JSON không thành công:', e)
    except requests.exceptions.RequestException as e:
        print('Yêu cầu POST không thành công:', e)
        return None

def put_request(url, data=None, json=None):
    try:
        response = requests.put(url, data=data, json=json)
        response.raise_for_status()  # Nếu có lỗi, raise exception
        print(response.status_code)
        try:
            return response.json()
        except ValueError as e:
            print('Lấy JSON không thành công:', e)
    except requests.exceptions.RequestException as e:
        print('Yêu cầu PUT không thành công:', e)
        return None

def create_child_folder_id(folder_name, folder_id):
    # Replace 'YOUR_ACCESS_TOKEN' with the actual access token.
    access_token = get_request('https://audiotruyencv.org/api/ggdrive/get-access-token')
    access_token = access_token["token"]
    # Define the API endpoint for creating a folder.
    endpoint = 'https://www.googleapis.com/drive/v3/files'

    # Define the headers for the API request.
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # Define the metadata for the folder.
    folder_metadata = {
        'name': f'{folder_name}',
        'parents': [f'{folder_id}'],  # Replace with the desired parent folder ID
        'mimeType': 'application/vnd.google-apps.folder'
    }

    # Send the POST request to create the folder.
    response = requests.post(endpoint, headers=headers, json=folder_metadata)

    if response.status_code == 200:
        folder_data = response.json()
        folder_id = folder_data['id']
        return folder_id
    else:
        return None

def create_folder_id(folder_name):
    # Replace 'YOUR_ACCESS_TOKEN' with the actual access token.
    access_token = get_request('https://audiotruyencv.org/api/ggdrive/get-access-token')
    access_token = access_token["token"]
    # Define the API endpoint for creating a folder.
    endpoint = 'https://www.googleapis.com/drive/v3/files'

    # Define the headers for the API request.
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # Define the metadata for the folder.
    folder_metadata = {
        'name': f'{folder_name}',
        'mimeType': 'application/vnd.google-apps.folder'
    }

    # Send the POST request to create the folder.
    response = requests.post(endpoint, headers=headers, json=folder_metadata)

    if response.status_code == 200:
        folder_data = response.json()
        folder_id = folder_data['id']
        return folder_id
    else:
        return None

def upload_audio_on_folder_id(file_name ,folder_id):
    # Replace 'YOUR_ACCESS_TOKEN' with the actual access token.
    access_token = get_request('https://audiotruyencv.org/api/ggdrive/get-access-token')
    access_token = access_token["token"]
    # Define the API endpoint for file uploads.
    endpoint = 'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart'

    # Define the headers for the API request.
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

        # Define the metadata of the file to be uploaded.
    metadata = {
        'name': f'{file_name}.mp3',
        'parents': [f'{folder_id}']  # Replace with the desired parent folder ID
    }

    # Define the path to the file on your local machine.
    file_path = './clip.mp3'

    files = {
        'data': ('metadata', json.dumps(metadata), 'application/json; charset=UTF-8'),
        'file': open(file_path, "rb")
    }

    # Send the POST request to upload the file.
    response = requests.post(endpoint, headers=headers, files=files)

    if response.status_code == 200:
        uploaded_file_data = response.json()
        file_id = uploaded_file_data['id']
        return file_id
    else:
        return None

def upload_text_on_folder_id(file_name ,folder_id, text):
    # Replace 'YOUR_ACCESS_TOKEN' with the actual access token.
    access_token = get_request('https://audiotruyencv.org/api/ggdrive/get-access-token')
    access_token = access_token["token"]
    # Define the API endpoint for file uploads.
    endpoint = 'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart'

    # Define the headers for the API request.
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

        # Define the metadata of the file to be uploaded.
    metadata = {
        'name': f'{file_name}.txt',
        'parents': [f'{folder_id}']  # Replace with the desired parent folder ID
    }

    with open('chapter.txt', 'w') as f:
        f.write(text)

    # Define the path to the file on your local machine.
    file_path = './chapter.txt'

    files = {
        'data': ('metadata', json.dumps(metadata), 'application/json; charset=UTF-8'),
        'file': open(file_path, "rb")
    }

    # Send the POST request to upload the file.
    response = requests.post(endpoint, headers=headers, files=files)

    if response.status_code == 200:
        uploaded_file_data = response.json()
        file_id = uploaded_file_data['id']
        return file_id
    else:
        return None

def get_all_folder():
    # Replace 'YOUR_ACCESS_TOKEN' with the actual access token.
    access_token = get_request('https://audiotruyencv.org/api/ggdrive/get-access-token')
    access_token = access_token["token"]
    # Define the API endpoint.
    endpoint = 'https://www.googleapis.com/drive/v3/files'

    # Define the headers for the API requests.
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    # Send a GET request to list files in Drive.
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
    # Replace 'YOUR_ACCESS_TOKEN' with the actual access token.
    access_token = get_request('https://audiotruyencv.org/api/ggdrive/get-access-token')
    access_token = access_token["token"]

    # Define the API endpoint for retrieving files.
    endpoint = 'https://www.googleapis.com/drive/v3/files'

    # Define the headers for the API request.
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    # Define the query parameters to search for files within the specified folder.
    params = {
        'q': f"'{folder_id}' in parents",
        'fields': 'files(id, name)'
    }

    # Send the GET request to retrieve the files.
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
        chapter_content = chapter["content"]
        if chapter_content is not None:
            status_add_guide = add_guide(chapter["content"])
            if status_add_guide is not None :
                status_upload_audio_on_folder_id = upload_audio_on_folder_id(chapter["id"], audio_folder_id)
                status_upload_text_on_folder_id = upload_text_on_folder_id(chapter["id"], text_folder_id, chapter["content"])
            if status_upload_audio_on_folder_id is not None and status_upload_text_on_folder_id is not None:
                post_response = put_request('https://audiotruyencv.org/api/chapter/update-info', json={"id" : chapter["id"], "status" : "1", "audiofileid": status_upload_audio_on_folder_id, "textfileid": status_upload_text_on_folder_id})
                print("end chapter")
                if post_response is None :
                    return False
            return True
        else:
            post_response = put_request('https://audiotruyencv.org/api/chapter/update-info', json={"id" : chapter["id"], "status" : "2"})
            return None
    except Exception as e:
            #print(e)
            post_response = put_request('https://audiotruyencv.org/api/chapter/update-info', json={"id" : chapter["id"], "status" : "2"})
            return None

def create_audio_all_chapter_by_book_id(id):
    # lấy sách
    folder_id = ""
    audio_folder_id = ""
    text_folder_id = ""
    book = get_request(f'https://audiotruyencv.org/api/book/{id}')
    if book is not None:
        if book["folderid"] is None :
            folder_id = create_folder_id(book["id"])
            if folder_id is not None:
                audio_folder_id = create_child_folder_id("audio", folder_id)
                text_folder_id = create_child_folder_id("text", folder_id)
                if audio_folder_id is not None and text_folder_id is not None:
                  post_response = put_request('https://audiotruyencv.org/api/book/update-folder-id', json={"id" : book["id"], "folderid" : folder_id, "textfolderid" : text_folder_id, "audiofolderid" : audio_folder_id})
                  if post_response is None :
                      return False
        else :
            folder_id = book["folderid"]
            audio_folder_id = book["audioFolderId"]
            text_folder_id = book["textFolderId"]
        if folder_id is not None :
            # lấy tất cả sách
            chapters = get_request(f'https://audiotruyencv.org/api/chapter/all/{book["id"]}')
            if chapters is not None:
                for x in chapters:
                    if x["status"] == '1':
                        continue
                    statusx = create_file_audio(x, audio_folder_id, text_folder_id)
                    delete_all_file()
                    time.sleep(30)  # Tạm dừng chương trình trong 30 giây.

def create_audio_all_book():
    # lấy tất cả sách
    books = get_request('https://audiotruyencv.org/api/book')
    if books is not None:
        for x in books:
            create_audio_all_chapter_by_book_id(x["id"])

# Endpoint to create mp3 from text
@app.route('/create_audio_book', methods=["GET"])
def create_audio_book():
    try:
        # Lấy giá trị của tham số id từ query string
        id = request.args.get('id')

        if id is not None:
            create_audio_all_chapter_by_book_id(id)
    except Exception as e:
            print("a" + e)
    # Trả về kết quả dưới dạng JSON
    return "đã hoàn thành tất cả các chapter của book"

# Endpoint to create mp3 from text
@app.route('/create_audio_all_book', methods=["GET"])
def create_audio_all_book():
    try:
       create_audio_all_book()
    except Exception as e:
            print("a" + e)
    # Trả về kết quả dưới dạng JSON
    return "đã hoàn thành tất cả các book"


@app.route('/')
def hello_world():
    return 'hello_world!'


@app.route('/download')
def downloadFile ():
    #For windows you need to use drive name [ex: F:/Example.pdf]
    path = "./clip.mp3"
    return send_file(path, as_attachment=True)
