from flask import Flask, render_template, request, jsonify
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import os
import time
import schedule
import threading
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('whatsapp_bot.log'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)

# Global variables
bot = None
bot_thread = None
scheduler_thread = None
is_bot_running = False

def load_config():
    """Load configuration from config.json"""
    if os.path.exists('config.json'):
        with open('config.json', 'r') as f:
            return json.load(f)
    return {
        'recipients': [],
        'message_templates': [],
        'scheduled_messages': [],
        'message_history': [],
        'stats': {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'pending': 0
        }
    }

def save_config(config):
    """Save configuration to config.json"""
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

def update_stats(status):
    """Update message statistics"""
    config = load_config()
    config['stats']['total'] += 1
    if status == 'success':
        config['stats']['successful'] += 1
    elif status == 'error':
        config['stats']['failed'] += 1
    save_config(config)

def add_to_history(recipient, message, status):
    """Add message to history"""
    config = load_config()
    config['message_history'].append({
        'recipient': recipient,
        'message': message,
        'status': status,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    save_config(config)

def setup_scheduled_message(schedule_item, recipient, template):
    """Set up a scheduled message using the schedule library"""
    try:
        if schedule_item['type'] == 'one_time':
            schedule.every().day.at(schedule_item['time']).do(
                send_scheduled_message, recipient, template
            ).tag(f"one_time_{schedule_item['id']}")
        elif schedule_item['type'] == 'daily':
            schedule.every().day.at(schedule_item['time']).do(
                send_scheduled_message, recipient, template
            ).tag(f"daily_{schedule_item['id']}")
        elif schedule_item['type'] == 'weekly':
            getattr(schedule.every(), schedule_item['day'].lower()).at(schedule_item['time']).do(
                send_scheduled_message, recipient, template
            ).tag(f"weekly_{schedule_item['id']}")
        elif schedule_item['type'] == 'monthly':
            schedule.every().month.at(schedule_item['time']).do(
                send_scheduled_message, recipient, template
            ).tag(f"monthly_{schedule_item['id']}")
        return True
    except Exception as e:
        logging.error(f"Error setting up schedule: {str(e)}")
        return False

def setup_all_schedules():
    """Set up all active scheduled messages"""
    config = load_config()
    for schedule_item in config['scheduled_messages']:
        if schedule_item['active']:
            recipient = next((r for r in config['recipients'] if r['id'] == schedule_item['recipient_id']), None)
            template = next((t for t in config['message_templates'] if t['id'] == schedule_item['template_id']), None)
            if recipient and template:
                setup_scheduled_message(schedule_item, recipient, template)

def send_scheduled_message(recipient, template):
    """Send a scheduled message"""
    try:
        message = template['content'].format(name=recipient['name'])
        success = send_whatsapp_message(recipient['phone'], message)
        status = 'success' if success else 'error'
        add_to_history(recipient['name'], message, status)
        update_stats(status)
    except Exception as e:
        logging.error(f"Error sending scheduled message: {str(e)}")
        add_to_history(recipient['name'], template['content'], 'error')
        update_stats('error')

def send_whatsapp_message(phone, message):
    """Send WhatsApp message using Selenium"""
    try:
        # Format phone number
        phone = phone.replace('+', '').replace(' ', '')
        
        # Navigate to WhatsApp Web
        bot.get(f'https://web.whatsapp.com/send?phone={phone}&text={message}')
        
        # Wait for send button and click it
        send_button = WebDriverWait(bot, 30).until(
            EC.presence_of_element_located((By.XPATH, "//span[@data-icon='send']"))
        )
        send_button.click()
        
        # Wait for message to be sent
        time.sleep(2)
        return True
    except Exception as e:
        logging.error(f"Error sending message: {str(e)}")
        return False

def run_scheduler():
    """Run the scheduler in a separate thread"""
    while is_bot_running:
        schedule.run_pending()
        time.sleep(1)

def start_bot():
    """Start the WhatsApp bot"""
    global bot, bot_thread, scheduler_thread, is_bot_running
    
    try:
        # Set up Edge options
        edge_options = Options()
        edge_options.add_argument("--user-data-dir=./whatsapp_bot_profile")
        edge_options.add_argument("--start-maximized")
        
        # Initialize the bot
        service = Service()
        bot = webdriver.Edge(service=service, options=edge_options)
        bot.get('https://web.whatsapp.com')
        
        # Wait for QR code scan
        WebDriverWait(bot, 60).until(
            EC.presence_of_element_located((By.XPATH, "//div[@id='side']"))
        )
        
        is_bot_running = True
        
        # Set up all schedules
        setup_all_schedules()
        
        # Start scheduler thread
        scheduler_thread = threading.Thread(target=run_scheduler)
        scheduler_thread.start()
        
        return True
    except Exception as e:
        logging.error(f"Error starting bot: {str(e)}")
        return False

def stop_bot():
    """Stop the WhatsApp bot"""
    global bot, bot_thread, scheduler_thread, is_bot_running
    
    try:
        is_bot_running = False
        if bot:
            bot.quit()
        if scheduler_thread:
            scheduler_thread.join()
        return True
    except Exception as e:
        logging.error(f"Error stopping bot: {str(e)}")
        return False

@app.route('/')
def index():
    """Render the main page"""
    config = load_config()
    return render_template('index.html',
                         recipients=config['recipients'],
                         templates=config['message_templates'],
                         scheduled_messages=config['scheduled_messages'],
                         message_history=config['message_history'],
                         stats=config['stats'])

@app.route('/start_bot', methods=['POST'])
def start_bot_route():
    """Start the WhatsApp bot"""
    success = start_bot()
    return jsonify({'success': success})

@app.route('/stop_bot', methods=['POST'])
def stop_bot_route():
    """Stop the WhatsApp bot"""
    success = stop_bot()
    return jsonify({'success': success})

@app.route('/add_recipient', methods=['POST'])
def add_recipient():
    """Add a new recipient"""
    try:
        data = request.json
        config = load_config()
        
        # Generate unique ID
        recipient_id = str(len(config['recipients']) + 1)
        
        new_recipient = {
            'id': recipient_id,
            'name': data['name'],
            'phone': data['phone']
        }
        
        config['recipients'].append(new_recipient)
        save_config(config)
        
        return jsonify({'success': True, 'recipient': new_recipient})
    except Exception as e:
        logging.error(f"Error adding recipient: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/add_template', methods=['POST'])
def add_template():
    """Add a new message template"""
    try:
        data = request.json
        config = load_config()
        
        # Generate unique ID
        template_id = str(len(config['message_templates']) + 1)
        
        new_template = {
            'id': template_id,
            'name': data['name'],
            'content': data['content']
        }
        
        config['message_templates'].append(new_template)
        save_config(config)
        
        return jsonify({'success': True, 'template': new_template})
    except Exception as e:
        logging.error(f"Error adding template: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/schedule_message', methods=['POST'])
def schedule_message():
    """Schedule a new message"""
    try:
        data = request.json
        config = load_config()
        
        # Validate recipient and template
        recipient = next((r for r in config['recipients'] if r['id'] == data['recipient_id']), None)
        template = next((t for t in config['message_templates'] if t['id'] == data['template_id']), None)
        
        if not recipient or not template:
            return jsonify({'success': False, 'error': 'Invalid recipient or template'})
        
        # Generate unique ID
        schedule_id = str(len(config['scheduled_messages']) + 1)
        
        new_schedule = {
            'id': schedule_id,
            'recipient_id': data['recipient_id'],
            'template_id': data['template_id'],
            'type': data['type'],
            'time': data['time'],
            'day': data.get('day'),
            'date': data.get('date'),
            'active': True
        }
        
        config['scheduled_messages'].append(new_schedule)
        save_config(config)
        
        # If bot is running, set up the schedule immediately
        if is_bot_running:
            setup_scheduled_message(new_schedule, recipient, template)
        
        return jsonify({'success': True, 'schedule': new_schedule})
    except Exception as e:
        logging.error(f"Error scheduling message: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/send_message', methods=['POST'])
def send_message():
    """Send a message immediately"""
    try:
        data = request.json
        config = load_config()
        
        recipient = next((r for r in config['recipients'] if r['id'] == data['recipient_id']), None)
        template = next((t for t in config['message_templates'] if t['id'] == data['template_id']), None)
        
        if not recipient or not template:
            return jsonify({'success': False, 'error': 'Invalid recipient or template'})
        
        message = template['content'].format(name=recipient['name'])
        success = send_whatsapp_message(recipient['phone'], message)
        
        status = 'success' if success else 'error'
        add_to_history(recipient['name'], message, status)
        update_stats(status)
        
        return jsonify({'success': success})
    except Exception as e:
        logging.error(f"Error sending message: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
