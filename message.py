from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import argparse
from selenium_stealth import stealth
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import os
import sys

# Load environment variables
load_dotenv()

# Facebook credentials from environment variables
email = os.getenv('FB_EMAIL')
password = os.getenv('FB_PASSWORD')

# List of user agents to rotate
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
]

def get_random_user_agent():
    return random.choice(user_agents)

def human_delay():
    """Add a random delay to simulate human behavior"""
    time.sleep(random.uniform(0.5, 2.0))

def type_like_human(element, text):
    """Type text like a human with random delays between keystrokes"""
    # Replace newlines with spaces to prevent line breaks
    text = text.replace('\n', ' ')
    
    for char in text:
        element.send_keys(char)
        # Random delay between keystrokes (50-150ms)
        time.sleep(random.uniform(0.05, 0.15))
    
    # Add a small delay after typing
    human_delay()

def setup_driver():
    options = Options()
    options.add_argument(f"user-agent={get_random_user_agent()}")
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
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

def send_messenger_message(driver, user_id: str, message: str):
    try:
        # Navigate to Facebook
        driver.get("https://www.facebook.com")
        human_delay()  # Wait for page load
        
        # Login
        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "email"))
        )
        human_delay()  # Wait before typing
        type_like_human(email_field, email)
        
        password_field = driver.find_element(By.ID, "pass")
        human_delay()  # Wait before typing password
        type_like_human(password_field, password)
        
        # Click login button instead of pressing Enter
        login_button = driver.find_element(By.NAME, "login")
        human_delay()  # Wait before clicking
        login_button.click()
        
        # Wait for login to complete and check for 2FA or CAPTCHA
        time.sleep(random.uniform(3, 5))
        
        # Check for 2FA
        try:
            # Look for common 2FA elements
            two_factor_elements = [
                "//input[@name='approvals_code']",  # 2FA code input
                "//div[contains(text(), 'Enter security code')]",  # 2FA text
                "//div[contains(text(), 'Two-factor authentication')]"  # 2FA header
            ]
            
            for selector in two_factor_elements:
                try:
                    element = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    if element:
                        print("2FA detected! Please enter the code manually.")
                        input("Enter the 2FA code and press Enter to continue...")
                        break
                except:
                    continue
        except Exception as e:
            print(f"Error checking for 2FA: {str(e)}")
        
        # Check for CAPTCHA
        try:
            # Look for common CAPTCHA elements
            captcha_elements = [
                "//iframe[contains(@src, 'captcha')]",
                "//div[contains(@class, 'captcha')]",
                "//div[contains(text(), 'Security Check')]",
                "//div[contains(text(), 'Verify you're not a robot')]"
            ]
            
            for selector in captcha_elements:
                try:
                    element = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    if element:
                        print("CAPTCHA detected! Please solve it manually.")
                        input("Solve the CAPTCHA and press Enter to continue...")
                        break
                except:
                    continue
        except Exception as e:
            print(f"Error checking for CAPTCHA: {str(e)}")
        
        # Navigate to messenger
        driver.get(f"https://www.facebook.com/messages/t/{user_id}")
        time.sleep(random.uniform(4, 6))  # Wait for messenger to load
        
        # Check for and click the Continue button if it exists
        try:
            # Try multiple selectors for the Continue button
            continue_button = None
            selectors = [
                "//div[@aria-label='Continue' and @role='button']",
                "//div[contains(@class, 'x1i10hfl') and .//span[contains(text(), 'Continue')]]",
                "//div[@role='button' and .//span[contains(@class, 'x1lliihq') and contains(text(), 'Continue')]]"
            ]
            
            for selector in selectors:
                try:
                    continue_button = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    if continue_button:
                        break
                except:
                    continue
            
            if continue_button:
                # Try regular click first
                try:
                    human_delay()  # Wait before clicking continue
                    continue_button.click()
                except:
                    # If regular click fails, try JavaScript click
                    try:
                        driver.execute_script("arguments[0].click();", continue_button)
                    except:
                        # If JavaScript click fails, try moving to element and clicking
                        from selenium.webdriver.common.action_chains import ActionChains
                        actions = ActionChains(driver)
                        actions.move_to_element(continue_button).click().perform()
                
                time.sleep(random.uniform(2, 3))  # Wait for the button click to take effect
            else:
                print("Continue button not found with any selector")
        except Exception as e:
            print(f"Error handling Continue button: {str(e)}")
            print("Proceeding with message...")
        
        # Find message input and send message
        message_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[role='textbox']"))
        )
        human_delay()  # Wait before typing message
        type_like_human(message_input, message)
        
        # Wait before sending
        human_delay()
        message_input.send_keys(Keys.RETURN)
        
        # Wait for message to be sent
        time.sleep(random.uniform(2, 4))
        return True
    except Exception as e:
        print(f"Error sending Messenger message: {str(e)}")
        return False

def send_whatsapp_message(driver, phone_number: str, message: str):
    try:
        # Navigate to WhatsApp Web
        driver.get("https://web.whatsapp.com")
        
        # Wait for QR code scan
        input("Please scan the QR code and press Enter to continue...")
        
        # Add a natural delay after QR scan
        time.sleep(random.uniform(2, 4))
        
        # Navigate to chat
        driver.get(f"https://web.whatsapp.com/send?phone={phone_number}")
        time.sleep(random.uniform(4, 6))  # Wait for chat to load
        
        # Find message input and send message
        message_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[title='Type a message']"))
        )
        human_delay()  # Wait before typing
        type_like_human(message_input, message)
        
        # Wait before sending
        human_delay()
        message_input.send_keys(Keys.RETURN)
        
        # Wait for message to be sent
        time.sleep(random.uniform(2, 4))
        return True
    except Exception as e:
        print(f"Error sending WhatsApp message: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Send messages via WhatsApp or Messenger')
    parser.add_argument('--platform', choices=['whatsapp', 'messenger'], required=True,
                      help='Platform to send message through')
    parser.add_argument('--phone', help='Phone number for WhatsApp')
    parser.add_argument('--user_id', help='User ID for Messenger')
    parser.add_argument('--message', required=True, help='Message to send')
    
    args = parser.parse_args()
    
    driver = setup_driver()
    
    try:
        success = False
        if args.platform == 'whatsapp':
            if not args.phone:
                raise ValueError("Phone number is required for WhatsApp")
            success = send_whatsapp_message(driver, args.phone, args.message)
        else:  # messenger
            if not args.user_id:
                raise ValueError("User ID is required for Messenger")
            success = send_messenger_message(driver, args.user_id, args.message)
        
        # Exit with appropriate status code
        sys.exit(0 if success else 1)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
