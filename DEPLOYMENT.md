# Deployment Guide for seminer.codinzy.com

## Current Status

The Django application is running with Gunicorn on port 8000, accessible at `http://seminer.codinzy.com` (assuming DNS is configured).

## Server Setup

### 1. Current Running Server

The server is currently running via Gunicorn. To check status:
```bash
ps aux | grep gunicorn
```

To stop the current server:
```bash
pkill -f gunicorn
```

### 2. Using Systemd Service (Recommended for Production)

For persistent service that starts on boot:

```bash
# Copy the service file
sudo cp /root/seminer/gunicorn.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start the service
sudo systemctl enable gunicorn.service
sudo systemctl start gunicorn.service

# Check status
sudo systemctl status gunicorn.service

# View logs
sudo journalctl -u gunicorn.service -f
```

### 3. Nginx Configuration (Recommended)

For production, use Nginx as a reverse proxy:

```bash
# Install Nginx (if not already installed)
sudo apt update
sudo apt install nginx

# Copy the configuration
sudo cp /root/seminer/nginx_config.conf /etc/nginx/sites-available/seminer.codinzy.com

# Create symlink
sudo ln -s /etc/nginx/sites-available/seminer.codinzy.com /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### 4. DNS Configuration

Make sure your DNS is configured to point `seminer.codinzy.com` to your server's IP address:
- Add an A record: `seminer.codinzy.com` → `YOUR_SERVER_IP`

### 5. SSL Certificate (Optional but Recommended)

For HTTPS, install Certbot and get a free SSL certificate:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d seminer.codinzy.com
```

Then update the nginx config to use HTTPS (see nginx_config.conf for HTTPS section).

## Manual Server Start

If you prefer to start manually:

```bash
cd /root/seminer
source venv/bin/activate
gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 kg_quality.wsgi:application
```

Or use the run script:
```bash
./run.sh
```

## Monitoring

- Check Gunicorn logs: `/root/seminer/logs/error.log` and `/root/seminer/logs/access.log`
- Check Django logs: Check console output or configure logging in settings.py
- Monitor server: `htop` or `top` to check resource usage

## Troubleshooting

1. **Port 8000 already in use**: Change the port in gunicorn command or kill the existing process
2. **502 Bad Gateway**: Check if Gunicorn is running and Nginx can reach it
3. **Static files not loading**: Run `python manage.py collectstatic` again
4. **Database errors**: Check database permissions and run migrations if needed

## Updating the Application

After making changes:

```bash
cd /root/seminer
source venv/bin/activate

# Pull latest code (if using git)
git pull

# Run migrations if models changed
python manage.py migrate

# Collect static files if changed
python manage.py collectstatic --noinput

# Restart Gunicorn
sudo systemctl restart gunicorn.service
# OR if running manually:
pkill -f gunicorn
gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 kg_quality.wsgi:application &
```
