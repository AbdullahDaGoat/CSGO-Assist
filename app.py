import os
import time
from datetime import datetime
import logging
import schedule
from playwright.sync_api import sync_playwright
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
discord_webhook_url = "https://discord.com/api/webhooks/1261580835035807744/Wh3dne1wda8oX5zlrDZUVtYHhkTaUYOwhkD_Y5KLlZb8oxQ_xWTCVQljPxwabYpwWc0r"

# Main website URL
main_url = 'https://www.csgoroll.com/withdraw/csgo/p2p'

# Function to render HTML template
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
        position = content.find('</div></body>')
        if position != -1:
            file.seek(position)
            file.write(log_entry + '</div></body></html>')
        else:
            file.write(log_entry)

def send_to_discord(message):
    try:
        payload = {'content': message}
        response = requests.post(discord_webhook_url, json=payload)
        response.raise_for_status()
    except Exception as e:
        log_to_html(f"Failed to send message to Discord: {e}", "error")

def handle_popups(page):
    try:
        page.wait_for_selector('button.mat-focus-indicator.close.mat-icon-button.mat-button-base', timeout=30000)
        page.click('button.mat-focus-indicator.close.mat-icon-button.mat-button-base')
        log_to_html("Closed Popup 1", "success")
        page.wait_for_selector('button.cky-btn.cky-btn-accept', timeout=30000)
        page.click('button.cky-btn.cky-btn-accept')
        log_to_html("Closed Popup 2", "success")
    except Exception as e:
        log_to_html(f"Error handling popups: {e}", "warning")
        time.sleep(5)

sold_values = []

def open_crates():
    crates_opened = 0
    initial_balance = 0.00
    final_balance = 0.00

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)  # Set to True for deployment
            page = browser.new_page()

            logger.info("Starting the application")
            log_to_html("Navigating to the main URL", "info")
            page.goto(main_url)
            handle_popups(page)
            time.sleep(5)

            try:
                page.click('a.mat-button.mat-button-base.link-btn')
                log_to_html("Clicked Alt Login button", "success")
            except Exception as e:
                log_to_html(f"Error clicking Alt Login button: {e}", "error")

            try:
                page.fill('input[formcontrolname="email"]', email)
                page.fill('input[formcontrolname="password"]', password)
                log_to_html("Filled in email and password", "success")
            except Exception as e:
                log_to_html(f"Error filling in email and password: {e}", "error")

            try:
                page.click('button[type="submit"]')
                log_to_html("Logged in successfully", "success")
            except Exception as e:
                log_to_html(f"Error clicking login button: {e}", "error")

            time.sleep(15)

            try:
                page.click('a.nav-link[href="/boxes/world/daily-free"]')
                log_to_html("Clicked Rewards button", "success")
            except Exception as e:
                log_to_html(f"Error clicking rewards button: {e}", "error")

            try:
                balance_text = page.text_content('.balance-container [data-test="value"]')
                initial_balance = float(balance_text.replace('$', '').replace(',', ''))
                log_to_html(f"Initial balance: ${initial_balance:.2f}", "info")
            except Exception as e:
                log_to_html(f"Error extracting initial balance: {e}", "error")

            try:
                crate_elements = page.query_selector_all('cw-box-grid-item-gaming')
                log_to_html(f'Found {len(crate_elements)} crates', "info")
                send_to_discord(f'Found {len(crate_elements)} crates')
            except Exception as e:
                log_to_html(f"Error retrieving crates: {e}", "error")

            for crate in crate_elements:
                try:
                    if 'mat-button-disabled' in crate.get_attribute('class'):
                        log_to_html('Crate is disabled, skipping...', "info")
                        continue

                    crate.click('button[data-test="open-case"]')
                    log_to_html('Opened crate', "success")
                    time.sleep(5)

                    crate.click('button[data-test="open-box-button"]')
                    log_to_html('Opened box', "success")
                    time.sleep(7)

                    crate.click('button[data-test="sell-reward-button"]')
                    log_to_html('Sold reward', "success")
                    time.sleep(3)

                    crate.click('button[data-test="sell-reward-button"]')
                    log_to_html('Confirmed sale', "success")
                    time.sleep(5)

                    crate.click('button[mat-dialog-close]')
                    log_to_html('Closed crate', "success")

                    crates_opened += 1

                except Exception as e:
                    log_to_html(f"Error opening/selling crate: {e}", "error")

            log_to_html('Crates opened and sold successfully!', "success")
            send_to_discord('Crates opened and sold successfully!')

            try:
                balance_text = page.text_content('.balance-container [data-test="value"]')
                final_balance = float(balance_text.replace('$', '').replace(',', ''))
                log_to_html(f"Final balance: ${final_balance:.2f}", "info")
            except Exception as e:
                log_to_html(f"Error extracting final balance: {e}", "error")

            browser.close()

    except Exception as e:
        log_to_html(f"Error running the script: {e}", "error")
    
    summary = f'<@610938347652775947> {crates_opened} Crates open -- {datetime.now()} -- ${final_balance - initial_balance:.2f} -- Logs above and at url: localhost:5000'
    send_to_discord(summary)

    log_to_html("Crate opening completed", "info")

def start_server():
    app = Flask(__name__)

    @app.route('/')
    def serve_log():
        return send_file('index.html')

    app.run(host='0.0.0.0', port=5000)

def run_bot():
    initialize_html_log()
    schedule.every(24).hours.do(open_crates)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    threading.Thread(target=start_server).start()
    run_bot()
