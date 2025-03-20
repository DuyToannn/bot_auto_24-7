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
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })
    return driver

def load_cookies(driver):
    """Load cookies from environment variable"""
    cookies_json = os.getenv(COOKIE_ENV_VAR)
    if not cookies_json:
        print(f"⚠️ Không tìm thấy biến môi trường {COOKIE_ENV_VAR}")
        return False

    try:
        cookies = json.loads(cookies_json)
        for cookie in cookies:
            driver.add_cookie(cookie)
        print(f"✅ Cookie đã được tải từ biến môi trường {COOKIE_ENV_VAR}")
        return True
    except json.JSONDecodeError as e:
        print(f"❌ Lỗi giải mã JSON từ {COOKIE_ENV_VAR}: {e}")
        return False

def run_bot():
    driver = None
    try:
        # Initialize driver
        driver = setup_driver()
        print("✅ ChromeDriver đã khởi động thành công!")

        # Navigate to base URL
        base_url = os.getenv("BASE_URL")
        if not base_url:
            raise Exception("BASE_URL not configured in environment variables")
        
        driver.get(base_url)
        random_sleep(2, 4)

        # Load cookies and refresh
        if load_cookies(driver):
            driver.refresh()
            random_sleep(2, 4)

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
        package_element = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, f"//li[.//h3[contains(text(), '{PACKAGE_NAME}')]]"))
        )
        ActionChains(driver).move_to_element(package_element).pause(0.5).click().perform()
        random_sleep(1, 2)

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
