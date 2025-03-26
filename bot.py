from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
import requests
import time
import json
import os
import random
import sys
import signal
import uuid
from dotenv import load_dotenv
import pymongo
from cookie_handler import CookieHandler

load_dotenv()
mongo_uri = os.getenv('MONGO_URI')
client = pymongo.MongoClient(mongo_uri)
db = client['bot_database']
COOKIE_ENV_VAR = "COOKIES_JSON"
WEBHOOK_URL = "https://hooks.zapier.com/hooks/catch/21914696/2ldbgyz/"
PACKAGE_NAME = "Nạp Nhanh 04"
collection = db['bank_info']
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_IDS = [chat_id.strip() for chat_id in os.getenv('TELEGRAM_CHAT_IDS', '').split(',')]
print(f"🔵 Bot cho {PACKAGE_NAME} đang khởi động...")

def random_sleep(min_sec, max_sec):
    """Sleep for a random amount of time between min_sec and max_sec"""
    time.sleep(random.uniform(min_sec, max_sec))

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        print("⚠️ Thiếu cấu hình Telegram Bot. Không thể gửi tin nhắn.")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    success = True
    
    for chat_id in TELEGRAM_CHAT_IDS:
        try:
            payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
            response = requests.post(url, json=payload)
            if response.status_code != 200:
                success = False
                print(f"❌ Lỗi gửi tin nhắn đến chat {chat_id}: {response.text}")
        except Exception as e:
            success = False
            print(f"❌ Lỗi khi gửi tin nhắn Telegram đến chat {chat_id}: {e}")
    
    return success

def setup_driver():
    """Setup ChromeDriver with anti-detection options"""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")   
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-webgl")
    chrome_options.add_argument("--enable-unsafe-swiftshader") 
    chrome_options.add_argument("--disable-software-rasterizer")  
    chrome_options.add_argument("--log-level=3")
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })
    return driver

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

def handle_token_expired(cookie_handler, account_id):
    """Xử lý khi token hết hạn"""
    account_info = cookie_handler.get_account_info(account_id)
    account_name = account_info.get('_account', 'Unknown') if account_info else 'Unknown'
    
    update_result = cookie_handler.mark_account_expired(account_id)
    if update_result:
        print(f"✅ Đã đánh dấu tài khoản {account_name} hết token trong DB")
    message = f"""
🔔 <b>TÀI KHOẢN ĐÃ ĐĂNG XUẤT: {account_name}</b>
    """
    send_telegram_message(message)
    raise Exception("Tài khoản hết token, dừng bot để xử lý thủ công.")

