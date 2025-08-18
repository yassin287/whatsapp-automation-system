# WhatsApp OTP Service API Documentation

## Overview
This WhatsApp OTP Service provides a RESTful API for sending OTP (One-Time Password) verification codes via WhatsApp messages. The service runs 24/7 and is designed for VPS deployment.

## Base URL
```
http://your-domain.com
# or for local testing:
http://localhost:5000
```

## API Endpoints

### 1. Send OTP
Send an OTP verification code to a phone number via WhatsApp.

**Endpoint:** `POST /api/send-otp`

**Request Body:**
```json
{
    "phone_number": "1234567890",
    "otp_code": "123456"
}
```

**Response:**
```json
{
    "status": "success",
    "message": "OTP request queued for processing",
    "request_id": "uuid-string"
}
```

**Error Response:**
```json
{
    "status": "error",
    "message": "Missing required fields: phone_number and otp_code"
}
```

### 2. Check OTP Status
Check the delivery status of a specific OTP request.

**Endpoint:** `GET /api/otp-status/{request_id}`

**Response:**
```json
{
    "status": "success",
    "request_id": "uuid-string",
    "phone_number": "201234567890",
    "timestamp": "2025-04-03 12:30:45",
    "delivery_status": "success",
    "retries": 0
}
```

### 3. Service Statistics
Get overall service statistics and health information.

**Endpoint:** `GET /api/stats`

**Response:**
```json
{
    "status": "success",
    "stats": {
        "total_messages": 150,
        "successful": 145,
        "failed": 5,
        "pending": 2,
        "otp_requests": 130,
        "otp_successful": 125,
        "otp_failed": 3,
        "service_running": true,
        "bot_running": true,
        "queue_size": 2,
        "uptime": "2025-04-03 12:30:45"
    }
}
```

## Phone Number Format
- The service automatically formats phone numbers
- Egyptian numbers: If number doesn't start with "20", it will be prefixed automatically
- International format: Include country code (e.g., "201234567890" for Egypt)

## Rate Limiting
- Default: 60 requests per minute
- Configurable in service settings

## Error Handling
- The service implements automatic retry with exponential backoff
- Default: 3 retries with 5-second delay
- Failed requests are logged for debugging

## Message Template
Default OTP message template:
```
Your OTP verification code is: {otp_code}
```

This can be customized in the service configuration.

## HTTP Status Codes
- `200 OK`: Request successful
- `400 Bad Request`: Invalid request data
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

## Examples

### cURL Examples

**Send OTP:**
```bash
curl -X POST http://localhost:5000/api/send-otp \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "1234567890",
    "otp_code": "123456"
  }'
```

**Check Status:**
```bash
curl http://localhost:5000/api/otp-status/your-request-id
```

**Get Stats:**
```bash
curl http://localhost:5000/api/stats
```

### Python Example
```python
import requests
import json

# Send OTP
url = "http://localhost:5000/api/send-otp"
data = {
    "phone_number": "1234567890",
    "otp_code": "123456"
}

response = requests.post(url, json=data)
result = response.json()

if result["status"] == "success":
    request_id = result["request_id"]
    print(f"OTP queued with ID: {request_id}")
    
    # Check status
    status_url = f"http://localhost:5000/api/otp-status/{request_id}"
    status_response = requests.get(status_url)
    status_result = status_response.json()
    print(f"Delivery status: {status_result['delivery_status']}")
else:
    print(f"Error: {result['message']}")
```

### JavaScript Example
```javascript
// Send OTP
async function sendOTP(phoneNumber, otpCode) {
    const response = await fetch('/api/send-otp', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            phone_number: phoneNumber,
            otp_code: otpCode
        })
    });
    
    const result = await response.json();
    return result;
}

// Usage
sendOTP('1234567890', '123456')
    .then(result => {
        if (result.status === 'success') {
            console.log('OTP sent:', result.request_id);
        } else {
            console.error('Error:', result.message);
        }
    });
```

## Deployment Notes

### VPS Setup
1. Use the provided `deploy-vps.sh` script for automated setup
2. Ensure Microsoft Edge is installed on the server
3. For headless operation, set `headless_mode: true` in config
4. Initial WhatsApp QR code scan required (use VNC or screen sharing)

### Monitoring
- Logs are available via `journalctl -u whatsapp-otp -f`
- Service management: `whatsapp-otp-ctl {start|stop|restart|status|logs}`
- Web interface available for manual testing and monitoring

### Security Considerations
- Run behind a reverse proxy (Nginx/Apache)
- Use HTTPS in production
- Implement API authentication if needed
- Monitor rate limits and abuse

### Troubleshooting
1. **Bot not starting**: Check WhatsApp Web session, re-scan QR if needed
2. **Messages not sending**: Verify phone number format and WhatsApp connection
3. **High memory usage**: Restart browser session periodically
4. **Queue backup**: Check bot status and connection health
