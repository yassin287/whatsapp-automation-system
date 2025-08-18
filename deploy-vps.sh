#!/bin/bash

# WhatsApp OTP Service Deployment Script for VPS
# This script sets up the WhatsApp OTP service on a Ubuntu/Debian VPS

echo "=== WhatsApp OTP Service VPS Deployment ==="

# Update system
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python and required system packages
echo "Installing Python and system dependencies..."
sudo apt install -y python3 python3-pip python3-venv wget curl unzip

# Install Microsoft Edge for Linux
echo "Installing Microsoft Edge..."
curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
sudo install -o root -g root -m 644 microsoft.gpg /etc/apt/trusted.gpg.d/
sudo sh -c 'echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/trusted.gpg.d/microsoft.gpg] https://packages.microsoft.com/repos/edge stable main" > /etc/apt/sources.list.d/microsoft-edge-dev.list'
sudo apt update
sudo apt install -y microsoft-edge-stable

# Install EdgeDriver
echo "Installing EdgeDriver..."
EDGE_VERSION=$(microsoft-edge --version | grep -oP '\d+\.\d+\.\d+\.\d+')
wget -O edgedriver.zip "https://msedgedriver.azureedge.net/${EDGE_VERSION}/edgedriver_linux64.zip"
unzip edgedriver.zip
sudo mv msedgedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/msedgedriver
rm edgedriver.zip

# Create application directory
echo "Setting up application directory..."
sudo mkdir -p /opt/whatsapp-otp
sudo chown $USER:$USER /opt/whatsapp-otp
cp -r * /opt/whatsapp-otp/

# Create Python virtual environment
echo "Creating Python virtual environment..."
cd /opt/whatsapp-otp
python3 -m venv venv
source venv/bin/activate

# Install Python requirements
echo "Installing Python requirements..."
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn  # Production WSGI server

# Create systemd service
echo "Creating systemd service..."
sudo cp whatsapp-otp.service /etc/systemd/system/
sudo sed -i "s|/path/to/your/whatsapp-automation|/opt/whatsapp-otp|g" /etc/systemd/system/whatsapp-otp.service
sudo sed -i "s|ExecStart=/usr/bin/python3|ExecStart=/opt/whatsapp-otp/venv/bin/python|g" /etc/systemd/system/whatsapp-otp.service

# Set up Nginx reverse proxy (optional)
echo "Setting up Nginx reverse proxy..."
sudo apt install -y nginx
sudo tee /etc/nginx/sites-available/whatsapp-otp << EOF
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/whatsapp-otp /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx

# Enable and start services
echo "Enabling and starting services..."
sudo systemctl daemon-reload
sudo systemctl enable whatsapp-otp
sudo systemctl enable nginx

# Create startup script for easier management
sudo tee /usr/local/bin/whatsapp-otp-ctl << 'EOF'
#!/bin/bash
case "$1" in
    start)
        sudo systemctl start whatsapp-otp
        echo "WhatsApp OTP service started"
        ;;
    stop)
        sudo systemctl stop whatsapp-otp
        echo "WhatsApp OTP service stopped"
        ;;
    restart)
        sudo systemctl restart whatsapp-otp
        echo "WhatsApp OTP service restarted"
        ;;
    status)
        sudo systemctl status whatsapp-otp
        ;;
    logs)
        sudo journalctl -u whatsapp-otp -f
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
EOF

sudo chmod +x /usr/local/bin/whatsapp-otp-ctl

echo "=== Deployment Complete! ==="
echo ""
echo "Important Notes:"
echo "1. Update the Nginx server_name with your actual domain"
echo "2. First time setup requires QR code scan - access via VNC or screen sharing"
echo "3. Use 'whatsapp-otp-ctl start' to start the service"
echo "4. Use 'whatsapp-otp-ctl logs' to view logs"
echo "5. Service will automatically restart on boot"
echo ""
echo "API Endpoints:"
echo "- POST /api/send-otp - Send OTP requests"
echo "- GET /api/otp-status/<request_id> - Check OTP status"
echo "- GET /api/stats - Service statistics"
echo ""
echo "Next steps:"
echo "1. Run 'whatsapp-otp-ctl start' to start the service"
echo "2. Access the web interface to scan WhatsApp QR code"
echo "3. Test the API endpoints"
