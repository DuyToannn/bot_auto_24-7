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
from dotenv import load_dotenv

load_dotenv()

# Cấu hình
COOKIE_ENV_VAR = "COOKIES_JSON"  
WEBHOOK_URL = "https://hooks.zapier.com/hooks/catch/21914696/2ldbgyz/"
PACKAGE_NAME = "Nạp Nhanh 04"  

print(f"🔵 Bot cho {PACKAGE_NAME} đang khởi động...")

def load_cookies(driver):
    cookies_json = os.getenv(COOKIE_ENV_VAR)
    if cookies_json:
        try:
            cookies = json.loads(cookies_json)
            for cookie in cookies:
                driver.add_cookie(cookie)
            print("✅ Cookie đã được tải thành công")
        except json.JSONDecodeError as e:
            print(f"❌ Lỗi giải mã JSON: {e}")
    else:
        print("⚠️ Không tìm thấy cookie. Sẽ yêu cầu đăng nhập.")

def save_cookies(driver, cookie_file="cookies.txt"):
    cookies = driver.get_cookies()
    with open(cookie_file, "w") as file:
        json.dump(cookies, file)
    print(f"✅ Đã lưu cookie vào {cookie_file}")

def run_bot():
    # Cấu hình Chrome Options
    chrome_options = Options()
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # Khởi tạo ChromeDriver
    driver = webdriver.Chrome(options=chrome_options)
    print("✅ ChromeDriver đã khởi động")
    
    try:
        # Mở trang gốc
        driver.get(os.getenv('BASE_URL'))
        time.sleep(3)

        # Tải cookie
        load_cookies(driver)
        driver.refresh()
        time.sleep(3)

        # Kiểm tra đăng nhập
        if "Login" in driver.current_url:
            print("⚠️ Cookie không hợp lệ. Cần đăng nhập thủ công!")
            input("👉 Hãy đăng nhập vào tài khoản, sau đó nhấn Enter để tiếp tục...")
            save_cookies(driver)

        print("✅ Đã đăng nhập! Tiếp tục nạp tiền...")

        # Mở trang nạp tiền
        driver.get(os.getenv('DEPOSIT_URL'))
        time.sleep(3)

        # Đóng popup (nếu có)
        try:
            close_popup = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[@class='_9PbX_LFgnXvcTnC_3cq6B']//span[@translate='Common_Closed']"))
            )
            close_popup.click()
        except Exception:
            pass

        # Chọn gói nạp
        print(f"📌 Chọn gói nạp: {PACKAGE_NAME}")
        package_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, f"//li[.//h3[contains(text(), '{PACKAGE_NAME}')]]"))
        )
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(random.uniform(1, 2))
        ActionChains(driver).move_to_element(package_element).click().perform()
        time.sleep(2)

        # Nhập số tiền ngẫu nhiên
        random_amount = random.randint(50, 30000)
        print(f"💰 Nhập số tiền {random_amount:,}")
        amount_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[@ng-show='!$ctrl.form.payment.amountLock']//input[@placeholder='Vui lòng nhập số tiền']"))
        )
        amount_input.clear()
        amount_input.send_keys(str(random_amount))
        time.sleep(1)

        # Nhấn nút thanh toán
        try:
            print("💳 Nhấn nút Thanh toán")
            submit_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Thanh toán ngay bây giờ')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView();", submit_button)
            time.sleep(random.uniform(1.5, 2.5))
            ActionChains(driver).move_to_element(submit_button).click().perform()
            time.sleep(3)
        except Exception as e:
            print(f"❌ Lỗi khi nhấn nút Thanh toán: {e}")
            raise

        # Chuyển sang tab mới
        WebDriverWait(driver, 60).until(EC.number_of_windows_to_be(2))
        original_window = driver.current_window_handle
        for window_handle in driver.window_handles:
            if window_handle != original_window:
                driver.switch_to.window(window_handle)
                break

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

        except Exception as e:
            print(f"❌ Lỗi lấy thông tin: {e}")
            raise Exception("Không thể lấy thông tin ngân hàng!")

        # Gửi dữ liệu đến Zapier
        print("🚀 Gửi dữ liệu đến Zapier")
        data = {"ho_ten": ho_ten, "stk": stk, "ten_ngan_hang": ten_ngan_hang, "goi_nap": PACKAGE_NAME}
        response = requests.post(WEBHOOK_URL, json=data)
        if response.status_code == 200:
            print("✅ Gửi dữ liệu thành công")
        else:
            print(f"❌ Gửi dữ liệu thất bại: {response.status_code}")

    except Exception as e:
        print(f"❌ Lỗi: {e}")

    finally:
        driver.quit()

if __name__ == "__main__":
    while True:
        try:
            run_bot()
            print("🔄 Chờ 5 giây trước khi chạy lại...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n⛔ Đã dừng chương trình")
            break
        except Exception as e:
            print(f"❌ Lỗi không mong muốn: {e}")
            time.sleep(5)