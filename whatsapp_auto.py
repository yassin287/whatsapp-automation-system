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
import logging

logger = logging.getLogger(__name__)

class WhatsAppBot:
    def __init__(self, headless=False):
        self.driver = None
        self.wait = None
        self.is_running = False
        self.headless = headless  # For VPS deployment
        
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
            
            # VPS/Headless configuration
            if self.headless:
                options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--remote-debugging-port=9222")
                options.add_argument("--disable-extensions")
                options.add_argument("--disable-plugins")
                options.add_argument("--disable-images")
                options.add_argument("--disable-javascript")  # Can help with performance
                options.add_argument("--window-size=1920,1080")
            else:
                options.add_argument("--start-maximized")
            
            # Profile and security settings
            edge_profile = os.path.join(os.getcwd(), "whatsapp_bot_profile")
            options.add_argument(f"user-data-dir={edge_profile}")
            options.add_argument("--disable-web-security")
            options.add_argument("--disable-site-isolation-trials")
            options.add_argument("--disable-features=IsolateOrigins,site-per-process")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # User agent to avoid detection
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0")
            
            # Memory and performance optimization for VPS
            options.add_argument("--memory-pressure-off")
            options.add_argument("--disk-cache-size=50000000")  # 50MB cache
            options.add_argument("--media-cache-size=50000000")
            
            service = Service()
            self.driver = webdriver.Edge(service=service, options=options)
            
            # Execute script to avoid detection
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.wait = WebDriverWait(self.driver, 60)
            
            # Set page load timeout
            self.driver.set_page_load_timeout(60)
            
            logger.info(f"Edge driver setup completed {'(headless mode)' if self.headless else ''}")
            return self.driver
            
        except Exception as e:
            logger.error(f"Error setting up Edge driver: {str(e)}")
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
            logger.info("Opening WhatsApp Web...")
            self.driver.get("https://web.whatsapp.com")
            time.sleep(5)
            
            logger.info("Waiting for WhatsApp Web to load...")
            initial_load = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="textbox"], div[data-testid="qrcode"]'))
            )
            
            # Check if already logged in
            textbox = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="textbox"]')
            if textbox:
                logger.info("Successfully connected to existing WhatsApp Web session!")
                return True
                
            # If QR code is present, wait for manual scan or existing session
            qr_code = self.driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="qrcode"]')
            if qr_code:
                logger.info("QR code detected. Waiting for login...")
                
                # Wait for login (either QR scan or existing session)
                try:
                    chat_list = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="textbox"]'))
                    )
                    if chat_list:
                        logger.info("Successfully logged in to WhatsApp Web!")
                        return True
                except Exception as e:
                    logger.warning(f"Login timeout or error: {str(e)}")
                    # For headless mode, we might need to use existing session
                    if self.headless:
                        logger.warning("Running in headless mode - ensure WhatsApp session is pre-authenticated")
                        return False
                    raise
            
            logger.error("Could not detect login status")
            return False
                
        except Exception as e:
            logger.error(f"Error connecting to WhatsApp Web: {str(e)}")
            return False

    def send_message_to_number(self, phone_number, message):
        """Send a message to a specific phone number"""
        try:
            if not self.driver or not self.is_running:
                logger.error("Bot is not initialized or not running")
                return False
                
            # Format phone number (assuming Egyptian numbers, adjust as needed)
            phone_number = ''.join(filter(str.isdigit, phone_number))
            if not phone_number.startswith('20'):
                phone_number = '20' + phone_number
                
            logger.info(f"Sending message to {phone_number}")
            
            # Step 1: Try to find existing chat first
            success = self._send_to_existing_chat(phone_number, message)
            if success:
                return True
            
            # Step 2: Check if we're already on new chat screen with this contact visible
            success = self._click_non_contact_if_visible(phone_number, message)
            if success:
                return True
            
            # Step 3: Use clean URL method (phone only)
            return self._send_to_new_chat(phone_number, message)
                
        except Exception as e:
            logger.error(f"Error in send_message_to_number: {str(e)}")
            return False

    def _click_non_contact_if_visible(self, phone_number, message):
        """Check if we're on new chat screen and click non-contact entry if visible"""
        try:
            # Check if we're on the new chat screen
            current_url = self.driver.current_url
            if "send" not in current_url and "New chat" not in self.driver.page_source:
                return False
            
            logger.info("Checking for visible non-contact entry...")
            
            # Look for contact under "Not in your contacts" with various formats
            formatted_number = f"+{phone_number[:2]} {phone_number[2:4]} {phone_number[4:]}"
            
            non_contact_selectors = [
                # Look for the exact formatted number display
                f"//span[contains(text(), '{formatted_number}')]",
                f"//div[contains(text(), '{formatted_number}')]",
                
                # Look for unformatted number
                f"//span[contains(text(), '+{phone_number}')]",
                f"//div[contains(text(), '+{phone_number}')]",
                
                # Look in the "Not in your contacts" section
                f"//div[contains(text(), 'Not in your contacts')]//following-sibling::*//span[contains(text(), '{phone_number[-8:]}')]",
                f"//div[contains(text(), 'Not in your contacts')]//parent::*//span[contains(text(), '{phone_number[-8:]}')]",
                
                # Look for clickable contact entries
                f"//div[@role='listitem']//span[contains(text(), '{formatted_number}')]",
                f"//div[@role='listitem']//span[contains(text(), '+{phone_number}')]"
            ]
            
            for selector in non_contact_selectors:
                try:
                    contact_elements = self.driver.find_elements(By.XPATH, selector)
                    
                    for contact_element in contact_elements:
                        if contact_element and contact_element.is_displayed():
                            logger.info(f"Found visible non-contact entry: {formatted_number}")
                            
                            # Try to click the contact or find its clickable parent
                            clickable_element = contact_element
                            
                            # Try to find the clickable parent container
                            for i in range(3):  # Try up to 3 parent levels
                                try:
                                    parent = clickable_element.find_element(By.XPATH, "./..")
                                    if parent.tag_name in ['div', 'button'] and parent.is_enabled():
                                        clickable_element = parent
                                except:
                                    break
                            
                            # Click the element
                            try:
                                clickable_element.click()
                                logger.info("Clicked on non-contact entry successfully")
                                time.sleep(2)
                                
                                # Send the message
                                return self._type_and_send_message(message)
                            except Exception as e:
                                logger.debug(f"Click failed: {str(e)}")
                                continue
                                
                except Exception as e:
                    logger.debug(f"Selector failed: {selector} - {str(e)}")
                    continue
            
            logger.info("No visible non-contact entry found")
            return False
            
        except Exception as e:
            logger.debug(f"Non-contact visibility check failed: {str(e)}")
            return False

    def _send_to_existing_chat(self, phone_number, message):
        """Try to send message to existing chat without page reload"""
        try:
            # First, make sure we're on the main WhatsApp page
            current_url = self.driver.current_url
            if "/send" in current_url or "phone=" in current_url:
                # Go back to main WhatsApp page first
                self.driver.get("https://web.whatsapp.com/")
                time.sleep(2)
            
            # Enhanced selectors for existing chats - including non-contact numbers
            chat_selectors = [
                # Look for exact phone number in chat list (contacts)
                f"//div[contains(@class, 'chat')]//span[contains(text(), '+{phone_number}')]",
                f"//div[contains(@class, 'chat')]//span[contains(text(), '{phone_number}')]",
                
                # Look for partial phone number (last 10 digits)
                f"//div[contains(@class, 'chat')]//span[contains(text(), '{phone_number[-10:]}')]",
                f"//div[contains(@class, 'chat')]//span[contains(text(), '{phone_number[-8:]}')]",
                
                # Look in chat titles/subtitles
                f"//span[@title='+{phone_number}']",
                f"//span[@title='{phone_number}']",
                
                # Look in the entire chat list area
                f"//div[@id='pane-side']//span[contains(text(), '{phone_number[-8:]}')]",
                
                # NEW: Look for non-contact numbers (appears under "Not in your contacts")
                f"//div[contains(@class, 'chat')]//div[contains(text(), '+{phone_number}')]",
                f"//div[contains(@class, 'chat')]//div[contains(text(), '{phone_number}')]",
                
                # NEW: Look in subtitle areas where non-contact numbers appear
                f"//span[contains(@class, 'subtitle')]//span[contains(text(), '+{phone_number}')]",
                f"//span[contains(@class, 'subtitle')]//span[contains(text(), '{phone_number}')]",
                
                # NEW: Look for any element containing the phone number in chat area
                f"//div[@data-testid='cell-frame-container']//span[contains(text(), '{phone_number[-8:]}')]",
                f"//div[@data-testid='cell-frame-container']//div[contains(text(), '{phone_number[-8:]}')]",
                
                # NEW: Look for chat items with phone numbers (broader search)
                f"//*[contains(@class, 'chat')]//*[contains(text(), '{phone_number[-10:]}')]",
                
                # NEW: Look specifically for non-contact entries
                f"//div[contains(text(), 'Not in your contacts')]/..//span[contains(text(), '{phone_number[-8:]}')]",
                f"//div[contains(text(), 'Not in your contacts')]//following-sibling::*//span[contains(text(), '{phone_number[-8:]}')]"
            ]
            
            logger.info(f"Looking for existing chat with {phone_number} (including non-contacts)")
            
            for selector in chat_selectors:
                try:
                    # Use a shorter wait time for existing chat detection
                    chat_elements = self.driver.find_elements(By.XPATH, selector)
                    
                    for chat_element in chat_elements:
                        if chat_element and chat_element.is_displayed():
                            logger.info(f"Found existing chat (possibly non-contact), clicking...")
                            
                            # Click on the chat element or its parent container
                            try:
                                # Try clicking the element itself
                                chat_element.click()
                            except:
                                try:
                                    # Try clicking parent element if direct click fails
                                    parent = chat_element.find_element(By.XPATH, "./..")
                                    parent.click()
                                except:
                                    try:
                                        # Try clicking the chat container (go up more levels)
                                        chat_container = chat_element.find_element(By.XPATH, "./../../..")
                                        chat_container.click()
                                    except:
                                        continue
                            
                            time.sleep(1)
                            
                            # Send the message
                            success = self._type_and_send_message(message)
                            if success:
                                logger.info("Message sent via existing chat (non-contact)")
                                return True
                            
                except Exception as e:
                    logger.debug(f"Selector failed: {selector} - {str(e)}")
                    continue
            
            logger.info("No existing chat found (checked contacts and non-contacts)")
            return False  # No existing chat found
            
        except Exception as e:
            logger.debug(f"Could not find existing chat: {str(e)}")
            return False

    def _send_to_new_chat(self, phone_number, message):
        """Send message to new chat - optimized approach"""
        try:
            # Clean URL with phone number only (no text to avoid mixing)
            url = f"https://web.whatsapp.com/send?phone={phone_number}"
            
            logger.info(f"Opening new chat URL: {url}")
            self.driver.get(url)
            
            # Wait for WhatsApp to load
            time.sleep(3)
            
            # Check if we're redirected to a chat or still on selection screen
            current_url = self.driver.current_url
            logger.info(f"Current URL after navigation: {current_url}")
            
            # If we're on a chat page, send the message directly
            if "chat" in current_url or self._is_in_chat():
                return self._type_and_send_message(message)
            
            # If we're still on selection screen, look for the contact in non-contacts
            return self._click_non_contact_if_visible(phone_number, message)
                
        except Exception as e:
            logger.error(f"Error in _send_to_new_chat: {str(e)}")
            return False

    def _open_new_chat_via_button(self, phone_number, message):
        """Try to open new chat using WhatsApp's new chat button OR click existing non-contact"""
        try:
            # FIRST: Check if we're already in new chat screen with the contact visible
            try:
                # Look for the contact in "Not in your contacts" section
                non_contact_selectors = [
                    f"//div[contains(text(), 'Not in your contacts')]/..//div[contains(text(), '+{phone_number}')]",
                    f"//div[contains(text(), 'Not in your contacts')]//following-sibling::*//span[contains(text(), '{phone_number}')]",
                    f"//span[contains(text(), '+{phone_number[-11:]}')]",  # Format like +20 10 67893250
                    f"//span[contains(text(), '+{phone_number[:2]} {phone_number[2:4]} {phone_number[4:]}')]"  # Formatted number
                ]
                
                for selector in non_contact_selectors:
                    try:
                        contact_element = self.driver.find_element(By.XPATH, selector)
                        if contact_element and contact_element.is_displayed():
                            logger.info("Found non-contact entry, clicking...")
                            
                            # Try to click the contact or its parent container
                            try:
                                contact_element.click()
                            except:
                                # Try clicking parent container
                                parent = contact_element.find_element(By.XPATH, "./..")
                                parent.click()
                            
                            time.sleep(1)
                            return self._type_and_send_message(message)
                    except:
                        continue
                        
            except:
                pass
            
            # If not found, try the new chat button approach
            new_chat_selectors = [
                "//div[@title='New chat']",
                "//span[@data-icon='chat']",
                "//div[contains(@class, 'new-chat')]",
                "//button[@aria-label='New chat']"
            ]
            
            for selector in new_chat_selectors:
                try:
                    new_chat_btn = self.driver.find_element(By.XPATH, selector)
                    if new_chat_btn:
                        new_chat_btn.click()
                        time.sleep(1)
                        
                        # Look for phone number input
                        phone_input_selectors = [
                            "//input[@type='text']",
                            "//div[@contenteditable='true']",
                            "//input[contains(@placeholder, 'phone')]"
                        ]
                        
                        for input_selector in phone_input_selectors:
                            try:
                                phone_input = WebDriverWait(self.driver, 3).until(
                                    EC.presence_of_element_located((By.XPATH, input_selector))
                                )
                                if phone_input:
                                    phone_input.send_keys(f"+{phone_number}")
                                    phone_input.send_keys(Keys.ENTER)
                                    time.sleep(2)
                                    
                                    # Now send the message
                                    return self._type_and_send_message(message)
                            except:
                                continue
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"New chat button method failed: {str(e)}")
            return False

    def _open_new_chat_via_javascript(self, phone_number, message):
        """Use JavaScript to navigate to chat without full reload - phone only"""
        try:
            # Use JavaScript to navigate internally with phone number only
            script = f"""
            // Try to navigate to chat using WhatsApp's internal routing
            if (window.WWebJS || window.Store) {{
                window.location.hash = '#/send?phone={phone_number}';
                return true;
            }}
            return false;
            """
            
            result = self.driver.execute_script(script)
            if result:
                time.sleep(2)
                return self._type_and_send_message(message, from_url=False)
            
            # Alternative JavaScript approach - phone number only
            script2 = f"""
            // Alternative: modify current URL without reload
            const url = new URL(window.location);
            url.pathname = '/send';
            url.searchParams.set('phone', '{phone_number}');
            // DON'T set text parameter to avoid the mixed search issue
            window.history.pushState({{}}, '', url);
            
            // Trigger WhatsApp's internal router if available
            if (window.dispatchEvent) {{
                window.dispatchEvent(new PopStateEvent('popstate'));
            }}
            return true;
            """
            
            self.driver.execute_script(script2)
            time.sleep(2)
            return self._type_and_send_message(message, from_url=False)
            
        except Exception as e:
            logger.debug(f"JavaScript method failed: {str(e)}")
            return False

    def _open_new_chat_via_url_optimized(self, phone_number, message):
        """Super optimized URL method - phone number only, then type message"""
        try:
            # Use JavaScript to navigate to phone number ONLY (no message in URL)
            target_url = f"https://web.whatsapp.com/send?phone={phone_number}"
            
            script = f"""
            // Navigate to chat with phone number only
            window.location.href = '{target_url}';
            return true;
            """
            
            self.driver.execute_script(script)
            time.sleep(2)  # Wait for navigation
            
            # Now type the message manually (not from URL)
            return self._type_and_send_message(message, from_url=False)
                
        except Exception as e:
            logger.error(f"Optimized URL method failed: {str(e)}")
            return False

    def _type_and_send_message(self, message, from_url=False):
        """Type message and click send button - FAST VERSION"""
        try:
            # If message came from URL, it should already be in the input box
            if not from_url:
                # Find message input box and type message
                input_selectors = [
                    "//div[@contenteditable='true'][@data-tab='10']",
                    "//div[@role='textbox'][@contenteditable='true']",
                    "//div[contains(@class, 'message-input')][@contenteditable='true']"
                ]
                
                message_box = None
                for selector in input_selectors:
                    try:
                        message_box = WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                        if message_box.is_displayed():
                            break
                    except:
                        continue
                
                if message_box:
                    # Clear and type message
                    message_box.clear()
                    message_box.send_keys(message)
                    logger.info("Message typed successfully")
                else:
                    logger.error("Could not find message input box")
                    return False
            
            # Wait for send button - FASTER detection with multiple attempts
            send_selectors = [
                "//span[@data-icon='send']",
                "//button[@aria-label='Send']",
                "//span[@data-icon='send']/parent::button",
                "//div[@role='button'][@aria-label='Send']",
                "//button[contains(@class, 'compose-btn-send')]"
            ]
            
            # Try multiple times with shorter waits for faster response
            max_attempts = 3
            for attempt in range(max_attempts):
                for selector in send_selectors:
                    try:
                        # Use shorter wait time but multiple attempts
                        send_button = WebDriverWait(self.driver, 2).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        
                        if send_button and send_button.is_displayed():
                            send_button.click()
                            logger.info("Send button clicked successfully")
                            time.sleep(0.5)  # Shorter wait after sending
                            return True
                            
                    except Exception as e:
                        logger.debug(f"Send button attempt {attempt+1}: {selector} failed")
                        continue
                
                # If no button found, wait a bit and try again
                if attempt < max_attempts - 1:
                    time.sleep(1)
            
            # Last resort: try pressing Enter key
            try:
                active_element = self.driver.switch_to.active_element
                active_element.send_keys(Keys.ENTER)
                logger.info("Sent message using Enter key")
                return True
            except:
                pass
            
            logger.error("Could not find any send button or send method")
            return False
                
        except Exception as e:
            logger.error(f"Error typing and sending message: {str(e)}")
            return False

    def start(self):
        """Initialize the bot and connect to WhatsApp Web"""
        try:
            logger.info("Starting WhatsApp bot...")
            self.driver = self.setup_driver()
            self.wait = WebDriverWait(self.driver, 60)
            
            logger.info("Logging in to WhatsApp Web...")
            login_success = self.login_to_whatsapp()
            
            if login_success:
                self.is_running = True
                logger.info("Bot started successfully")
                return True
            else:
                logger.error("Failed to login to WhatsApp Web")
                return False
            
        except Exception as e:
            logger.error(f"Error starting bot: {str(e)}")
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            self.driver = None
            self.is_running = False
            return False

    def stop(self):
        """Stop the bot and cleanup resources"""
        try:
            if self.driver:
                self.driver.quit()
            self.is_running = False
            logger.info("Bot stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping bot: {str(e)}")

def main():
    # For testing
    bot = WhatsAppBot(headless=False)  # Set to True for VPS
    bot.start()

if __name__ == "__main__":
    main()