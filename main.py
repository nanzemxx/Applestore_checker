from selenium import webdriver
from datetime import datetime
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import os
import time
import smtplib
from email.header import Header
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
import logging
import json

# 设置日志记录
logging.basicConfig(filename='availability_checker.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def setup_driver():
    # 用户数据目录路径
    user_data_dir = "./profile"  # 替换为实际的路径
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)

    # 设置Edge选项
    edge_options = Options()
    edge_options.add_argument("--headless")  # 启用无头模式，如不需要请用#
    edge_options.use_chromium = True
    edge_options.add_argument(f"user-data-dir={user_data_dir}")
    edge_options.add_experimental_option('useAutomationExtension', False)


    # EdgeDriver路径
    driver_path = "msedgedriver"  # 替换为实际的msedgedriver路径
    service = Service(executable_path=driver_path)

    # 创建WebDriver实例
    driver = webdriver.Edge(service=service, options=edge_options)
    driver.implicitly_wait(5)
    return driver

def check_availability(driver):
    global taiguli_available, wanxiangcheng_available
    driver.set_window_size(988, 824)


    # 等待页面加载完成
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    driver.find_element(By.XPATH, "//button[normalize-space(text())='显示更多零售店' and @aria-label='Show more stores near the postcode you entered']").click()
    time.sleep(3)

    try:
        # 检查 "成都太古里" 是否可选
        taiguli_input = driver.find_element(By.XPATH, "//input[@name='store-locator-result' and @value='R580']")
        taiguli_available = taiguli_input.get_attribute("disabled") is None

        # 检查 "成都万象城" 是否可选
        wanxiangcheng_input = driver.find_element(By.XPATH, "//input[@name='store-locator-result' and @value='R502']")
        wanxiangcheng_available = wanxiangcheng_input.get_attribute("disabled") is None

        if taiguli_available or wanxiangcheng_available:
            driver.save_screenshot('screenshot.png')
            time.sleep(2)
        # 打印可选状态
        #print(1 if taiguli_available else 0)
        #print(1 if wanxiangcheng_available else 0)
    finally:
        driver.find_element(By.XPATH, "//button[span='确认你的零售店']").click()

def send_email():
    mail_host = "SMTP服务器"      
    mail_user = "你的用户名"                  
    mail_pass = "你的密码" 

    sender = "请填入你的邮箱地址"
    receivers = ["请填入收件人"]
    title  = "有货提醒"
    content  = "有货啦！"
    message = MIMEMultipart()
    message.attach(MIMEText(content, 'plain', 'utf-8'))
    
    with open('screenshot.png', 'rb') as file:
        img = MIMEImage(file.read(), name="screenshot.png")
        message.attach(img)
   
    

    message['From'] = "{}".format(sender)
    message['To'] = ",".join(receivers)
    message['Subject'] = title

    try:
        smtpObj = smtplib.SMTP_SSL(mail_host, 465)  # 启用SSL发信, 端口一般是465
        smtpObj.login(mail_user, mail_pass)  # 登录验证
        smtpObj.sendmail(sender, receivers, message.as_string())  # 发送
        print("Email sent successfully")
    except smtplib.SMTPException as e:
        print(f"Error: {e}")

# ------ 主要改动部分 ------

def main():
    global taiguli_available, wanxiangcheng_available
    check_count = 0
    while True:
        try:
            driver = setup_driver()
            driver.implicitly_wait(10)
            driver.get("https://www.apple.com.cn/shop/bag")
            with open('cookies.json', 'r') as file:
                cookies = json.load(file)
            # 添加cookie到浏览器
            for cookie in cookies:
                driver.add_cookie(cookie)

            taiguli_available = False
            wanxiangcheng_available = False

            while not (taiguli_available or wanxiangcheng_available):
                driver.refresh()
                check_availability(driver)
                check_count += 1 
                if taiguli_available or wanxiangcheng_available:
                    logging.info("Stores are available. Sending email...")
                    send_email()
                    time.sleep(20)  # 邮件发送后等待1分钟
                    driver.quit()  # 退出浏览器
                    return
                else:
                    logging.info("Both stores are unavailable. Checking again in 5 minutes.")
                    time.sleep(300)  # 等待5分钟

                if check_count >= 10:
                    logging.info("Restarting WebDriver after 10 checks.")
                    time.sleep(10)
                    driver.quit()  # 退出浏览器
                    check_count = 0  # 重置计数器
                    break 

            

        except Exception as e:
            time.sleep(10)
            logging.error(f"An error occurred: {e}")
            driver.quit()
            time.sleep(300)  # 发生错误后等待5分钟再试

if __name__ == "__main__":
    main()
