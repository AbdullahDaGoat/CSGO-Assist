import os
import sys
import time
from datetime import datetime
import logging
import schedule
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import requests
import threading
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set up ChromeDriver and Prevent excess logging
sys.stderr = open(os.devnull, 'w')

# Read environment variables
email = os.getenv('EMAIL')
password = os.getenv('PASSWORD')
discord_webhook_url = "https://discord.com/api/webhooks/1261580835035807744/Wh3dne1wda8oX5zlrDZUVtYHhkTaUYOwhkD_Y5KLlZb8oxQ_xWTCVQljPxwabYpwWc0r"

# Main website URL
main_url = 'https://www.csgoroll.com/withdraw/csgo/p2p'

# Function to render html template
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
    # Define Tailwind classes for different log levels
    level_classes = {
        'info': 'border-blue-500 text-blue-400',
        'success': 'border-green-500 text-green-400',
        'warning': 'border-yellow-500 text-yellow-400',
        'error': 'border-red-500 text-red-400'
    }
    
    # Use the appropriate class based on the log level
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
        payload = {
            'content': message
        }
        response = requests.post(discord_webhook_url, json=payload)
        response.raise_for_status()
    except Exception as e:
        log_to_html(f"Failed to send message to Discord: {e}", "error")

def handle_popups(driver):
    popups_handled = False

    # If both popups were not closesd we have created a loop to ensure they are prior to continuing
    while not popups_handled:
        try:
            # Handle Popup 1
            close_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.mat-focus-indicator.close.mat-icon-button.mat-button-base'))
            )
            close_button.click()
            log_to_html("Closed Popup 1", "success")

            # Handle Popup 2
            popup2_accept_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.cky-btn.cky-btn-accept'))
            )
            popup2_accept_button.click()
            log_to_html("Closed Popup 2", "success")

            popups_handled = True  # Both popups handled successfully
        except Exception as e:
            log_to_html(f"Error handling popups: {e}", "warning")

# Initialize Sold values as a list to map later (so if sold value is none then the value outputed is zero)
sold_values = []

