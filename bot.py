from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
import requests
import time
import json
import os
import random

# 🔧 Cấu hình Chrome chạy ngầm
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")  # Chạy không giao diện
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Tránh bị phát hiện là bot
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option("useAutomationExtension", False)

# Tự động tải ChromeDriver
service = Service()

# 🏷 Cấu hình Cookie & Webhook
COOKIE_FILE = "cookies.txt"
WEBHOOK_URL = "https://hooks.zapier.com/hooks/catch/21914696/2ldbgyz/" 
MAX_RETRIES = 5  # Giới hạn số lần thử lại nếu lỗi

def load_cookies(driver):
    """📌 Tải cookie từ file vào trình duyệt"""
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, 'r') as file:
            cookies = json.load(file)
        for cookie in cookies:
            driver.add_cookie(cookie)
        print(f"✅ Cookie đã được tải từ {COOKIE_FILE}")

def save_cookies(driver):
    """📌 Lưu cookie mới vào file"""
    cookies = driver.get_cookies()
    with open(COOKIE_FILE, "w") as file:
        json.dump(cookies, file)
    print(f"✅ Đã lưu cookie vào {COOKIE_FILE}")

def run_bot():
    """🏃‍♂️ Chạy bot"""
    retries = 0  # Đếm số lần thử lại

    while retries < MAX_RETRIES:
        driver = None
        try:
            driver = webdriver.Chrome(service=service, options=chrome_options)
            print("🌍 Mở trang web...")
            driver.get("https://new8838.net/")
            time.sleep(3)

            # 🔄 Tải cookie và làm mới trang
            load_cookies(driver)
            driver.refresh()
            time.sleep(3)

            # 📌 Kiểm tra đăng nhập
            if "Login" in driver.current_url:
                print("⚠️ Cookie không hợp lệ. Cần đăng nhập thủ công!")
                input("👉 Hãy đăng nhập vào tài khoản, sau đó nhấn Enter để tiếp tục...")
                save_cookies(driver)

            print("✅ Đã đăng nhập! Tiếp tục nạp tiền...")

            # 🔄 Chuyển đến trang Deposit
            driver.get("https://new8838.net/Deposit")
            time.sleep(3)

            # 🏦 Chọn gói "Nạp Nhanh 04"
            print("📌 Chọn gói nạp: Nạp Nhanh 04...")
            package_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//li[.//h3[contains(text(), 'Nạp Nhanh 04')]]"))
            )
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(random.uniform(1, 2))
            ActionChains(driver).move_to_element(package_element).click().perform()
            time.sleep(2)

            # 💰 Nhập số tiền ngẫu nhiên từ 50 đến 30,000
            random_amount = random.randint(50, 30000)
            print(f"💰 Nhập số tiền {random_amount:,}...")
            amount_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Vui lòng nhập số tiền']"))
            )
            amount_input.clear()
            amount_input.send_keys(str(random_amount))
            time.sleep(1)

            # 💳 Nhấn nút "Thanh toán ngay bây giờ"
            print("💳 Nhấn nút Thanh toán ngay bây giờ...")
            submit_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Thanh toán ngay bây giờ')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView();", submit_button)
            time.sleep(random.uniform(1.5, 2.5))
            ActionChains(driver).move_to_element(submit_button).click().perform()
            print("✅ Đã nhấn nút Thanh toán thành công.")
            time.sleep(3)

            # 🔄 Chuyển sang tab mới
            WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
            original_window = driver.current_window_handle
            for window_handle in driver.window_handles:
                if window_handle != original_window:
                    driver.switch_to.window(window_handle)
                    break
            print("✅ Đã chuyển sang tab mới.")

            # 📋 Lấy thông tin tài khoản ngân hàng
            print("📋 Lấy thông tin tài khoản ngân hàng...")
            try:
                ho_ten = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Người nhận tiền:')]/following-sibling::div/span"))
                ).text
                stk = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Số tài khoản ngân hàng:')]/following-sibling::div/span"))
                ).text
                ten_ngan_hang = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Tên ngân hàng:')]/following-sibling::div/span"))
                ).text

                print(f"✅ Họ tên: {ho_ten}, STK: {stk}, Ngân hàng: {ten_ngan_hang}")

                # 🚀 Gửi thông tin đến Zapier
                print("🚀 Gửi dữ liệu đến Zapier...")
                data = {"ho_ten": ho_ten, "stk": stk, "ten_ngan_hang": ten_ngan_hang, "goi_nap": "Nạp Nhanh 04"}
                response = requests.post(WEBHOOK_URL, json=data)
                print(f"📤 Kết quả gửi dữ liệu: {response.status_code}")

            except Exception as e:
                print(f"❌ Lỗi lấy thông tin ngân hàng: {e}")
                raise Exception("Không thể lấy thông tin tài khoản ngân hàng!")

            break  # ✅ Nếu chạy xong không lỗi, thoát khỏi vòng lặp

        except Exception as e:
            retries += 1
            print(f"❌ Lỗi (thử lần {retries}/{MAX_RETRIES}): {e}")

        finally:
            if driver:
                driver.quit()
            time.sleep(3)  # ⏳ Đợi trước khi thử lại

    print("🔄 Bot dừng do hết số lần thử.")

# 🔄 Chạy bot khi script khởi động
if __name__ == "__main__":
    run_bot()
