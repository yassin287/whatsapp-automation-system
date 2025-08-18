# WhatsApp OTP Service - Hostinger VPS Setup Guide

## Prerequisites
- Hostinger VPS with Ubuntu 20.04+ 
- FastPanel installed
- SSH access to your VPS
- Domain name (optional but recommended)

## Step 1: Initial VPS Setup

### 1.1 Connect to Your VPS
```bash
ssh root@your-vps-ip
```

### 1.2 Update System
```bash
apt update && apt upgrade -y
```

### 1.3 Install Required System Packages
```bash
# Install Python and system dependencies
apt install -y python3 python3-pip python3-venv wget curl unzip git

# Install Node.js (required for some dependencies)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
apt install -y nodejs
```

## Step 2: Install Microsoft Edge Browser

### 2.1 Add Microsoft Repository
```bash
# Add Microsoft GPG key
curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
install -o root -g root -m 644 microsoft.gpg /etc/apt/trusted.gpg.d/

# Add Microsoft Edge repository
sh -c 'echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/trusted.gpg.d/microsoft.gpg] https://packages.microsoft.com/repos/edge stable main" > /etc/apt/sources.list.d/microsoft-edge-dev.list'

# Update and install Edge
apt update
apt install -y microsoft-edge-stable
```

### 2.2 Install EdgeDriver
```bash
# Get Edge version
EDGE_VERSION=$(microsoft-edge --version | grep -oP '\d+\.\d+\.\d+\.\d+')

# Download and install EdgeDriver
wget -O edgedriver.zip "https://msedgedriver.azureedge.net/${EDGE_VERSION}/edgedriver_linux64.zip"
unzip edgedriver.zip
mv msedgedriver /usr/local/bin/
chmod +x /usr/local/bin/msedgedriver
rm edgedriver.zip
```

## Step 3: Setup Application Directory

### 3.1 Create Application User (Security Best Practice)
```bash
# Create dedicated user for the application
useradd -m -s /bin/bash whatsapp-otp
usermod -aG sudo whatsapp-otp

# Create application directory
mkdir -p /opt/whatsapp-otp
chown whatsapp-otp:whatsapp-otp /opt/whatsapp-otp
```

### 3.2 Upload Application Files
You can upload files using SCP, SFTP, or Git:

**Option A: Using SCP (from your local machine)**
```bash
scp -r "d:\projects\whatsapp automation\*" root@your-vps-ip:/opt/whatsapp-otp/
```

**Option B: Using Git**
```bash
cd /opt/whatsapp-otp
git clone https://github.com/yourusername/whatsapp-automation-system.git .
```

**Option C: Manual upload via FastPanel**
- Use FastPanel's file manager to upload the project files

## Step 4: Python Environment Setup

### 4.1 Switch to Application User
```bash
su - whatsapp-otp
cd /opt/whatsapp-otp
```

### 4.2 Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4.3 Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 5: Configure the Service

### 5.1 Update Configuration
```bash
# Edit config.json with your settings
nano config.json
```

Make sure your config.json has proper service settings:
```json
{
  "service_config": {
    "auto_start_bot": true,
    "otp_message_template": "Your OTP verification code is: {otp_code}",
    "rate_limit_per_minute": 60,
    "max_retries": 3,
    "retry_delay": 5
  }
}
```

### 5.2 Test the Application
```bash
# Test if the application starts
source venv/bin/activate
python app.py
```

## Step 6: Setup Systemd Service (Production)

### 6.1 Create Service File
```bash
sudo nano /etc/systemd/system/whatsapp-otp.service
```

Add this content:
```ini
[Unit]
Description=WhatsApp OTP Service
After=network.target

[Service]
Type=simple
User=whatsapp-otp
Group=whatsapp-otp
WorkingDirectory=/opt/whatsapp-otp
Environment=PATH=/opt/whatsapp-otp/venv/bin
ExecStart=/opt/whatsapp-otp/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 --timeout 120 wsgi:app
Restart=always
RestartSec=10

# Environment variables
Environment=FLASK_ENV=production
Environment=DISPLAY=:99

[Install]
WantedBy=multi-user.target
```

### 6.2 Enable and Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable whatsapp-otp
sudo systemctl start whatsapp-otp

