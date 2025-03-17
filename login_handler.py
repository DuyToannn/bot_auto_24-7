from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import random
import os
import time

def random_sleep(min_time=1, max_time=3):
    time.sleep(random.uniform(min_time, max_time))

def handle_login(driver, get_captcha_text):
    login_attempt_count = 0
    max_login_attempts = 3
    
    while login_attempt_count < max_login_attempts:
        login_attempt_count += 1
        
        print("⚠️ Cần đăng nhập!")
        
        # Thêm độ trễ trước khi nhập thông tin đăng nhập
        random_sleep(1, 2)
        
        # Chọn ngẫu nhiên một tài khoản từ danh sách
        account_number = random.randint(1, 5)
        account_key = f"USER_ACCOUNT{'' if account_number == 1 else account_number}"
        password_key = f"USER_PASSWORD{'' if account_number == 1 else account_number}"
        
        selected_account = os.getenv(account_key)
        selected_password = os.getenv(password_key)
        
        print(f"🔑 Đang sử dụng tài khoản: {selected_account}")
        
        # Tìm và nhập tên đăng nhập với hành vi giống người dùng
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@ng-model='$ctrl.user.account.value']"))
        )
        username_field.click()
        random_sleep(0.3, 0.8)
        
        # Nhập từng ký tự một với độ trễ ngẫu nhiên
        for char in selected_account:
            username_field.send_keys(char)
            random_sleep(0.05, 0.15)
        
        random_sleep(0.5, 1)
        
        # Tìm và nhập mật khẩu với hành vi giống người dùng
        password_field = driver.find_element(By.XPATH, "//input[@ng-model='$ctrl.user.password.value']")
        password_field.click()
        random_sleep(0.3, 0.8)
        
        # Nhập từng ký tự một với độ trễ ngẫu nhiên
        for char in selected_password:
            password_field.send_keys(char)
            random_sleep(0.05, 0.15)
        
        login_success = False
        max_attempts = 5
        attempt = 0
        
        while not login_success and attempt < max_attempts:
            attempt += 1
            print(f"Lần thử đăng nhập thứ {attempt}")
            
            captcha_input = driver.find_element(By.XPATH, "//input[@ng-model='$ctrl.code']")
            captcha_input.click()
            random_sleep(1, 2)

            captcha_image = driver.find_element(By.XPATH, "//gupw-captcha-login-box//img")
            captcha_base64 = captcha_image.get_attribute("src")
            
            captcha_code = get_captcha_text(captcha_base64)
            if not captcha_code:
                print("⚠️ Không thể nhận diện mã xác minh, thử lại...")
                # Làm mới captcha
                try:
                    refresh_button = driver.find_element(By.XPATH, "//i[contains(@class, 'refresh')]")
                    refresh_button.click()
                    random_sleep(1, 2)
                except:
                    pass
                continue
                
            captcha_input.clear()
            random_sleep(0.3, 0.7)
            
            # Nhập từng ký tự captcha một với độ trễ ngẫu nhiên
            for char in captcha_code:
                captcha_input.send_keys(char)
                random_sleep(0.1, 0.3)
            
            random_sleep(0.5, 1.5)
            login_button = driver.find_element(By.XPATH, "//button[contains(@ng-class, 'login-btn')]")
            # Click bằng chuột thay vì JavaScript
            ActionChains(driver).move_to_element(login_button).click().perform()
            random_sleep(2, 4)

            # Kiểm tra thông báo lỗi
            try:
                error_dialog = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//gupw-dialog-alert"))
                )
                
                # Kiểm tra nếu là lỗi đăng nhập (không phải lỗi captcha)
                error_content = error_dialog.find_element(By.XPATH, ".//div[@class='modal-body']//div").text
                if "Lỗi đăng nhập" in error_content:
                    print("⚠️ Lỗi đăng nhập, thử lại từ đầu...")
                    # Đóng thông báo lỗi
                    close_button = error_dialog.find_element(By.XPATH, ".//button[contains(@ng-click, '$ctrl.ok()')]")
                    driver.execute_script("arguments[0].click();", close_button)
                    random_sleep(1, 2)
                    # Thoát khỏi vòng lặp hiện tại để quay lại bước đăng nhập từ đầu
                    break
                else:
                    # Nếu là lỗi captcha
                    print("⚠️ Mã xác minh không đúng, thử lại...")
                    # Sử dụng JavaScript để click vào nút đóng thông báo lỗi
                    close_button = error_dialog.find_element(By.XPATH, ".//button[contains(@ng-click, '$ctrl.ok()')]")
                    driver.execute_script("arguments[0].click();", close_button)
                    random_sleep(1, 2)
                    continue
            except:
                # Không có thông báo lỗi = đăng nhập thành công
                login_success = True
                print("✅ Đăng nhập thành công!")
                return True

        # Nếu đăng nhập thành công, thoát khỏi vòng lặp ngoài
        if login_success:
            break
    
    print("❌ Đã thử đăng nhập nhiều lần nhưng không thành công")
    return False