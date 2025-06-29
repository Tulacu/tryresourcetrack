import csv


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ingress Portal Hack 數據追蹤器
功能：追蹤和分析 Ingress 遊戲中的 Portal Hack 獲得物資數據
"""

import json
import csv
import os
import hashlib
from datetime import datetime
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
import pandas as pd
import requests
import base64

class IngressHackTracker:
    def load_from_csv(self, file_stream) -> int:
        """
        從檔案流匯入 CSV 資料，回傳成功匯入的筆數，並自動轉換成 UTF-8
        """
        import io
        content = None
        if hasattr(file_stream, 'read'):
            raw = file_stream.read()
            # 嘗試多種編碼
            for encoding in ['utf-8-sig', 'utf-8', 'big5', 'cp950']:
                try:
                    content = raw.decode(encoding)
                    # 若不是 utf-8，則自動轉存 utf-8
                    if encoding not in ['utf-8', 'utf-8-sig']:
                        # 重新以 utf-8 儲存一份
                        with open('last_uploaded_utf8.csv', 'w', encoding='utf-8') as f:
                            f.write(content)
                    break
                except Exception:
                    continue
            if content is None:
                raise ValueError("CSV 檔案編碼無法辨識，請另存為 UTF-8 再上傳")
        else:
            content = str(file_stream)
        return self.load_from_csv_content(content)
    def __init__(self, data_file: str = "ingress_hack_data.json"):
        """初始化追蹤器"""
        self.data_file = data_file
        self.hack_data = []
        self.authenticated = False
        self.current_user = None
        self.github_config = {}
        
        # 預設帳號密碼 (實際使用時請修改)
        self.valid_credentials = {
            'tulacu': '611450',
            'winnietest': 'winnie123'
        }
        
        # 物資欄位名稱
        self.item_columns = [
            'L7Res', 'L8Res', 'L7XMP', 'L8XMP', 'L7US', 'L8US', 'L7PC', 'L8PC', 
            'Cshield', 'Rshield', 'VRShield', 'AXAShield', 'Else', 
            'Cmod', 'Rmod', 'VRmod', 'Virus'
        ]
        
        # 物資中文名稱對應
        self.item_names = {
            'L7Res': 'L7 共振器',
            'L8Res': 'L8 共振器',
            'L7XMP': 'L7 XMP',
            'L8XMP': 'L8 XMP',
            'L7US': 'L7 超擊',
            'L8US': 'L8 超擊',
            'L7PC': 'L7 能量方塊',
            'L8PC': 'L8 能量方塊',
            'Cshield': '普通護盾',
            'Rshield': '稀有護盾',
            'VRShield': '極稀有護盾',
            'AXAShield': 'AXA 護盾',
            'Else': '其他物品',
            'Cmod': '普通模組',
            'Rmod': '稀有模組',
            'VRmod': '極稀有模組',
            'Virus': '病毒'
        }
        
        self.load_data()
        self.load_github_config()
        
    def login(self, username: str, password: str) -> bool:
        """登入功能"""
        if username in self.valid_credentials and self.valid_credentials[username] == password:
            self.authenticated = True
            self.current_user = username
            print(f"✅ 登入成功！歡迎 {username}")
            return True
        else:
            print("❌ 帳號或密碼錯誤！")
            return False
    
    def logout(self):
        """登出功能"""
        self.authenticated = False
        self.current_user = None
        print("🚪 已登出！")
    
    def check_auth(self) -> bool:
        """檢查是否已登入"""
        if not self.authenticated:
            print("❌ 請先登入才能使用此功能！")
            return False
        return True
    
    def save_github_config(self, repo: str, token: str, filename: str = "ingress_hack_data.csv"):
        """儲存 GitHub 設定"""
        if not self.check_auth():
            return
            
        self.github_config = {
            'repo': repo,
            'token': token,
            'filename': filename
        }
        
        with open('github_config.json', 'w', encoding='utf-8') as f:
            json.dump(self.github_config, f, ensure_ascii=False, indent=2)
        
        print("💾 GitHub 設定已儲存！")
    
    def load_github_config(self):
        """載入 GitHub 設定"""
        try:
            if os.path.exists('github_config.json'):
                with open('github_config.json', 'r', encoding='utf-8') as f:
                    self.github_config = json.load(f)
        except Exception as e:
            print(f"⚠️ 載入 GitHub 設定失敗：{e}")
    
    def sync_from_github(self) -> bool:
        """從 GitHub 同步資料"""
        if not self.check_auth():
            return False
            
        if not all(key in self.github_config for key in ['repo', 'token', 'filename']):
            print("❌ 請先設定 GitHub 資訊！")
            return False
        
        try:
            print("🔄 正在從 GitHub 同步資料...")
            
            repo = self.github_config['repo']
            token = self.github_config['token']
            filename = self.github_config['filename']
            
            headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.get(
                f'https://api.github.com/repos/{repo}/contents/{filename}',
                headers=headers
            )
            
            if response.status_code == 200:
                file_data = response.json()
                csv_content = base64.b64decode(file_data['content']).decode('utf-8')
                
                # 解析 CSV
                lines = csv_content.strip().split('\n')
                if len(lines) > 1:
                    headers_list = [h.strip() for h in lines[0].split(',')]
                    github_data = []
                    
                    for line in lines[1:]:
                        if line.strip():
                            values = line.split(',')
                            record = {}
                            for i, header in enumerate(headers_list):
                                if header == 'timestamp':
                                    record[header] = values[i].strip()
                                else:
                                    record[header] = int(values[i]) if values[i].strip() else 0
                            github_data.append(record)
                    
                    # 合併資料（避免重複）
                    existing_timestamps = {r['timestamp'] for r in self.hack_data}
                    new_records = [r for r in github_data if r['timestamp'] not in existing_timestamps]
                    
                    self.hack_data.extend(new_records)
                    self.save_data()
                    
                    print(f"✅ 成功從 GitHub 同步資料！新增了 {len(new_records)} 筆記錄。")
                    return True
                else:
                    print("⚠️ GitHub 上沒有找到資料檔案。")
                    return False
            elif response.status_code == 404:
                print("⚠️ GitHub 上沒有找到資料檔案。")
                return False
            else:
                print(f"❌ 同步失敗：HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 從 GitHub 同步資料失敗：{e}")
            return False
    
    def upload_to_github(self) -> bool:
        """上傳資料到 GitHub"""
        if not self.check_auth():
            return False
            
        if not all(key in self.github_config for key in ['repo', 'token', 'filename']):
            print("❌ 請先設定 GitHub 資訊！")
            return False
        
        if not self.hack_data:
            print("⚠️ 沒有資料可以上傳！")
            return False
        
        try:
            print("☁️ 正在上傳資料到 GitHub...")
            
            repo = self.github_config['repo']
            token = self.github_config['token']
            filename = self.github_config['filename']
            
            # 生成 CSV 內容
            csv_content = self.generate_csv_content()
            encoded_content = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')
            
            headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            }
            
            # 檢查檔案是否存在
            sha = None
            check_response = requests.get(
                f'https://api.github.com/repos/{repo}/contents/{filename}',
                headers=headers
            )
            
            if check_response.status_code == 200:
                sha = check_response.json()['sha']
            
            # 上傳檔案
            upload_data = {
                'message': f'更新 Ingress hack 資料 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                'content': encoded_content
            }
            
            if sha:
                upload_data['sha'] = sha
            
            upload_response = requests.put(
                f'https://api.github.com/repos/{repo}/contents/{filename}',
                headers=headers,
                json=upload_data
            )
            
            if upload_response.status_code in [200, 201]:
                print("✅ 資料成功上傳到 GitHub！")
                return True
            else:
                print(f"❌ 上傳失敗：HTTP {upload_response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 上傳到 GitHub 失敗：{e}")
            return False
    
    def add_hack_data(self, hack_count: int = 1, **items) -> bool:
        """新增 Hack 數據"""
        if not self.check_auth():
            return False
        
        new_record = {
            'timestamp': datetime.now().isoformat(),
            'hackCount': hack_count
        }
        
        # 添加物資數據
        for column in self.item_columns:
            new_record[column] = items.get(column, 0)
        
        self.hack_data.append(new_record)
        self.save_data()
        
        print("✅ 資料已新增！")
        return True
    
    def get_stats(self) -> Dict:
        """取得統計資料"""
        if not self.hack_data:
            return {
                'total_hacks': 0,
                'total_items': 0,
                'avg_items_per_hack': 0.0,
                'total_records': 0
            }
        
        total_hacks = sum(
            int(record.get('hackCount', 1) or 1)
            for record in self.hack_data
        )
        total_items = sum(
            sum(record.get(column, 0) for column in self.item_columns)
            for record in self.hack_data
        )
        avg_items_per_hack = total_items / total_hacks if total_hacks > 0 else 0.0
        total_records = len(self.hack_data)
        
        return {
            'total_hacks': total_hacks,
            'total_items': total_items,
            'avg_items_per_hack': round(avg_items_per_hack, 2),
            'total_records': total_records
        }
    
    def show_stats(self):
        """顯示統計資料"""
        stats = self.get_stats()
        
        print("\n" + "="*50)
        print("📊 統計摘要")
        print("="*50)
        print(f"總 Hack 次數: {stats['total_hacks']}")
        print(f"總物資數量: {stats['total_items']}")
        print(f"平均每次 Hack 物資量: {stats['avg_items_per_hack']}")
        print(f"總記錄筆數: {stats['total_records']}")
        print("="*50)
    
    def show_item_stats(self):
        """顯示物資統計表格"""
        if not self.hack_data:
            print("⚠️ 沒有資料可以顯示！")
            return
        
        stats = self.get_stats()
        total_hacks = stats['total_hacks']
        total_items = stats['total_items']
        
        print("\n" + "="*80)
        print("📋 詳細物資統計")
        print("="*80)
        print(f"{'物資名稱':<15} {'總獲得量':<10} {'佔總物資比例':<15} {'平均每次Hack獲得量':<20}")
        print("-"*80)
        
        for column in self.item_columns:
            total = sum(record.get(column, 0) for record in self.hack_data)
            if total > 0:
                percentage = (total / total_items * 100) if total_items > 0 else 0
                avg_per_hack = total / total_hacks if total_hacks > 0 else 0
                
                item_name = self.item_names.get(column, column)
                print(f"{item_name:<15} {total:<10} {percentage:<14.2f}% {avg_per_hack:<20.2f}")
        
        print("="*80)
    
    def plot_item_chart(self, save_path: str = "item_chart.png"):
        """繪製物資統計圖表"""
        if not self.hack_data:
            print("⚠️ 沒有資料可以繪圖！")
            return
        
        # 計算各物資總量
        item_totals = {}
        for column in self.item_columns:
            total = sum(record.get(column, 0) for record in self.hack_data)
            if total > 0:
                item_totals[self.item_names.get(column, column)] = total
        
        if not item_totals:
            print("⚠️ 沒有物資資料可以繪圖！")
            return
        
        # 設定中文字型
        plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 創建圖表
        fig, ax = plt.subplots(figsize=(12, 8))
        
        items = list(item_totals.keys())
        values = list(item_totals.values())
        
        bars = ax.bar(items, values, color='skyblue', edgecolor='navy', alpha=0.7)
        
        # 在每個柱子上顯示數值
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                   f'{value}', ha='center', va='bottom')
        
        ax.set_title('Ingress Portal Hack 物資獲得統計', fontsize=16, fontweight='bold')
        ax.set_xlabel('物資類型', fontsize=12)
        ax.set_ylabel('獲得數量', fontsize=12)
        
        # 旋轉 x 軸標籤以避免重疊
        plt.xticks(rotation=45, ha='right')
        
        # 調整版型
        plt.tight_layout()
        
        # 儲存圖表
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"📊 圖表已儲存為 {save_path}")
        
        # 顯示圖表
        plt.show()
    
    def export_to_csv(self, filename: str = None) -> bool:
        """匯出資料到 CSV"""
        if not self.check_auth():
            return False
        
        if not self.hack_data:
            print("⚠️ 沒有資料可以匯出！")
            return False
        
        if filename is None:
            filename = f"ingress_hack_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        try:
            csv_content = self.generate_csv_content()
            with open(filename, 'w', encoding='utf-8-sig') as f:
                f.write(csv_content)
            
            print(f"📥 CSV 檔案已匯出：{filename}")
            return True
            
        except Exception as e:
            print(f"❌ 匯出 CSV 失敗：{e}")
            return False
    
    def import_from_csv(self, filename: str) -> bool:
        """從 CSV 匯入資料"""
        if not self.check_auth():
            return False
        
        try:
            with open(filename, 'r', encoding='utf-8-sig') as f:
                csv_content = f.read()
            
            lines = csv_content.strip().split('\n')
            if len(lines) < 2:
                print("❌ CSV 檔案格式不正確！")
                return False
            
            headers = [h.strip() for h in lines[0].split(',')]
            imported_data = []
            
            for line in lines[1:]:
                if line.strip():
                    values = line.split(',')
                    record = {}
                    for i, header in enumerate(headers):
                        if header == 'timestamp':
                            record[header] = values[i].strip()
                        else:
                            record[header] = int(values[i]) if values[i].strip() else 0
                    imported_data.append(record)
            
            # 合併資料（避免重複）
            existing_timestamps = {r['timestamp'] for r in self.hack_data}
            new_records = [r for r in imported_data if r['timestamp'] not in existing_timestamps]
            
            self.hack_data.extend(new_records)
            self.save_data()
            
            print(f"✅ 成功匯入 {len(new_records)} 筆新記錄！")
            return True
            
        except Exception as e:
            print(f"❌ 匯入 CSV 失敗：{e}")
            return False
    
    def generate_csv_content(self) -> str:
        """生成 CSV 內容"""
        if not self.hack_data:
            return ''
        
        headers = ['timestamp', 'hackCount'] + self.item_columns
        csv_lines = [','.join(headers)]
        
        for record in self.hack_data:
            row = [str(record.get(header, 0)) for header in headers]
            csv_lines.append(','.join(row))
        
        return '\n'.join(csv_lines)
    
    def clear_all_data(self) -> bool:
        """清空所有資料"""
        if not self.check_auth():
            return False
        
        confirm = input("⚠️ 確定要清空所有資料嗎？此操作無法復原！(輸入 'YES' 確認): ")
        if confirm == 'YES':
            self.hack_data = []
            self.save_data()
            print("✅ 所有資料已清空！")
            return True
        else:
            print("❌ 操作已取消")
            return False
    
    def load_from_csv_content(self, csv_content: str) -> int:
        """
        從 CSV 字串內容匯入資料，回傳成功匯入的筆數
        """
        from datetime import datetime
        lines = csv_content.strip().split('\n')
        if len(lines) < 2:
            raise ValueError("CSV 檔案格式不正確！")
        headers = [h.strip() for h in lines[0].split(',')]
        has_timestamp = 'timestamp' in headers
        has_hackcount = 'hackCount' in headers
        imported_data = []
        for line in lines[1:]:
            if line.strip():
                values = line.split(',')
                if len(values) != len(headers):
                    continue
                record = {}
                for i, header in enumerate(headers):
                    v = values[i].strip()
                    if header == 'timestamp':
                        record[header] = v if v else datetime.now().isoformat()
                    elif header == 'hackCount':
                        try:
                            record[header] = int(float(v)) if v else 1
                        except Exception:
                            record[header] = 1
                    else:
                        try:
                            record[header] = int(float(v)) if v else 0
                        except Exception:
                            record[header] = 0
                # 若原本就沒有 hackCount 欄，則自動補 1
                if not has_hackcount:
                    record['hackCount'] = 1
                if not has_timestamp:
                    record['timestamp'] = datetime.now().isoformat()
                imported_data.append(record)
        existing_timestamps = {r['timestamp'] for r in self.hack_data}
        new_records = [r for r in imported_data if r['timestamp'] not in existing_timestamps]
        self.hack_data.extend(new_records)
        self.save_data()
        return len(new_records)

    def save_data(self):
        """儲存資料到檔案"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.hack_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 儲存資料失敗：{e}")
    
    def load_data(self):
        """從檔案載入資料"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.hack_data = json.load(f)
        except Exception as e:
            print(f"⚠️ 載入資料失敗：{e}")
            self.hack_data = []

def main():
    """主程式"""
    print("🎮 Ingress Portal Hack 數據追蹤器")
    print("="*50)
    
    tracker = IngressHackTracker()
    
    while True:
        if not tracker.authenticated:
            print("\n🔐 請先登入")
            username = input("帳號: ").strip()
            password = input("密碼: ").strip()
            
            if not tracker.login(username, password):
                continue
        
        print(f"\n歡迎回來, {tracker.current_user}！")
        print("\n選擇功能:")
        print("1. 新增 Hack 資料")
        print("2. 查看統計")
        print("3. 查看詳細物資統計")
        print("4. 繪製圖表")
        print("5. 匯出 CSV")
        print("6. 匯入 CSV")
        print("7. GitHub 設定")
        print("8. 從 GitHub 同步")
        print("9. 上傳到 GitHub")
        print("10. 清空所有資料")
        print("11. 登出")
        print("0. 退出")
        
        choice = input("\n請輸入選項 (0-11): ").strip()
        
        if choice == '1':
            print("\n📝 新增 Hack 資料")
            try:
                hack_count = int(input("Hack次數 (預設1): ") or "1")
                items = {}
                
                print("請輸入各物資數量 (直接按 Enter 表示 0):")
                for column in tracker.item_columns:
                    item_name = tracker.item_names.get(column, column)
                    value = input(f"{item_name}: ").strip()
                    items[column] = int(value) if value else 0
                
                tracker.add_hack_data(hack_count, **items)
                
            except ValueError:
                print("❌ 請輸入有效的數字！")
        
        elif choice == '2':
            tracker.show_stats()
        
        elif choice == '3':
            tracker.show_item_stats()
        
        elif choice == '4':
            save_path = input("圖表儲存路徑 (預設: item_chart.png): ").strip()
            if not save_path:
                save_path = "item_chart.png"
            tracker.plot_item_chart(save_path)
        
        elif choice == '5':
            filename = input("檔案名稱 (預設: 自動產生): ").strip()
            tracker.export_to_csv(filename if filename else None)
        
        elif choice == '6':
            filename = input("CSV 檔案路徑: ").strip()
            if filename and os.path.exists(filename):
                tracker.import_from_csv(filename)
            else:
                print("❌ 檔案不存在！")
        
        elif choice == '7':
            print("\n⚙️ GitHub 設定")
            repo = input("GitHub Repository (例: username/repo-name): ").strip()
            token = input("GitHub Personal Access Token: ").strip()
            filename = input("資料檔案名稱 (預設: ingress_hack_data.csv): ").strip()
            if not filename:
                filename = "ingress_hack_data.csv"
            
            if repo and token:
                tracker.save_github_config(repo, token, filename)
            else:
                print("❌ 請填寫完整的 GitHub 資訊！")
        
        elif choice == '8':
            tracker.sync_from_github()
        
        elif choice == '9':
            tracker.upload_to_github()
        
        elif choice == '10':
            tracker.clear_all_data()
        
        elif choice == '11':
            tracker.logout()
        
        elif choice == '0':
            print("👋 感謝使用！")
            break
        
        else:
            print("❌ 無效的選項，請重新選擇！")

if __name__ == "__main__":
    # 檢查必要的套件
    try:
        import matplotlib.pyplot as plt
        import pandas as pd
        import requests
    except ImportError as e:
        print(f"❌ 缺少必要套件：{e}")
        print("請安裝以下套件：")
        print("pip install matplotlib pandas requests")
        exit(1)
    
    main()