#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from flask import Flask, request, jsonify, session, render_template
from flask_cors import CORS
from datetime import timedelta
from ingress_tracker import IngressHackTracker

# =========================================================
# ▼▼▼ 正確的位置在這裡 ▼▼▼
# 緊接著 import 語句之後，在任何函式或路由定義之前
app = Flask(__name__)
# =========================================================

# --- Flask App 初始化 ---
app.config['SECRET_KEY'] = os.urandom(24) 
# 設定 session 的生命週期，例如 24 小時
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
# 之後請將 'https://your-username.github.io' 換成你真正的 GitHub Pages 網址
origins = [
    "https://tulacu.github.io", 
    "http://127.0.0.1:5000" # 保留本機測試用
]
CORS(app, resources={r"/api/*": {"origins": origins}}, supports_credentials=True)

# 創建一個全域的 tracker 實例。在真實的多人應用中，你可能需要為每個用戶管理數據。
# 但根據原始腳本的設計，這是一個共享的追蹤器。
tracker = IngressHackTracker()

# --- 輔助函數 ---
def is_authenticated():
    """檢查使用者是否已登入"""
    return session.get('authenticated', False)

# --- API Endpoints (路由) ---

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