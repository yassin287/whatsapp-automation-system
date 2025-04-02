import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
import subprocess
import os
from urllib.parse import quote

class WhatsAppBot:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.is_running = False
        
    def kill_edge_processes(self):
        """Kill any existing Edge processes"""
        try:
            subprocess.run(['taskkill', '/F', '/IM', 'msedge.exe'], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
            time.sleep(2)
        except Exception:
            pass
        
    def setup_driver(self):
        """Setup the Edge WebDriver with existing profile"""
        try:
            self.kill_edge_processes()
            
            options = Options()
            options.add_argument("--start-maximized")
            edge_profile = os.path.join(os.getcwd(), "whatsapp_bot_profile")
            options.add_argument(f"user-data-dir={edge_profile}")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-web-security")
            options.add_argument("--disable-site-isolation-trials")
            options.add_argument("--disable-features=IsolateOrigins,site-per-process")
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0")
            
            service = Service()
            self.driver = webdriver.Edge(service=service, options=options)
            self.wait = WebDriverWait(self.driver, 60)
            
            # Set page load timeout
            self.driver.set_page_load_timeout(60)
            
            return self.driver
            
        except Exception as e:
            print(f"Error setting up Edge driver: {str(e)}")
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            self.driver = None
            raise

    def login_to_whatsapp(self):
        """Open WhatsApp Web with existing session"""
        try:
            print("Opening WhatsApp Web...")
            self.driver.get("https://web.whatsapp.com")
            time.sleep(5)
            
            print("Waiting for WhatsApp Web to load...")
            initial_load = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="textbox"], div[data-testid="qrcode"]'))
            )
            
            textbox = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="textbox"]')
            if textbox:
                print("Successfully connected to existing WhatsApp Web session!")
                return
                
            qr_code = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="qrcode"]'))
            )
            if qr_code:
                print("Please scan the QR code to login to WhatsApp Web...")
                chat_list = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="textbox"]'))
                )
                if chat_list:
                    print("Successfully logged in to WhatsApp Web!")
                    return
            
            raise Exception("Could not detect login status")
                
        except Exception as e:
            print(f"Error connecting to WhatsApp Web: {str(e)}")
            raise

    def send_message_to_number(self, phone_number, message):
        """Send a message to a specific phone number"""
        try:
            if not self.driver or not self.is_running:
                print("Bot is not initialized or not running")
                return False
                
            # Format phone number
            phone_number = ''.join(filter(str.isdigit, phone_number))
            if not phone_number.startswith('20'):
                phone_number = '20' + phone_number
                
            # Construct WhatsApp URL
            url = f"https://web.whatsapp.com/send?phone={phone_number}&text={quote(message)}"
            print(f"Navigating to: {url}")
            
            # Navigate to chat
            self.driver.get(url)
            time.sleep(5)  # Wait for page to load
            
            # Wait for chat to load
            try:
                send_button = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//span[@data-icon='send']"))
                )
                send_button.click()
                print("Message sent successfully")
                return True
            except Exception as e:
                print(f"Error sending message: {str(e)}")
                return False
                
        except Exception as e:
            print(f"Error in send_message_to_number: {str(e)}")
            return False

    def start(self):
        """Initialize the bot and connect to WhatsApp Web"""
        try:
            print("Starting WhatsApp bot...")
            self.driver = self.setup_driver()
            self.wait = WebDriverWait(self.driver, 60)
            
            print("Logging in to WhatsApp Web...")
            self.login_to_whatsapp()
            
            self.is_running = True
            print("Bot started successfully")
            return True
            
        except Exception as e:
            print(f"Error starting bot: {str(e)}")
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            self.driver = None
            self.is_running = False
            return False

def main():
    bot = WhatsAppBot()
    bot.start()

if __name__ == "__main__":
    main() 