# Check status
sudo systemctl status whatsapp-otp
```

## Step 7: Setup Virtual Display (Required for Selenium)

### 7.1 Install Xvfb
```bash
sudo apt install -y xvfb
```

### 7.2 Create Xvfb Service
```bash
sudo nano /etc/systemd/system/xvfb.service
```

Add this content:
```ini
[Unit]
Description=X Virtual Frame Buffer Service
After=network.target

[Service]
ExecStart=/usr/bin/Xvfb :99 -screen 0 1024x768x24
Restart=on-failure
RestartSec=3
User=whatsapp-otp

[Install]
WantedBy=multi-user.target
```

### 7.3 Enable Xvfb Service
```bash
sudo systemctl enable xvfb
sudo systemctl start xvfb
```

## Step 8: Setup Nginx Reverse Proxy (via FastPanel)

### 8.1 In FastPanel Dashboard:
1. Go to "Websites" section
2. Create a new website with your domain
3. Enable SSL certificate (Let's Encrypt)
4. Configure reverse proxy

### 8.2 Nginx Configuration
Add this to your site's nginx configuration:
```nginx
location / {
    proxy_pass http://127.0.0.1:5000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
}

# API endpoint optimization
location /api/ {
    proxy_pass http://127.0.0.1:5000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}
```

## Step 9: Security & Firewall Setup

### 9.1 Configure UFW Firewall
```bash
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow from 127.0.0.1 to any port 5000
```

### 9.2 Secure the Application
```bash
# Set proper file permissions
sudo chown -R whatsapp-otp:whatsapp-otp /opt/whatsapp-otp
sudo chmod 750 /opt/whatsapp-otp
sudo chmod 640 /opt/whatsapp-otp/config.json
```

## Step 10: Monitoring & Logging

### 10.1 Setup Log Rotation
```bash
sudo nano /etc/logrotate.d/whatsapp-otp
```

Add:
```
/opt/whatsapp-otp/*.log {
    daily
    missingok
    rotate 7
    compress
    notifempty
    create 644 whatsapp-otp whatsapp-otp
    postrotate
        systemctl reload whatsapp-otp
    endscript
}
```

### 10.2 Monitor Service Logs
```bash
# View service logs
sudo journalctl -u whatsapp-otp -f

# View application logs
tail -f /opt/whatsapp-otp/whatsapp_otp_service.log
```

## Step 11: Testing the Service

### 11.1 Test API Endpoints
```bash
# Test OTP sending
curl -X POST "https://yourdomain.com/api/send-otp" \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "201234567890", "otp_code": "123456"}'

# Check service stats
curl "https://yourdomain.com/api/stats"
```

### 11.2 Initial WhatsApp Web Login
1. Access your domain in browser
2. The service will open WhatsApp Web
3. Scan QR code with your phone
4. Service will maintain the session

## Troubleshooting

### Common Issues:

**1. Edge Driver Not Found**
```bash
# Reinstall EdgeDriver
EDGE_VERSION=$(microsoft-edge --version | grep -oP '\d+\.\d+\.\d+\.\d+')
wget -O edgedriver.zip "https://msedgedriver.azureedge.net/${EDGE_VERSION}/edgedriver_linux64.zip"
unzip edgedriver.zip
sudo mv msedgedriver /usr/local/bin/
```

**2. Display Issues**
```bash
# Check if Xvfb is running
sudo systemctl status xvfb

# Set display environment
export DISPLAY=:99
```

**3. Permission Issues**
```bash
# Fix ownership
sudo chown -R whatsapp-otp:whatsapp-otp /opt/whatsapp-otp
```

**4. Service Won't Start**
```bash
# Check logs
sudo journalctl -u whatsapp-otp -n 50
```

## Maintenance Commands

```bash
# Restart service
sudo systemctl restart whatsapp-otp

# Update application
cd /opt/whatsapp-otp
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart whatsapp-otp

# View logs
sudo journalctl -u whatsapp-otp -f
```

## Performance Optimization

### For High-Volume OTP Service:
1. **Increase worker processes** in gunicorn config
2. **Setup Redis** for queue management (optional)
3. **Monitor memory usage** and adjust as needed
4. **Setup automatic backups** for config.json and logs

## Support

If you encounter issues:
1. Check service logs: `sudo journalctl -u whatsapp-otp -f`
2. Check application logs: `tail -f /opt/whatsapp-otp/whatsapp_otp_service.log`
3. Verify all dependencies are installed
4. Ensure proper file permissions

Your WhatsApp OTP service should now be running 24/7 on your Hostinger VPS!
