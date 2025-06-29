from flask import send_file
from werkzeug.utils import secure_filename
import io
# ...existing code...
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from flask import Flask, request, jsonify, session, render_template
from flask_cors import CORS
from datetime import timedelta
from ingress_tracker import IngressHackTracker

# 確保 app 實例在全域（gunicorn app:app 需要）
app = Flask(__name__)

# (1) 固定的印章 (必要的)
# 從環境變數讀取 SECRET_KEY，讓 session 在伺服器重啟後依然有效
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_default_secret_key_for_local_dev')

# (2) 允許跨網域Cookie的安全設定 (必要的)
# 讓瀏覽器同意在跨網域時發送 session cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True

# (3) 門禁系統，指定誰可以進來 (必要的)
# 告訴伺服器只接受來自您 GitHub Pages 網站的請求
CORS(app, origins=["https://tulacu.github.io"], supports_credentials=True, allow_headers="*")

# 創建一個全域的 tracker 實例。在真實的多人應用中，你可能需要為每個用戶管理數據。
# 但根據原始腳本的設計，這是一個共享的追蹤器。

tracker = IngressHackTracker()
# 啟動時自動載入本地 CSV（假設是 tab 分隔，欄位名稱為中文）
csv_path = 'ingress_hack_data.csv'
if os.path.exists(csv_path):
    tracker.load_from_csv(csv_path)

# --- 輔助函數 ---
# --- 輔助函數 ---
def is_authenticated():
    """檢查使用者是否已登入"""
    return session.get('authenticated', False)

# --- API Endpoints (路由) ---

# --- 上傳 CSV API ---
@app.route('/api/upload_csv', methods=['POST'])
def upload_csv():
    """上傳 CSV 並立即載入資料"""
    print("[LOG] 收到 /api/upload_csv 請求")
    if not is_authenticated():
        print("[LOG] 未登入，拒絕上傳")
        return jsonify({'error': '請先登入'}), 401

    # 支援前端直接傳 csv 字串
    csv_content = request.form.get('csv')
    if csv_content:
        try:
            count = tracker.load_from_csv_content(csv_content)
            print(f"[LOG] CSV 字串上傳並載入成功，新增 {count} 筆")
            return jsonify({'status': 'success', 'message': f'CSV 已上傳並載入，新增 {count} 筆', 'data': tracker.hack_data})
        except Exception as e:
            print(f"[LOG] CSV 字串載入失敗: {e}")
            return jsonify({'status': 'error', 'message': f'CSV 載入失敗: {e}'}), 500

    # 傳統檔案上傳
    if 'file' in request.files:
        file = request.files['file']
        if file.filename == '':
            print("[LOG] 未選擇檔案")
            return jsonify({'error': '未選擇檔案'}), 400
        try:
            tracker.load_from_csv(file.stream)
            print("[LOG] CSV 檔案上傳並載入成功")
            return jsonify({'status': 'success', 'message': 'CSV 已上傳並載入', 'data': tracker.hack_data})
        except Exception as e:
            print(f"[LOG] CSV 檔案載入失敗: {e}")
            return jsonify({'status': 'error', 'message': f'CSV 載入失敗: {e}'}), 500

    print("[LOG] 未收到 csv 字串或檔案")
    return jsonify({'error': '未收到 csv 字串或檔案'}), 400

@app.route('/')
def index():
    """提供前端網頁"""
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    """登入 API"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if username in tracker.valid_credentials and tracker.valid_credentials[username] == password:
        session['authenticated'] = True
        session['username'] = username
        session.permanent = True # 使用 PERMANENT_SESSION_LIFETIME
        return jsonify({'status': 'success', 'username': username})
    else:
        return jsonify({'status': 'error', 'message': '帳號或密碼錯誤'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    """登出 API"""
    session.clear()
    return jsonify({'status': 'success'})

@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    """檢查登入狀態 API"""
    if is_authenticated():
        return jsonify({'authenticated': True, 'username': session.get('username')})
    return jsonify({'authenticated': False})

@app.route('/api/data', methods=['GET', 'POST', 'DELETE'])
def handle_data():
    """處理數據的獲取、新增和刪除"""
    if not is_authenticated():
        return jsonify({'error': '請先登入'}), 401

    if request.method == 'GET':
        return jsonify(tracker.hack_data)
    
    if request.method == 'POST':
        hack_record = request.get_json()
        hack_count = hack_record.get('hackCount', 1)
        items = {col: hack_record.get(col, 0) for col in tracker.item_columns}
        
        if tracker.add_hack_data(hack_count, **items):
            return jsonify({'status': 'success', 'message': '資料已新增'})
        return jsonify({'status': 'error', 'message': '新增資料失敗'}), 500

    if request.method == 'DELETE':
        if tracker.clear_all_data():
             return jsonify({'status': 'success', 'message': '所有資料已清空'})
        return jsonify({'status': 'error', 'message': '清空資料失敗，或操作被取消'}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """獲取統計數據 API"""
    if not is_authenticated():
        return jsonify({'error': '請先登入'}), 401
    return jsonify(tracker.get_stats())

@app.route('/api/github/config', methods=['GET', 'POST'])
def github_config():
    """處理 GitHub 設定的儲存與載入"""
    if not is_authenticated():
        return jsonify({'error': '請先登入'}), 401
        
    if request.method == 'POST':
        config = request.get_json()
        tracker.save_github_config(config['repo'], config['token'], config['filename'])
        return jsonify({'status': 'success', 'message': 'GitHub 設定已儲存'})
    
    if request.method == 'GET':
        return jsonify(tracker.github_config)

@app.route('/api/github/sync', methods=['POST'])
def sync_from_github():
    """從 GitHub 同步資料 API"""
    if not is_authenticated():
        return jsonify({'error': '請先登入'}), 401
    
    success = tracker.sync_from_github()
    if success:
        return jsonify({'status': 'success', 'message': '同步成功', 'data': tracker.hack_data})
    return jsonify({'status': 'error', 'message': '同步失敗'}), 500

@app.route('/api/github/upload', methods=['POST'])
def upload_to_github():
    """上傳資料到 GitHub API"""
    if not is_authenticated():
        return jsonify({'error': '請先登入'}), 401
        
    success = tracker.upload_to_github()
    if success:
        return jsonify({'status': 'success', 'message': '上傳成功'})
    return jsonify({'status': 'error', 'message': '上傳失敗'}), 500

@app.route('/api/export/csv', methods=['GET'])
def export_csv():
    """匯出 CSV API"""
    if not is_authenticated():
        return jsonify({'error': '請先登入'}), 401

    csv_content = tracker.generate_csv_content()
    return jsonify({'filename': f"ingress_hack_data_{tracker.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", 'content': csv_content})

# --- 啟動伺服器 ---
if __name__ == '__main__':
    # 確保 templates 資料夾存在，Flask 預設會從這裡找 html
    if not os.path.exists('templates'):
        os.makedirs('templates')
    # 將 index.html 移入 templates 資料夾
    if os.path.exists('index.html') and not os.path.exists('templates/index.html'):
        os.rename('index.html', 'templates/index.html')
        
    print("伺服器即將啟動於 http://127.0.0.1:5000")
    print("請用瀏覽器開啟此網址")
    app.run(debug=True, port=5000)