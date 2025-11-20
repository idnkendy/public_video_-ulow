from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import time
import json
import base64
import io
from PIL import Image

app = Flask(__name__)
CORS(app)

# ================= CẤU HÌNH (CẬP NHẬT TOKEN MỚI NHẤT CỦA BẠN) =================
HEADERS = {
    'accept': '*/*',
    # --- DÁN TOKEN CỦA BẠN VÀO DƯỚI ---
    'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImtlbmR5IiwiYXVkIjoiaHR0cHM6Ly9jb2luMTQubmV0IiwiaXNzIjoiY29pbjE0LWF1dGgiLCJpYXQiOjE3NjM2NDE3ODcsImV4cCI6MTc2NDI0NjU4N30.gbOb2JARNjZrBKYPfLCnT4tXeYlt9K1yj4p0Ixfgk7o', 
    'content-type': 'application/json',
    'origin': 'https://promptmarketcap.net',
    'referer': 'https://promptmarketcap.net/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
}

COOKIES = {
    # --- DÁN COOKIE CỦA BẠN VÀO DƯỚI ---
    'session': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImtlbmR5IiwiYXVkIjoiaHR0cHM6Ly9jb2luMTQubmV0IiwiaXNzIjoiY29pbjE0LWF1dGgiLCJpYXQiOjE3NjM2NDE3ODcsImV4cCI6MTc2NDI0NjU4N30.gbOb2JARNjZrBKYPfLCnT4tXeYlt9K1yj4p0Ixfgk7o', 
    '_ga': 'GA1.1.959723901.1763641764'
}

URL_UPLOAD = 'https://promptmarketcap.net/api/veo3/upload-image'
URL_AGENT = 'https://flow.coin14.net/webhook/ai-agent'
PROJECT_ID = 'b8f8c699-65bc-4afd-b9ca-780f54dbc50c'

# ================= HÀM HỖ TRỢ =================
def compress_image(base64_string):
    try:
        if "," in base64_string: header, encoded = base64_string.split(",", 1)
        else: encoded = base64_string
        img_data = base64.b64decode(encoded)
        img = Image.open(io.BytesIO(img_data))
        if img.width > 1024:
            ratio = 1024 / float(img.width)
            new_height = int((float(img.height) * float(ratio)))
            img = img.resize((1024, new_height), Image.Resampling.LANCZOS)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        new_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/jpeg;base64,{new_base64}"
    except Exception as e:
        print(f"Lỗi nén ảnh: {e}")
        return base64_string

# ================= CÁC HÀM XỬ LÝ CHÍNH =================

def upload_image(base64_string):
    compressed = compress_image(base64_string)
    print("1. Đang upload ảnh...")
    payload = {'rowId': 1, 'base64Image': compressed, 'type': 'start'}
    try:
        res = requests.post(URL_UPLOAD, headers=HEADERS, cookies=COOKIES, json=payload)
        if res.status_code == 200:
            data = res.json()
            media_id = data.get('mediaId') or data.get('id')
            print(f"-> Upload xong. Media ID: {media_id}")
            return media_id
        else:
            print(f"Lỗi Upload: {res.text}")
            return None
    except Exception as e:
        print(f"Lỗi kết nối Upload: {e}")
        return None

def trigger_video(prompt, start_media_id=None):
    print(f"2. Đang gửi lệnh tạo video: '{prompt}'")
    params = {
        'project': PROJECT_ID, 'action': 'video', 'service': 'veo3',
        'query': 'video', 'status': 'new',
        'model': 'veo3_1-fast-image', 'ratio': 'landscape_16_9'
    }
    video_obj = {'id': '1', 'prompt': prompt, 'number': '1', 'frame': '1'}
    if start_media_id: video_obj['startMediaId'] = start_media_id
    json_data = [{'videos': [video_obj]}]

    try:
        res = requests.post(URL_AGENT, headers=HEADERS, params=params, json=json_data)
        if res.status_code == 200:
            data = res.json()
            # --- SỬA LỖI: DÙNG KEY 'operations' ---
            try:
                op_item = data[0]['operations'][0]
                task_id = op_item['operation']['name']
                scene_id = op_item['sceneId']
                print(f"-> Đã tạo Task! ID: {task_id} | Scene: {scene_id}")
                return task_id, scene_id
            except:
                print("Lỗi cấu trúc Trigger:", json.dumps(data))
                return None, None
        else:
            print(f"Lỗi Trigger: {res.text}")
            return None, None
    except Exception as e:
        print(f"Lỗi kết nối Trigger: {e}")
        return None, None

def check_status_loop(task_id, scene_id):
    print(f"3. Bắt đầu theo dõi Task ID: {task_id}")
    params = {
        'project': PROJECT_ID, 'action': 'video', 'service': 'veo3',
        'query': 'video', 'status': 'check'
    }
    final_scene_id = scene_id if scene_id else '6d2056e9-f929-4f13-bb25-6e5a49a7fbcc'
    json_data = [{
        'videos': [{
            'id': '1',
            'query': [{
                'id': '1', 'operation': {'name': task_id}, 'sceneId': final_scene_id 
            }]
        }]
    }]

    for i in range(120):
        time.sleep(5)
        try:
            res = requests.post(URL_AGENT, headers=HEADERS, params=params, json=json_data)
            if res.status_code == 200:
                data = res.json()
                try:
                    op_item = data[0]['operations'][0]
                    status = op_item.get('status')
                    
                    # --- SỬA LỖI Ở ĐÂY: LẤY KEY 'video_url' ---
                    url = op_item.get('video_url')
                    
                    if url and "http" in url:
                        print(f"-> 🎉 HOÀN THÀNH! Video: {url}")
                        return url
                    
                    if status and 'SUCCESSFUL' in status:
                         # Fallback nếu key video_url bị đổi, thử tìm lại lần nữa
                         url = op_item.get('url') or op_item.get('resultUrl')
                         if url: return url

                    if status and 'FAILED' in status:
                        print("-> Thất bại:", op_item)
                        return None
                        
                    print(f"   [Lần {i+1}] Status: {status}")
                except Exception as parse_err:
                    pass
        except Exception as e:
            print(f"Lỗi check: {e}")
    return None
# ================= API ENDPOINT =================
@app.route('/run-video', methods=['POST'])
def api_handle():
    input_data = request.json
    prompt = input_data.get('prompt')
    image_base64 = input_data.get('image')
    
    if not prompt: return jsonify({'status': 'error', 'message': 'Thiếu prompt'}), 400

    media_id = None
    if image_base64:
        media_id = upload_image(image_base64)
        if not media_id: return jsonify({'status': 'error', 'message': 'Lỗi upload ảnh'}), 500

    task_id, scene_id = trigger_video(prompt, media_id)
    if not task_id: return jsonify({'status': 'error', 'message': 'Lỗi tạo video'}), 500

    final_url = check_status_loop(task_id, scene_id)
    
    if final_url: return jsonify({'status': 'success', 'video_url': final_url})
    else: return jsonify({'status': 'timeout', 'message': 'Quá thời gian chờ'}), 504

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
