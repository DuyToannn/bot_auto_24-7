from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import requests
import time
import json
import os
import random
import base64
from login_handler import random_sleep, handle_login


import re
import io
from dotenv import load_dotenv
import pymongo
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import pytesseract
from PIL import Image
import undetected_chromedriver as uc
if os.getenv("RAILWAY_ENVIRONMENT"):
    pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
else:
    # Đặt đường dẫn local (Windows)
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Load environment variables
load_dotenv()

# MongoDB configuration with error handling
mongo_uri = os.getenv('MONGO_URI')
db = None
collection = None
mongo_client = None

try:
    mongo_client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    mongo_client.admin.command('ping')  # Verify connection
    db = mongo_client['bot_database']
    collection = db['bank_info']
    print("✅ MongoDB connection successful")
except (ConnectionFailure, ServerSelectionTimeoutError) as e:
    print(f"❌ MongoDB connection error: {e}")
    print("⚠️ Bot will continue without database functionality")


# Constants
PACKAGE_NAME = "Nạp Nhanh 04"
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
print(f"🔵 Bot cho {PACKAGE_NAME} đang khởi động...")

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Thiếu cấu hình Telegram Bot. Không thể gửi tin nhắn.")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ Đã gửi tin nhắn đến Telegram")
            return True
        else:
            print(f"❌ Gửi tin nhắn Telegram thất bại: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Lỗi khi gửi tin nhắn Telegram: {e}")
        return False

def save_to_database(bank_info):
    if collection is None:
        print("⚠️ Không thể lưu vào database - Kết nối MongoDB không khả dụng")
        return False
    
    try:
        collection.insert_one(bank_info)
        print("✅ Dữ liệu đã được lưu vào MongoDB")
        return True
    except Exception as e:
        print(f"❌ Lỗi khi lưu vào database: {e}")
        return False

def check_existing_record(stk):
    if collection is None:
        print("⚠️ Không thể kiểm tra database - Kết nối MongoDB không khả dụng")
        return False
    
    try:
        existing_record = collection.find_one({"stk": stk})
        return existing_record is not None
    except Exception as e:
        print(f"❌ Lỗi khi kiểm tra database: {e}")
        return False

def get_captcha_text(captcha_base64):
    try:
        image_data = base64.b64decode(captcha_base64.split(',')[1])
        image = Image.open(io.BytesIO(image_data))
        captcha_code = pytesseract.image_to_string(image, config="--psm 8 -c tessedit_char_whitelist=0123456789").strip()
        captcha_code = re.sub(r'\D', '', captcha_code)  # Chỉ lấy số

        if len(captcha_code) == 4:
            print(f"✅ Mã xác minh nhận diện: {captcha_code}")
            return captcha_code
        else:
            print(f"⚠️ Mã OCR sai ({captcha_code}), thử lại...")
            return None
    except Exception as e:
        print(f"❌ Lỗi nhận diện mã xác minh: {e}")
        return None

