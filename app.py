import os
import time
from datetime import datetime
import logging
import schedule
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import requests
import threading
from flask import Flask, send_file

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Read environment variables
email = os.getenv('EMAIL')
password = os.getenv('PASSWORD')
discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')

# Main website URL
main_url = 'https://www.csgoroll.com/withdraw/csgo/p2p'

# Initialize HTML log
def initialize_html_log():
    html_template = """
    <!DOCTYPE html>
    <html lang="en" class="dark">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CSGORoll Crate Opening Log</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <script>
            tailwind.config = {
                darkMode: 'class',
                theme: {
                    extend: {
                        colors: {
                            dark: {
                                100: '#1a202c',
                                200: '#2d3748',
                                300: '#4a5568',
                            }
                        }
                    }
                }
            }
        </script>
    </head>
    <body class="bg-dark-100 text-gray-300 min-h-screen" x-data="{ showCopiedMessage: false }">
        <div class="container mx-auto px-4 py-8">
            <h1 class="text-4xl font-bold mb-6 text-blue-400 border-b-2 border-blue-500 pb-2">CSGORoll Crate Opening Log</h1>
            
            <div class="mb-4 flex space-x-2">
                <button @click="downloadLog()" class="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded transition duration-300 flex items-center">
                    <i class="fas fa-download mr-2"></i> Download Log
                </button>
            </div>
            <div id="log-container"></div>
        </div>

        <script>
            function downloadLog() {
                const logContent = document.getElementById('log-container').innerText;
                const blob = new Blob([logContent], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'csgoroll_log.txt';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }
        </script>
    </body>
    </html>
    """
    with open('index.html', 'w') as file:
        file.write(html_template)

def log_to_html(message, level='info'):
    log_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    level_classes = {
        'info': 'border-blue-500 text-blue-400',
        'success': 'border-green-500 text-green-400',
        'warning': 'border-yellow-500 text-yellow-400',
        'error': 'border-red-500 text-red-400'
    }
    level_class = level_classes.get(level, level_classes['info'])
    log_entry = f"""
    <div class="bg-dark-200 border-l-4 {level_class} p-4 rounded mb-4">
        <span class="text-gray-400 text-sm">{log_time}</span>
        <p class="mt-1">{message}</p>
    </div>
    """
    with open('index.html', 'r+') as file:
        content = file.read()
        position = content.find('<div id="log-container"></div>')
        if position != -1:
            file.seek(position)
            file.write(f'{log_entry}\n<div id="log-container"></div>')
        else:
            file.write(log_entry)

def send_to_discord(message):
    try:
        payload = {
            'content': message
        }
        response = requests.post(discord_webhook_url, json=payload)
        response.raise_for_status()
    except Exception as e:
        log_to_html(f"Failed to send message to Discord: {e}", "error")

def handle_popups(driver):
    popups_handled = False
    while not popups_handled:
        try:
            close_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.mat-focus-indicator.close.mat-icon-button.mat-button-base'))
            )
            close_button.click()
            log_to_html("Closed Popup 1", "success")
            popup2_accept_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.cky-btn.cky-btn-accept'))
            )
            popup2_accept_button.click()
            log_to_html("Closed Popup 2", "success")
            popups_handled = True
        except Exception as e:
            log_to_html(f"Error handling popups: {e}", "warning")
            time.sleep(5)

sold_values = []

def open_crates():
    driver = None
    crates_opened = 0
    initial_balance = 0.00
    final_balance = 0.00
    try:
        logger.info("Starting the application")
        chrome_options = Options()
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--verbose")
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        driver_path = '/usr/local/bin/chromedriver'  # Path to ChromeDriver
        driver = uc.Chrome(driver_executable_path=driver_path, options=chrome_options)
        logger.info("Page title was '{}'".format(driver.title))
        driver.get(main_url)
        handle_popups(driver)
        time.sleep(5)
        alt_login_button = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'a.mat-button.mat-button-base.link-btn'))
        )
        alt_login_button.click()
        log_to_html("Clicked Alt Login button", "success")
        alt_login_button_span = alt_login_button.find_element(By.CSS_SELECTOR, 'span.mat-button-wrapper')
        alt_login_button_span.click()
        log_to_html("Clicked Alt Login button (span)", "success")
        email_input = driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="email"]')
        password_input = driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="password"]')
        email_input.clear()
        password_input.clear()
        email_input.send_keys(email)
        password_input.send_keys(password)
        login_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        login_button.click()
        log_to_html("Logged in successfully", "success")
        time.sleep(15)
        rewards_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.nav-link[href="/boxes/world/daily-free"]'))
        )
        rewards_button.click()
        log_to_html("Clicked Rewards button", "success")
        balance_container = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, '.balance-container'))
        )
        balance_text = balance_container.find_element(By.CSS_SELECTOR, '[data-test="value"]').text
        initial_balance = float(balance_text.replace('$', '').replace(',', ''))
        log_to_html(f"Initial balance: ${initial_balance:.2f}", "info")
        crate_elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'cw-box-grid-item-gaming'))
        )
        log_to_html(f'Found {len(crate_elements)} crates', "info")
        send_to_discord(f'Found {len(crate_elements)} crates')
        for crate in crate_elements:
            crate.click()
            log_to_html("Clicked crate", "info")
            time.sleep(10)
            sold_value_element = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'span.value'))
            )
            sold_value = float(sold_value_element.text.replace('$', '').replace(',', ''))
            sold_values.append(sold_value)
            crates_opened += 1
            log_to_html(f"Sold value: ${sold_value:.2f}", "info")
            send_to_discord(f"Sold value: ${sold_value:.2f}")
            log_to_html(f"Crates opened: {crates_opened}", "success")
        balance_text = balance_container.find_element(By.CSS_SELECTOR, '[data-test="value"]').text
        final_balance = float(balance_text.replace('$', '').replace(',', ''))
        log_to_html(f"Final balance: ${final_balance:.2f}", "info")
        message = f"<@610938347652775947> {crates_opened} Crates open -- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ${final_balance - initial_balance:.2f} -- Logs above and at url: localhost:5000"
        send_to_discord(message)
    except Exception as e:
        log_to_html(f"An error occurred: {e}", "error")
    finally:
        if driver:
            driver.quit()

app = Flask(__name__)

@app.route('/')
def index():
    return send_file('index.html')

if __name__ == '__main__':
    initialize_html_log()
    schedule.every(24).hours.do(open_crates)
    threading.Thread(target=app.run, kwargs={'debug': False, 'use_reloader': False}).start()
    while True:
        schedule.run_pending()
        time.sleep(1)
