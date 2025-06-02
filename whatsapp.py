from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
from selenium_stealth import stealth
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from alert import send_alert
import os
import re

# List of user agents
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
]

def get_random_user_agent():
    return random.choice(user_agents)

def human_delay():
    time.sleep(random.uniform(0.5, 2.0))

def type_like_human(element, text):
    time.sleep(6)
    # Clear existing text using CTRL+A and Backspace
    element.send_keys(Keys.CONTROL + "a")
    element.send_keys(Keys.BACKSPACE)
    human_delay()
    
    text = text.replace('\n', ' ')
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.01, 0.05))
    human_delay()

def setup_driver():
    options = Options()
    options.add_argument(f"user-agent={get_random_user_agent()}")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Use absolute path for session directory
    user_data_path = os.path.abspath("whatsapp_session")
    options.add_argument(f"--user-data-dir={user_data_path}")
    options.add_argument("--profile-directory=Default")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    return driver

# Global driver instance
_driver = None

def get_driver():
    global _driver
    if _driver is None:
        _driver = setup_driver()
    return _driver

def wait_for_qr_scan(driver, timeout=300):
    """
    Wait for the QR code to be scanned and WhatsApp Web to be ready.
    
    Args:
        driver: Selenium WebDriver instance
        timeout: Maximum time to wait in seconds
        
    Returns:
        bool: True if QR code was scanned successfully, False if timeout occurred
    """
    time.sleep(30)
    try:
        # First check if already logged in by looking for "Loading your chats"
        try:
            WebDriverWait(driver, 30).until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Loading your chats')]")),
                    EC.presence_of_element_located((By.XPATH, "//*[normalize-space(text())='Chats']"))
                )
            )
            print("Already logged in - Loading chats detected")
            return True
        except:
            print("Not logged in - proceeding with QR code check")
        
        # First check if QR code is present by looking for specific text patterns
        qr_code_texts = [
            "Log in to WhatsApp Web",
            "WhatsApp Web",
            "Scan QR code",
            "To use WhatsApp on your computer",
            "Log in"
        ]
        
        # Find which text is present on the page
        found_text = None
        for text in qr_code_texts:
            try:
                element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, f"//*[contains(text(), '{text}')]"))
                )
                found_text = text
                print(f"QR code page detected: Found text '{text}'")
                send_alert(
                    subject="WhatsApp Web QR Code Detected",
                    message=f"Scan the QR code within next {timeout} seconds",
                    recipient=os.getenv("ALERT_RECIPIENT")
                )
                break
            except:
                continue
        
        if found_text == None:
            print("No QR code text patterns found on the page")
            return False
            
        # Start time for timeout
        start_time = time.time()
        
        # While loop to check if the text remains present
        while time.time() - start_time < timeout:
            try:
                # Check if the text is still present
                driver.find_element(By.XPATH, f"//*[contains(text(), '{found_text}')]")
                # If text is still present, wait a bit and check again
                time.sleep(1)
            except:
                # If text is no longer present, QR code was likely scanned
                print("QR code text no longer present - likely scanned")
                # Wait longer for the page to fully load
                print("Waiting for page to load completely...")
                time.sleep(20)  # Increased wait time
                try:
                    # Verify Chats text is present (without relying on specific class)
                    WebDriverWait(driver, 60).until(  # Increased timeout
                        EC.presence_of_element_located((By.XPATH, "//*[text()='Chats']"))
                    )
                    print("Chats text detected - QR code scanned successfully!")
                    return True
                except:
                    print("Chats text not found after QR code text disappeared")
                    return False
        
        print("Timeout waiting for QR code to be scanned")
        return False
        
    except Exception as e:
        print("Error during QR code scanning:", str(e))
        try:
            driver.close()
            driver.switch_to.new_window('tab')
        except:
            pass
        return False

def send_message(phone_number: str, message: str) -> bool:
    """
    Send a WhatsApp message using Selenium.
    Maintains the same interface as the previous implementation.
    
    Args:
        phone_number (str): Phone number with country code (e.g., +1234567890)
        message (str): Message to send
        
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    try:
        # Ensure phone number is properly formatted
        phone_number = str(phone_number)
        # Remove all non-digit characters
        phone_number = re.sub(r'\D', '', phone_number)
        
        driver = get_driver()
        
        # First, go to the main WhatsApp Web page
        driver.get("https://web.whatsapp.com")
        
        # Wait for QR code to be scanned
        if not wait_for_qr_scan(driver):
            print("Failed to scan QR code within timeout period")
            cleanup()  # Clean up the driver completely
            return False
            
        # Now go to the specific chat
        url = f"https://web.whatsapp.com/send?phone={phone_number}"
        driver.get(url)

        print("Waiting for WhatsApp chat to load...")
        WebDriverWait(driver, 90).until(
            EC.presence_of_element_located((By.XPATH, "//div[@data-tab='10' and @contenteditable='true']"))
        )

        # Get the message input box
        message_box = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@data-tab='10' and @contenteditable='true']"))
        )
        message_box.click()
        type_like_human(message_box, message)

        # Wait for the Send button and click it
        send_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Send']"))
        )
        send_button.click()

        print("Message sent successfully!")
        time.sleep(2)
        
        # Close the current window but keep the session
        driver.close()
        
        return True

    except Exception as e:
        print(f"Error sending WhatsApp message: {str(e)}")
        # Close the window even if there's an error
        try:
            driver.close()
            driver.switch_to.new_window('tab')
        except:
            pass
        cleanup()  # Clean up the driver completely
        return False

def cleanup():
    """Clean up the driver when the program exits"""
    global _driver
    if _driver is not None:
        try:
            _driver.quit()
        except:
            pass
        _driver = None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Send WhatsApp messages using Selenium')
    parser.add_argument('--phone', required=True, help='Phone number with country code (e.g., +1234567890)')
    parser.add_argument('--message', required=True, help='Message to send')
    
    args = parser.parse_args()
    
    try:
        send_message(args.phone, args.message)
    finally:
        cleanup()