# Function to login and open crates
def open_crates():
    driver = None # Initialize chrome web driver as None
    crates_opened = 0  # Counter for number of crates opened
    try:
        # Configure Chrome options to prevent bot from being blocked / gettoing external errors
        chrome_options = Options()
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--log-level=3")  # Suppresses warnings and info logs
        chrome_options.add_argument("--verbose")  
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--headless')

        
        # Initialize undetected Chrome WebDriver with options
        driver = uc.Chrome(service=Service('/usr/local/bin/chromedriver'), options=chrome_options)

        # Open main URL
        driver.get(main_url)

        # Call the Handle popups function
        handle_popups(driver)

        # Wait for the entire page to load
        time.sleep(5)

        # Click on the "Alt Login" button
        try:
            alt_login_button = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'a.mat-button.mat-button-base.link-btn'))
            )
            alt_login_button.click()
            log_to_html("Clicked Alt Login button", "success")

            # Optionally, click on the <span> element if necessary
            alt_login_button_span = alt_login_button.find_element(By.CSS_SELECTOR, 'span.mat-button-wrapper')
            alt_login_button_span.click()
            log_to_html("Clicked Alt Login button (span)", "success")

        except Exception as e:
            log_to_html(f"Error clicking Alt Login button: {e}", "error")

        # Clear (in case of autofill) and fill in the email and password fields
        try:
            email_input = driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="email"]')
            password_input = driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="password"]')

            email_input.clear()
            password_input.clear()

            email_input.send_keys(email)
            password_input.send_keys(password)
        except Exception as e:
            log_to_html(f"Error filling in email and password: {e}", "error")

        # Click the Login button
        try:
            login_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            login_button.click()
            log_to_html("Logged in successfully", "success")
        except Exception as e:
            log_to_html(f"Error clicking login button: {e}", "error")

        # Wait for 15 seconds to ensure the page is fully loaded
        time.sleep(15)

        # Click the rewards button
        try:
            rewards_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.nav-link[href="/boxes/world/daily-free"]'))
            )
            rewards_button.click()
            log_to_html("Clicked Rewards button", "success")
        except Exception as e:
            log_to_html(f"Error clicking rewards button: {e}", "error")

        try:
            initial_balance_element = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, '.balance .amount'))
            )
            initial_balance = float(initial_balance_element.text.replace('$', '').replace(',', ''))
            log_to_html(f"Initial balance: ${initial_balance:.2f}", "info")
        except Exception as e:
            log_to_html(f"Error extracting initial balance: {e}", "error")

        # Get all the crates 
        crate_elements = []
        try:
            crate_elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'cw-box-grid-item-gaming'))
            )
            log_to_html(f'Found {len(crate_elements)} crates', "info")
            send_to_discord(f'Found {len(crate_elements)} crates')
        except Exception as e:
            log_to_html(f"Error retrieving crates: {e}", "error")

            
        # Open and sell each crate
        for crate in crate_elements:
            try:
                # Check if the crate is disabled
                open_now_button = crate.find_element(By.CSS_SELECTOR, 'button[data-test="open-case"]')
                if 'mat-button-disabled' in open_now_button.get_attribute('class'):
                    log_to_html('Crate is disabled, skipping...', "info")
                    continue

                # Click the "Open Now" button
                open_now_button.click()
                log_to_html('Opened crate', "success")
                time.sleep(5)

                # Click the "Open 1 time" button
                open_box_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-test="open-box-button"]'))
                )
                open_box_button.click()
                log_to_html('Opened box', "success")
                time.sleep(7)

                # Click the "Sell" button
                sell_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-test="sell-reward-button"]'))
                )
                sell_button.click()
                log_to_html('Sold reward', "success")
                time.sleep(3)

                # Confirm the sale
                confirm_sell_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-test="sell-reward-button"]'))
                )
                confirm_sell_button.click()
                log_to_html('Confirmed sale', "success")
                time.sleep(5)

                # Close the crate
                close_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[mat-dialog-close]'))
                )
                close_button.click()
                log_to_html('Closed crate', "success")

                crates_opened += 1

            except Exception as e:
                log_to_html(f"Error opening/selling crate: {e}", "error")

        log_to_html('Crates opened and sold successfully!', "success")
        send_to_discord('Crates opened and sold successfully!')

        try:
            final_balance_element = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, '.balance .amount'))
            )
            final_balance = float(final_balance_element.text.replace('$', '').replace(',', ''))
            log_to_html(f"Final balance: ${final_balance:.2f}", "info")
        except Exception as e:
            log_to_html(f"Error extracting final balance: {e}", "error")

        # Prepare final log message
        balance_difference = final_balance - initial_balance
        log_to_html(f"Balance difference after opening crates: ${balance_difference:.2f}", "info")
        total_value = balance_difference
        final_message = f'<@610938347652775947>, Hey there I have succesfully opened **{crates_opened}** Crates on **{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}**. We also successfully sold all of the crates amounting to a total value of: **$ {total_value:.2f}, in game currency**! My Logs are can be viewed and downloaded at https://localhost:443 -- Thanks for using Crate Open Bot! -- Made by DebateMyRoomba'
        log_to_html(final_message, "info")
        send_to_discord(final_message)

    except Exception as e:
        log_to_html(f"Error opening crates: {e}", "error")
        send_to_discord(f"Error opening crates: {e}")

    finally:
        if driver:
            driver.quit()

# Function to run the crate-opening process at regular intervals
def schedule_open_crates():
    log_to_html('Scheduling crate opening every 24 hours', "info")
    send_to_discord('Scheduling crate opening every 24 hours')
    schedule.every(24).hours.do(open_crates)

    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

# Function to initialize the HTML log file with HTTP
def run_http_server():
    handler = SimpleHTTPRequestHandler
    with TCPServer(("", 443), handler) as httpd:
        print("Serving at port: ", 443)
        httpd.serve_forever()


def main():
    # Initialize the HTML log file
    initialize_html_log()
    
    # Start the HTTP server in a separate thread
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # Run the crate-opening process in the main thread
    open_crates()
    schedule_open_crates()
    log_to_html('Crate opening script is running...', "info")
    send_to_discord('Crate opening script is running...')

    # Keep the main thread running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")

# Run everything
if __name__ == "__main__":
    main()