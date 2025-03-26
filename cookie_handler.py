import json
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class CookieHandler:
    def __init__(self):
        self.mongo_uri = os.getenv('MONGO_URI')
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client['account']
        self.collection = self.db['new88']
        self.COOKIE_ENV_VAR = "COOKIES_JSON"

    def mark_account_locked(self, account_id):
        """Đánh dấu tài khoản bị khóa trong MongoDB theo account_id"""
        try:
            result = self.collection.update_one(
                {"_id": account_id},
                {"$set": {
                    "is_locked": True,
                    "updated_at": datetime.now()
                }},
                upsert=True
            )
            print(f"✅ Đã đánh dấu tài khoản bị khóa trong DB")
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            print(f"❌ Lỗi khi cập nhật trạng thái khóa tài khoản: {e}")
            return False

    def get_cookies(self, account_id):
        """Lấy và kết hợp cookies từ env và MongoDB theo account_id"""
        try:
            cookies_json = os.getenv(self.COOKIE_ENV_VAR)
            if not cookies_json:
                return None
            cookies = json.loads(cookies_json)

            account_data = self.collection.find_one({
                "_id": account_id,
                "is_locked": {"$ne": True},
                "token_expired": {"$ne": True}
               
            })

            if account_data and '_pat' in account_data and '_prt' in account_data:
                for cookie in cookies:
                    if cookie['name'] == '_pat':
                        cookie['value'] = account_data['_pat']
                    elif cookie['name'] == '_prt':
                        cookie['value'] = account_data['_prt']
            return cookies
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            return None
        except Exception as e:
            print(f"❌ Error in get_cookies: {e}")
            return None

    def load_cookies_to_driver(self, driver, account_id):
        """Load cookies vào driver, bỏ qua nếu tài khoản hết token theo account_id"""
        try:
            cookies = self.get_cookies(account_id)
            if not cookies:
                print("❌ Không có cookies để load")
                return False

            if self.is_account_expired(account_id):
                print(f"⚠️ Tài khoản đã hết token, không load cookies")
                return False

            for cookie in cookies:
                driver.add_cookie(cookie)
            print("✅ Đã load cookies thành công")
            return True
        except Exception as e:
            print(f"❌ Lỗi khi load cookies: {e}")
            return False

    def update_mongo_cookies(self, account_id, pat, prt):
        """Cập nhật _pat và _prt vào MongoDB và reset trạng thái token_expired theo account_id"""
        try:
            result = self.collection.update_one(
                {"_id": account_id},
                {
                    "$set": {
                        "_pat": pat,
                        "_prt": prt,
                        "updated_at": datetime.now()
                    },
                    "$unset": {"token_expired": ""}
                },
                upsert=True
            )
            print(f"✅ Đã cập nhật token")
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            print(f"❌ Lỗi khi cập nhật token: {e}")
            return False

    def mark_account_expired(self, account_id):
        """Đánh dấu tài khoản hết token trong MongoDB theo account_id"""
        try:
            result = self.collection.update_one(
                {"_id": account_id},
                {"$set": {"token_expired": True, "updated_at": datetime.now()}},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            print(f"❌ Lỗi khi cập nhật trạng thái token_expired: {e}")
            return False

    def is_account_expired(self, account_id):
        """Kiểm tra xem tài khoản có bị hết token không theo account_id"""
        try:
            account = self.collection.find_one({"_id": account_id})
            return account.get("token_expired", False) if account else False
        except Exception as e:
            print(f"❌ Lỗi khi kiểm tra trạng thái tài khoản: {e}")
            return False

    def reset_account_status(self, account_id):
        """Xóa trạng thái hết token sau khi đăng nhập lại theo account_id"""
        try:
            result = self.collection.update_one(
                {"_id": account_id},
                {"$unset": {"token_expired": ""}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"❌ Lỗi khi reset trạng thái tài khoản: {e}")
            return False

    def get_account_id(self):
        """Lấy account_id từ tài khoản chưa hết token và chưa bị khóa"""
        try:
            account_data = self.collection.find_one({
                "is_locked": {"$ne": True},
                "token_expired": {"$ne": True}
            })
            if not account_data:
                print("⚠️ Không tìm thấy tài khoản nào còn token hợp lệ và chưa bị khóa")
                return None
            return account_data.get("_id")
        except Exception as e:
            print(f"❌ Lỗi khi lấy account_id từ MongoDB: {e}")
            return None

    def get_account_info(self, account_id):

        try:
            account_data = self.collection.find_one({"_id": account_id})
            if account_data:
                return account_data  # Trả về toàn bộ thông tin tài khoản
            else:
                print("⚠️ Không tìm thấy tài khoản với account_id:", account_id)
                return None
        except Exception as e:
            print(f"❌ Lỗi khi lấy thông tin tài khoản: {e}")
            return None