def run_bot():
    try:
        # Sử dụng undetected_chromedriver thay vì selenium webdriver thông thường
        options = uc.ChromeOptions()
        # options.add_argument("--no-sandbox")
        # options.add_argument("--disable-blink-features=AutomationControlled")
        # options.add_argument("--disable-extensions")
        # options.add_argument("--disable-gpu")
        # options.add_argument("--disable-dev-shm-usage")
        # options.add_argument("--enable-javascript")
        # options.add_argument("--window-size=1920,1080")
        # options.add_argument("--disable-dev-tools")  # Vô hiệu hóa dev tools
        
        # Thêm các tham số để giả lập người dùng thực
        # options.add_experimental_option("excludeSwitches", ["enable-automation"])
        # options.add_experimental_option("useAutomationExtension", False)
        
        # Khởi tạo trình duyệt với undetected_chromedriver
        driver = uc.Chrome(options=options)
        
        # Thêm JavaScript để giả lập trình duyệt thật
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("✅ ChromeDriver đã khởi động với chế độ không phát hiện")
        
        # Mở trang web với độ trễ ngẫu nhiên
        driver.get(os.getenv("BASE_URL"))
        random_sleep(2, 4)
        
        # Kiểm tra và đóng popup nếu có
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//span[@ng-click='$ctrl.ok()'][@translate='Common_Closed']"))
            ).click()
            random_sleep(0.5, 1.5)
        except Exception:
            pass

        # Kiểm tra xem có cần đăng nhập không
        if "Login" in driver.current_url:
            login_success = handle_login(driver, get_captcha_text)
            if not login_success:
                return

        # Đã đăng nhập hoặc không cần đăng nhập, chuyển đến trang nạp tiền
        print("🔄 Chuyển đến trang nạp tiền")
        driver.get(os.getenv('DEPOSIT_URL'))
        random_sleep(2, 4)

        # Kiểm tra và đóng popup nếu có
        try:
            popup_close = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//span[@translate='Common_Closed']"))
            )
            driver.execute_script("arguments[0].click();", popup_close)
            random_sleep(0.5, 1.5)
        except Exception:
            pass

        package_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, f"//li[.//h3[contains(text(), '{PACKAGE_NAME}')]]"))
        )
        # Di chuyển chuột đến phần tử trước khi click
        ActionChains(driver).move_to_element(package_element).perform()
        random_sleep(0.5, 1)
        driver.execute_script("window.scrollBy(0, 500);")
        random_sleep(0.5, 1)
        # Sử dụng JavaScript để click
        driver.execute_script("arguments[0].click();", package_element)
        random_sleep(1, 2)

        random_amount = random.randint(50, 30000)
        print(f"💰 Nhập số tiền {random_amount:,}")
        amount_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Vui lòng nhập số tiền']"))
        )
        amount_input.click()
        random_sleep(0.3, 0.8)
        amount_input.clear()
        random_sleep(0.3, 0.8)
        
        # Nhập từng ký tự số tiền một với độ trễ ngẫu nhiên
        for char in str(random_amount):
            amount_input.send_keys(char)
            random_sleep(0.05, 0.15)
        
        random_sleep(0.5, 1.5)

        pay_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Thanh toán ngay bây giờ')]"))
        )
        # Di chuyển chuột đến nút trước khi click
        ActionChains(driver).move_to_element(pay_button).perform()
        random_sleep(0.5, 1)
        # Sử dụng JavaScript để click
        driver.execute_script("arguments[0].click();", pay_button)
        random_sleep(2, 4)

        # Chuyển sang tab mới
        WebDriverWait(driver, 60).until(EC.number_of_windows_to_be(2))
        original_window = driver.current_window_handle
        for window_handle in driver.window_handles:
            if window_handle != original_window:
                driver.switch_to.window(window_handle)
                break
        
        random_sleep(1, 3)

        # Lấy thông tin ngân hàng
        print("📋 Lấy thông tin tài khoản ngân hàng")
        try:
            ho_ten = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Người nhận tiền:')]/following-sibling::div[@class='text']/span[@class='value high-light']"))
            ).text
            stk = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Số tài khoản ngân hàng:')]/following-sibling::div[@class='text']/span[@class='value high-light']"))
            ).text
            ten_ngan_hang = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Tên ngân hàng:')]/following-sibling::div[@class='text']/span[@class='value']"))
            ).text

            if not ho_ten or not stk or not ten_ngan_hang:
                raise Exception("Thông tin tài khoản ngân hàng không đầy đủ!")
            print(f"✅ Đã lấy thông tin: {ho_ten}, {stk}, {ten_ngan_hang}")

            # Kiểm tra xem STK đã tồn tại trong database chưa
            if check_existing_record(stk):
                print(f"⚠️ STK {stk} đã tồn tại trong database")
            else:
                bank_info = {
                    "ho_ten": ho_ten,
                    "stk": stk,
                    "ten_ngan_hang": ten_ngan_hang,
                    "goi_nap": PACKAGE_NAME,
                    "timestamp": time.time()
                }
                save_to_database(bank_info)
                
                # Gửi thông báo qua Telegram
                message = f"""
🔔 <b>THÔNG TIN TÀI KHOẢN MỚI</b>

👤 <b>Họ Tên:</b> {ho_ten}
💳 <b>Số tài khoản:</b> <code>{stk}</code>
🏦 <b>Ngân hàng:</b> {ten_ngan_hang}
📦 <b>Gói nạp:</b> {PACKAGE_NAME}
                """
                send_telegram_message(message)

        except Exception as e:
            print(f"❌ Lỗi lấy thông tin: {e}")
            raise Exception("Không thể lấy thông tin ngân hàng!")

    except Exception as e:
        print(f"❌ Lỗi: {e}")

    finally:
        driver.quit()

if __name__ == "__main__":
    while True:
        try:
            run_bot()
            wait_time = random.uniform(4, 6)
            print(f"🔄 Chờ {wait_time:.1f} giây trước khi chạy lại...")
            time.sleep(wait_time)
        except KeyboardInterrupt:
            print("\n⛔ Đã dừng chương trình")
            break
        except Exception as e:
            print(f"❌ Lỗi không mong muốn: {e}")
            time.sleep(5)
