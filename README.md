# WhatsApp OTP Service

A professional 24/7 WhatsApp OTP (One-Time Password) service that provides a REST API for sending verification codes via WhatsApp. Perfect for businesses needing automated OTP delivery through WhatsApp messaging.

## 🚀 Features

- **24/7 Operation**: Designed to run continuously on VPS servers
- **RESTful API**: Simple HTTP API for OTP requests
- **Queue Processing**: Handles multiple OTP requests efficiently
- **Auto-Retry**: Automatic retry mechanism for failed deliveries
- **Monitoring**: Built-in statistics and health monitoring
- **VPS Ready**: Optimized for headless server deployment
- **Rate Limiting**: Configurable rate limiting to prevent abuse
- **Logging**: Comprehensive logging for debugging and monitoring

## 📋 Requirements

- Python 3.8+
- Microsoft Edge Browser
- EdgeDriver
- Flask
- Selenium
- Valid WhatsApp account

## 🛠️ Quick Setup (Local Development)

1. **Clone and Install Dependencies**
```bash
git clone <your-repo>
cd whatsapp-automation
pip install -r requirements.txt
```

2. **Configure Service**
Edit `config.json` to customize settings:
```json
{
    "service_config": {
        "auto_start_bot": true,
        "otp_message_template": "Your OTP verification code is: {otp_code}",
        "rate_limit_per_minute": 60,
        "max_retries": 3,
        "retry_delay": 5,
        "headless_mode": false
    }
}
```

3. **Start the Service**
```bash
python app.py
```

4. **First Time Setup**
- Open http://localhost:5000 in your browser
- Click "Start Bot" to initialize WhatsApp connection
- Scan the QR code with your WhatsApp mobile app
- Service is now ready to receive API requests

## 🌐 VPS Deployment (Production)

### Automated Setup
Use the provided deployment script for Ubuntu/Debian servers:

```bash
chmod +x deploy-vps.sh
./deploy-vps.sh
```

### Manual Setup Steps

1. **Install System Dependencies**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and tools
sudo apt install -y python3 python3-pip python3-venv

# Install Microsoft Edge
curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
sudo install -o root -g root -m 644 microsoft.gpg /etc/apt/trusted.gpg.d/
sudo sh -c 'echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/trusted.gpg.d/microsoft.gpg] https://packages.microsoft.com/repos/edge stable main" > /etc/apt/sources.list.d/microsoft-edge-dev.list'
sudo apt update && sudo apt install -y microsoft-edge-stable
```

2. **Setup Application**
```bash
# Create app directory
sudo mkdir -p /opt/whatsapp-otp
sudo chown $USER:$USER /opt/whatsapp-otp
cd /opt/whatsapp-otp

# Upload your files and create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. **Create Systemd Service**
```bash
sudo cp whatsapp-otp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable whatsapp-otp
sudo systemctl start whatsapp-otp
```

4. **Setup Nginx Reverse Proxy**
```bash
sudo apt install -y nginx
# Configure nginx (see deploy-vps.sh for config)
sudo systemctl restart nginx
```

## 📡 API Usage

### Send OTP
```bash
curl -X POST http://your-domain.com/api/send-otp \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "1234567890",
    "otp_code": "123456"
  }'
```

**Response:**
```json
{
    "status": "success",
    "message": "OTP request queued for processing",
    "request_id": "uuid-string"
}
```

### Check OTP Status
```bash
curl http://your-domain.com/api/otp-status/your-request-id
```

### Get Service Statistics
```bash
curl http://your-domain.com/api/stats
```

## 🧪 Testing

Run the test suite to verify everything is working:

```bash
python test_api.py
```

The test script will:
- Check service health
- Test OTP sending
- Verify status checking
- Test error handling
- Display statistics

## 🔧 Configuration Options

### Service Configuration (`config.json`)

```json
{
    "service_config": {
        "auto_start_bot": true,              // Auto-start bot on service startup
        "otp_message_template": "Your OTP verification code is: {otp_code}",
        "rate_limit_per_minute": 60,         // Max requests per minute
        "max_retries": 3,                    // Retry attempts for failed sends
        "retry_delay": 5,                    // Delay between retries (seconds)
        "headless_mode": false,              // Run browser in headless mode
        "phone_number_prefix": "20"          // Country code prefix
    }
}
```

### Environment Variables

- `FLASK_ENV`: Set to `production` for production deployment
- `PYTHONUNBUFFERED`: Set to `1` for better logging in containers

## 📊 Monitoring & Management

### Service Management (VPS)
```bash
# Start service
whatsapp-otp-ctl start

# Stop service
whatsapp-otp-ctl stop

# Restart service
whatsapp-otp-ctl restart

# Check status
whatsapp-otp-ctl status

# View logs
whatsapp-otp-ctl logs
```

### Health Monitoring
- **API Endpoint**: `GET /api/stats` for service statistics
- **Logs**: Available in `whatsapp_otp_service.log`
- **System Logs**: `journalctl -u whatsapp-otp -f`

### Key Metrics
- Total messages sent
- Success/failure rates
- Queue size
- Bot status
- Service uptime

## 🔒 Security Considerations

1. **API Authentication**: Implement API keys or JWT tokens for production
2. **Rate Limiting**: Configure appropriate rate limits
3. **Firewall**: Restrict access to necessary ports only
4. **HTTPS**: Use SSL certificates in production
5. **Monitoring**: Set up alerting for failures

## 🐛 Troubleshooting

### Common Issues

**Bot Not Starting**
- Check WhatsApp Web session
- Re-scan QR code if needed
- Verify Edge browser installation

**Messages Not Sending**
- Verify phone number format
- Check WhatsApp connection status
- Review bot logs for errors

**High Memory Usage**
- Restart browser session periodically
- Enable headless mode for better performance
- Monitor system resources

**Queue Backup**
- Check bot status
- Verify network connectivity
- Review error logs

### Debug Mode
For debugging, set `debug=True` in `app.py` and check detailed logs.

## 📁 Project Structure

```
whatsapp-automation/
├── app.py                    # Main Flask application
├── whatsapp_auto.py         # WhatsApp bot implementation
├── wsgi.py                  # Production WSGI entry point
├── config.json              # Service configuration
├── requirements.txt         # Python dependencies
├── deploy-vps.sh           # VPS deployment script
├── whatsapp-otp.service    # Systemd service file
├── test_api.py             # API testing script
├── API_DOCUMENTATION.md    # Detailed API docs
├── templates/
│   └── index.html          # Web interface
└── whatsapp_bot_profile/   # Browser profile data
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This tool is for legitimate business use only. Ensure compliance with:
- WhatsApp Terms of Service
- Local telecommunications regulations
- Data protection laws (GDPR, etc.)
- Anti-spam regulations

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs
3. Create an issue on GitHub
4. Contact support

---

**Happy messaging! 🚀📱**