def run_bot():
    driver = None
    try:
        # Initialize driver
        driver = setup_driver()
        print("✅ ChromeDriver đã khởi động thành công!")

        cookie_handler = CookieHandler()
        # Lấy account_id
        account_id = cookie_handler.get_account_id()
        if not account_id:
            raise Exception("Không thể xác định account_id từ MongoDB")


        account_info = cookie_handler.get_account_info(account_id)
        account_name = account_info.get('_account', 'Unknown') if account_info else 'Unknown'
        print(f"🔑 Sử dụng tài khoản với ID: {account_id}, Tên tài khoản: {account_name}")

        # Navigate to base URL
        base_url = os.getenv("BASE_URL")
        if not base_url:
            raise Exception("BASE_URL not configured in environment variables")
        
        driver.get(base_url)
        random_sleep(2, 4)

        # Load cookies and refresh
        if not cookie_handler.load_cookies_to_driver(driver, account_id):
            raise Exception("Không thể load cookies, kiểm tra tài khoản")
        driver.refresh()
        time.sleep(3)

        # Kiểm tra đăng nhập
        if "Login" in driver.current_url:
            print("⚠️ Cookie không hợp lệ. Cần đăng nhập thủ công!")
        print("✅ Đã đăng nhập! Tiếp tục nạp tiền...")

        # Handle initial popup
        try:
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//span[@ng-click='$ctrl.ok()'][@translate='Common_Closed']"))
            ).click()
            random_sleep(0.5, 1.5)
        except:
            pass

        # Navigate to deposit page
        deposit_url = os.getenv('DEPOSIT_URL')
        if not deposit_url:
            raise Exception("DEPOSIT_URL not configured in environment variables")
            
        driver.get(deposit_url)
        random_sleep(2, 4)

        max_wait_time = 10  
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            current_url = driver.current_url
            if current_url == base_url:
                handle_token_expired(cookie_handler, account_id)
            elif deposit_url in current_url:
                break
            time.sleep(1)
        else:
            handle_token_expired(cookie_handler, account_id)

        # Check if wallet is locked
        try:
            wallet_locked = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[@ng-if='$ctrl.isLock']"))
            )
            if wallet_locked.is_displayed():
                cookie_handler.mark_account_locked(account_id)
                message = f"""
🔒 <b>TÀI KHOẢN BỊ ĐÓNG BĂNG : {account_name}</b>
"""
                send_telegram_message(message)
                print("🔒 Tài khoản bị đóng băng, đóng Chrome và chạy lại...")
                if driver:
                    driver.quit()
                return  # Thoát hàm ngay để chạy lại từ đầu
        except:
            pass

        # Handle deposit page popup
        try:
            popup_close = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//span[@translate='Common_Closed']"))
            )
            driver.execute_script("arguments[0].click();", popup_close)
            random_sleep(0.5, 1.5)
        except:
            pass

        # Select package
        try:
            package_element = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, f"//li[.//h3[contains(text(), '{PACKAGE_NAME}')]]"))
            )
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(random.uniform(1, 2))
            ActionChains(driver).move_to_element(package_element).pause(0.5).click().perform()
            time.sleep(random.uniform(1, 2))
            print("✅ Đã chọn gói thành công")
        except Exception as e:
            if "no such element" in str(e).lower():
                send_telegram_message(f"❌ Không có gói {PACKAGE_NAME}")
            else:
                send_telegram_message(f"❌ Không có gói {PACKAGE_NAME}")
            return
        except Exception as e:
            if "no such element" in str(e).lower():
                send_telegram_message(message)
            else:
                send_telegram_message(f"❌ Không thể chọn gói {PACKAGE_NAME}: {e}")
            if "đóng băng" not in str(e).lower():
                try:
                    logout_button = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//button[contains(@class, '_1TEhFF5lWfbkg-wGKQap0W')]//span[@translate='Shared_Logout']"))
                    )
                except:
                    pass

        # Enter amount
        random_amount = random.randint(50, 30000)
        print(f"💰 Nhập số tiền {random_amount:,}")
        amount_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Vui lòng nhập số tiền']"))
        )
        amount_input.click()
        amount_input.clear()
        for char in str(random_amount):
            amount_input.send_keys(char)
            random_sleep(0.05, 0.15)

        # Click pay button
        pay_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Thanh toán ngay bây giờ')]"))
        )
        ActionChains(driver).move_to_element(pay_button).pause(0.5).click().perform()
        random_sleep(2, 4)

        # Switch to new window
        WebDriverWait(driver, 60).until(EC.number_of_windows_to_be(2))
        original_window = driver.current_window_handle
        for window_handle in driver.window_handles:
            if window_handle != original_window:
                driver.switch_to.window(window_handle)
                break

        # Get bank info
        bank_info = {}
        for key, xpath in {
            'ho_ten': "//span[contains(text(), 'Người nhận tiền:')]/following-sibling::div[@class='text']/span[@class='value high-light']",
            'stk': "//span[contains(text(), 'Số tài khoản ngân hàng:')]/following-sibling::div[@class='text']/span[@class='value high-light']",
            'ten_ngan_hang': "//span[contains(text(), 'Tên ngân hàng:')]/following-sibling::div[@class='text']/span[@class='value']"
        }.items():
            bank_info[key] = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            ).text.strip()

        if not all(bank_info.values()):
            raise Exception("Missing bank information!")

        # Process bank info
        existing_record = collection.find_one({"stk": bank_info['stk']})
        if existing_record:
            print(f"⚠️ STK {bank_info['stk']} đã tồn tại trong database")
        else:
            bank_data = {
                **bank_info,
                "goi_nap": PACKAGE_NAME,
                "timestamp": time.time()
            }
            collection.insert_one(bank_data)
            print("✅ Dữ liệu đã được lưu vào MongoDB")

            message = f"""
🔔 <b>THÔNG TIN TÀI KHOẢN MỚI</b>
👤 <b>Họ Tên:</b> {bank_info['ho_ten']}
💳 <b>Số tài khoản:</b> <code>{bank_info['stk']}</code>
🏦 <b>Ngân hàng:</b> {bank_info['ten_ngan_hang']}
📦 <b>Gói nạp:</b> {PACKAGE_NAME}
            """
            send_telegram_message(message)

    except Exception as e:
        print(f"❌ Lỗi: {e}")
        raise
    finally:
        if driver:
            driver.quit()
            print("✅ Đã đóng ChromeDriver")

if __name__ == "__main__":
    while True:
        try:
            run_bot()
            wait_time = random.uniform(4, 6)
            print(f"🔄 Chờ {wait_time:.1f} giây trước khi chạy lại...")
            time.sleep(wait_time)
        except KeyboardInterrupt:
            print("\n⛔ Đã dừng chương trình")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Lỗi không mong muốn: {e}")
            time.sleep(5)