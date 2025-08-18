from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime
import threading
from whatsapp_auto import WhatsAppBot
import schedule
import time
import uuid
import logging
from logging.handlers import RotatingFileHandler
import signal
import sys
from queue import Queue
import atexit

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        RotatingFileHandler('whatsapp_otp_service.log', maxBytes=10485760, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global variables for OTP service
bot = None
bot_thread = None
is_bot_running = False
is_service_running = True
otp_queue = Queue()
otp_processor_thread = None

def load_config():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            'recipients': [],
            'message_templates': [],
            'scheduled_messages': [],
            'message_history': [],
            'otp_history': [],  # New: OTP service history
            'service_config': {  # New: Service configuration
                'auto_start_bot': True,
                'otp_message_template': "Your OTP verification code is: {otp_code}",
                'rate_limit_per_minute': 60,
                'max_retries': 3,
                'retry_delay': 5
            },
            'stats': {
                'total_messages': 0,
                'successful': 0,
                'failed': 0,
                'pending': 0,
                'otp_requests': 0,  # New: OTP specific stats
                'otp_successful': 0,
                'otp_failed': 0
            }
        }

def save_config(config):
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

def process_otp_queue():
    """Continuously process OTP requests from the queue"""
    global bot, is_service_running
    
    logger.info("OTP queue processor started")
    
    while is_service_running:
        try:
            if not otp_queue.empty():
                otp_request = otp_queue.get(timeout=1)
                process_single_otp(otp_request)
            else:
                time.sleep(0.1)  # Short sleep when queue is empty
        except Exception as e:
            logger.error(f"Error in OTP queue processor: {str(e)}")
            time.sleep(1)
    
    logger.info("OTP queue processor stopped")

def process_single_otp(otp_request):
    """Process a single OTP request"""
    global bot
    
    phone_number = otp_request['phone_number']
    otp_code = otp_request['otp_code']
    request_id = otp_request['request_id']
    
    config = load_config()
    service_config = config['service_config']
    
    # Format the OTP message
    message = service_config['otp_message_template'].format(otp_code=otp_code)
    
    logger.info(f"Processing OTP request {request_id} for {phone_number}")
    
    success = False
    retries = 0
    max_retries = service_config['max_retries']
    retry_delay = service_config['retry_delay']
    
    while retries < max_retries and not success:
        try:
            # Ensure bot is running
            if not bot or not bot.is_running:
                logger.warning("Bot not running, attempting to restart...")
                if not start_bot_internal():
                    logger.error("Failed to start bot for OTP processing")
                    break
            
            success = bot.send_message_to_number(phone_number, message)
            
            if success:
                logger.info(f"OTP sent successfully to {phone_number}")
            else:
                logger.warning(f"Failed to send OTP to {phone_number}, attempt {retries + 1}")
                
        except Exception as e:
            logger.error(f"Error sending OTP to {phone_number}: {str(e)}")
        
        if not success:
            retries += 1
            if retries < max_retries:
                time.sleep(retry_delay)
    
    # Update statistics and history
    config = load_config()
    otp_history_entry = {
        'request_id': request_id,
        'phone_number': phone_number,
        'otp_code': otp_code,
        'message': message,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'success' if success else 'failed',
        'retries': retries
    }
    
    config['otp_history'].append(otp_history_entry)
    config['stats']['otp_requests'] += 1
    
    if success:
        config['stats']['otp_successful'] += 1
        config['stats']['successful'] += 1
    else:
        config['stats']['otp_failed'] += 1
        config['stats']['failed'] += 1
    
    config['stats']['total_messages'] += 1
    save_config(config)
    
    return success

def start_bot_internal():
    """Internal function to start the bot"""
    global bot, is_bot_running
    
    try:
        if bot and bot.is_running:
            return True
            
        logger.info("Starting WhatsApp bot...")
        bot = WhatsAppBot()
        success = bot.start()
        
        if success:
            is_bot_running = True
            logger.info("Bot started successfully")
            return True
        else:
            logger.error("Failed to start bot")
            return False
            
    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}")
        return False

def ensure_bot_running():
    """Ensure the bot is running, start if necessary"""
    global bot, is_bot_running
    
    if not bot or not bot.is_running:
        return start_bot_internal()
    return True

# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    global is_service_running
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    is_service_running = False
    cleanup_service()
    sys.exit(0)

def cleanup_service():
    """Cleanup resources before shutdown"""
    global bot, is_bot_running, otp_processor_thread
    
    logger.info("Cleaning up service...")
    is_service_running = False
    
    if bot:
        try:
            bot.driver.quit()
        except:
            pass
        bot = None
        is_bot_running = False
    
    if otp_processor_thread and otp_processor_thread.is_alive():
        otp_processor_thread.join(timeout=5)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
atexit.register(cleanup_service)

def update_stats(config, status):
    config['stats']['total_messages'] += 1
    if status == 'success':
        config['stats']['successful'] += 1
    elif status == 'error':
        config['stats']['failed'] += 1
    else:
        config['stats']['pending'] += 1
    save_config(config)

def add_to_history(config, recipient, phone, message, status):
    history_entry = {
        'id': len(config['message_history']),
        'recipient': recipient,
        'phone': phone,
        'content': message,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': status
    }
    config['message_history'].append(history_entry)
    update_stats(config, status)
    save_config(config)

def run_scheduled_messages():
    global bot
    while is_bot_running:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except Exception as e:
            print(f"Error in scheduled messages: {str(e)}")
            time.sleep(5)  # Wait before retrying

def send_scheduled_message(recipient, template):
    if bot and bot.is_running:
        message = template['content'].format(name=recipient['name'])
        success = bot.send_message_to_number(recipient['phone'], message)
        config = load_config()
        add_to_history(config, recipient['name'], recipient['phone'], message, 
                      'success' if success else 'error')

def setup_scheduled_message(schedule_item, recipient, template):
    """Set up a scheduled message with the schedule library"""
    schedule_type = schedule_item['schedule_type']
    message = template['content'].format(name=recipient['name'])

    job = None
    if schedule_type == 'one_time':
        # Parse the datetime string to get time
        dt = datetime.fromisoformat(schedule_item['datetime'])
        job = schedule.every().day.at(dt.strftime('%H:%M')).do(
            send_scheduled_message, recipient, template
        ).tag(f"schedule_{schedule_item['id']}")
        
    elif schedule_type == 'daily':
        job = schedule.every().day.at(schedule_item['time']).do(
            send_scheduled_message, recipient, template
        ).tag(f"schedule_{schedule_item['id']}")
        
    elif schedule_type == 'weekly':
        for day in schedule_item['days']:
            job = schedule.every().week.days(day.lower()).at(schedule_item['time']).do(
                send_scheduled_message, recipient, template
            ).tag(f"schedule_{schedule_item['id']}")
            
    elif schedule_type == 'monthly':
        time_parts = schedule_item['time'].split(':')
        job = schedule.every().month.at(f"{schedule_item['day_of_month']}:{time_parts[0]}:{time_parts[1]}").do(
            send_scheduled_message, recipient, template
        ).tag(f"schedule_{schedule_item['id']}")

    return job is not None

def setup_all_schedules():
    """Set up all scheduled messages from config"""
    config = load_config()
    for schedule_item in config['scheduled_messages']:
        if schedule_item['status'] == 'active':
            try:
                recipient = config['recipients'][schedule_item['recipient_id']]
                template = config['message_templates'][schedule_item['template_id']]
                setup_scheduled_message(schedule_item, recipient, template)
            except Exception as e:
                print(f"Error setting up schedule {schedule_item['id']}: {str(e)}")

@app.route('/')
def index():
    config = load_config()
    return render_template('index.html', 
                         recipients=config['recipients'],
                         templates=config['message_templates'],
                         scheduled_messages=config['scheduled_messages'],
                         message_history=config['message_history'],
                         stats=config['stats'])

@app.route('/send_message', methods=['POST'])
def send_message():
    global bot
    try:
        # Check if bot is running, if not start it
        if not ensure_bot_running():
            return jsonify({'status': 'error', 'message': 'Failed to start bot'})
        
        phone_number = request.form['phone']
        message = request.form['message']
        
        success = bot.send_message_to_number(phone_number, message)
        
        # Add to history only once with the final status
        config = load_config()
        add_to_history(config, "Quick Send", phone_number, message, 
                      'success' if success else 'error')
        
        if success:
            return jsonify({'status': 'success', 'message': 'Message sent successfully'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to send message'})
            
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

# New OTP API Endpoints
@app.route('/api/send-otp', methods=['POST'])
def send_otp_api():
    """API endpoint to receive OTP requests and queue them for processing"""
    try:
        # Parse JSON request
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error', 
                'message': 'Invalid JSON data'
            }), 400
        
        # Validate required fields
        phone_number = data.get('phone_number')
        otp_code = data.get('otp_code')
        
        if not phone_number or not otp_code:
            return jsonify({
                'status': 'error',
                'message': 'Missing required fields: phone_number and otp_code'
            }), 400
        
        # Validate phone number format
        phone_number = ''.join(filter(str.isdigit, phone_number))
        if len(phone_number) < 10:
            return jsonify({
                'status': 'error',
                'message': 'Invalid phone number format'
            }), 400
        
        # Validate OTP code
        otp_code = str(otp_code).strip()
        if not otp_code:
            return jsonify({
                'status': 'error',
                'message': 'Invalid OTP code'
            }), 400
        
        # Create OTP request
        request_id = str(uuid.uuid4())
        otp_request = {
            'request_id': request_id,
            'phone_number': phone_number,
            'otp_code': otp_code,
            'timestamp': datetime.now().isoformat(),
            'client_ip': request.remote_addr
        }
        
        # Add to queue for processing
        otp_queue.put(otp_request)
        
        logger.info(f"OTP request queued: {request_id} for {phone_number}")
        
        return jsonify({
            'status': 'success',
            'message': 'OTP request queued for processing',
            'request_id': request_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error in send_otp_api: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@app.route('/api/otp-status/<request_id>', methods=['GET'])
def get_otp_status(request_id):
    """Get the status of a specific OTP request"""
    try:
        config = load_config()
        
        # Find the OTP request in history
        for otp_entry in config['otp_history']:
            if otp_entry['request_id'] == request_id:
                return jsonify({
                    'status': 'success',
                    'request_id': request_id,
                    'phone_number': otp_entry['phone_number'],
                    'timestamp': otp_entry['timestamp'],
                    'delivery_status': otp_entry['status'],
                    'retries': otp_entry.get('retries', 0)
                }), 200
        
        return jsonify({
            'status': 'error',
            'message': 'OTP request not found'
        }), 404
        
    except Exception as e:
        logger.error(f"Error in get_otp_status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@app.route('/api/stats', methods=['GET'])
def get_service_stats():
    """Get service statistics"""
    try:
        config = load_config()
        stats = config['stats'].copy()
        
        # Add runtime information
        stats['service_running'] = is_service_running
        stats['bot_running'] = is_bot_running
        stats['queue_size'] = otp_queue.qsize()
        stats['uptime'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({
            'status': 'success',
            'stats': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_service_stats: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@app.route('/add_recipient', methods=['POST'])
def add_recipient():
    config = load_config()
    new_recipient = {
        'id': len(config['recipients']),
        'name': request.form['name'],
        'phone': request.form['phone'],
        'notes': request.form.get('notes', '')
    }
    config['recipients'].append(new_recipient)
    save_config(config)
    return jsonify({'status': 'success'})

@app.route('/add_template', methods=['POST'])
def add_template():
    config = load_config()
    new_template = {
        'id': len(config['message_templates']),
        'name': request.form['name'],
        'content': request.form['content']
    }
    config['message_templates'].append(new_template)
    save_config(config)
    return jsonify({'status': 'success'})

@app.route('/schedule_message', methods=['POST'])
def schedule_message():
    try:
        data = request.form
        schedule_type = data.get('schedule_type')
        recipient_id = data.get('recipient')
        template_id = data.get('template')

        # Validate required fields
        if not all([schedule_type, recipient_id, template_id]):
            return jsonify({'status': 'error', 'message': 'Missing required fields'})

        # Load config and validate recipient and template IDs
        config = load_config()
        
        # Convert IDs to integers for indexing
        try:
            recipient_id = int(recipient_id)
            template_id = int(template_id)
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid recipient or template ID'})

        # Validate recipient and template exist
        if recipient_id >= len(config['recipients']):
            return jsonify({'status': 'error', 'message': 'Invalid recipient'})
        if template_id >= len(config['message_templates']):
            return jsonify({'status': 'error', 'message': 'Invalid template'})

        # Create schedule entry
        schedule_item = {
            'id': str(uuid.uuid4()),
            'recipient_id': recipient_id,
            'template_id': template_id,
            'schedule_type': schedule_type,
            'status': 'active',
            'created_at': datetime.now().isoformat()
        }

        # Add schedule type specific fields
        if schedule_type == 'one_time':
            date = data.get('date')
            time = data.get('time')
            if not date or not time:
                return jsonify({'status': 'error', 'message': 'Date and time required for one-time schedule'})
            schedule_item['datetime'] = f"{date}T{time}"
        
        elif schedule_type == 'daily':
            schedule_item['time'] = data.get('time')
            if not schedule_item['time']:
                return jsonify({'status': 'error', 'message': 'Time required for daily schedule'})
        
        elif schedule_type == 'weekly':
            schedule_item['time'] = data.get('time')
            schedule_item['days'] = request.form.getlist('days[]')
            if not schedule_item['time'] or not schedule_item['days']:
                return jsonify({'status': 'error', 'message': 'Time and days required for weekly schedule'})
        
        elif schedule_type == 'monthly':
            schedule_item['time'] = data.get('time')
            schedule_item['day_of_month'] = data.get('day_of_month')
            if not schedule_item['time'] or not schedule_item['day_of_month']:
                return jsonify({'status': 'error', 'message': 'Time and day of month required for monthly schedule'})

        # Set up the schedule if bot is running
        if is_bot_running:
            recipient = config['recipients'][recipient_id]
            template = config['message_templates'][template_id]
            if not setup_scheduled_message(schedule_item, recipient, template):
                return jsonify({'status': 'error', 'message': 'Failed to set up schedule'})
        
        # Add new schedule to config
        if 'scheduled_messages' not in config:
            config['scheduled_messages'] = []
        config['scheduled_messages'].append(schedule_item)
        
        # Save updated config
        save_config(config)

        return jsonify({'status': 'success', 'message': 'Message scheduled successfully'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/start_bot', methods=['POST'])
def start_bot():
    global bot, bot_thread, is_bot_running
    if not is_bot_running:
        try:
            success = start_bot_internal()
            
            if not success:
                return jsonify({'status': 'error', 'message': 'Failed to start bot'})
                
            # Set up all existing schedules
            setup_all_schedules()
            
            # Start a thread to monitor schedules
            bot_thread = threading.Thread(target=run_scheduled_messages)
            bot_thread.daemon = True
            bot_thread.start()
            
            return jsonify({'status': 'success', 'message': 'Bot started successfully'})
        except Exception as e:
            logger.error(f"Error starting bot: {str(e)}")
            if bot:
                try:
                    bot.driver.quit()
                except:
                    pass
            bot = None
            is_bot_running = False
            return jsonify({'status': 'error', 'message': str(e)})
    return jsonify({'status': 'error', 'message': 'Bot is already running'})

@app.route('/stop_bot', methods=['POST'])
def stop_bot():
    global bot, is_bot_running
    if is_bot_running:
        try:
            if bot:
                bot.driver.quit()
                bot = None
            is_bot_running = False
            schedule.clear()
            return jsonify({'status': 'success'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
    return jsonify({'status': 'error', 'message': 'Bot is not running'})

def initialize_service():
    """Initialize the OTP service"""
    global otp_processor_thread, is_service_running
    
    logger.info("Initializing WhatsApp OTP Service...")
    
    # Start OTP queue processor
    otp_processor_thread = threading.Thread(target=process_otp_queue)
    otp_processor_thread.daemon = True
    otp_processor_thread.start()
    
    # Auto-start bot if configured
    config = load_config()
    if config.get('service_config', {}).get('auto_start_bot', True):
        logger.info("Auto-starting WhatsApp bot...")
        if start_bot_internal():
            logger.info("Bot auto-started successfully")
        else:
            logger.warning("Failed to auto-start bot")
    
    logger.info("WhatsApp OTP Service initialized successfully")

if __name__ == '__main__':
    # Initialize the service
    initialize_service()
    
    # Run Flask app
    # For production/VPS deployment, use external WSGI server
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
