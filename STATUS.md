# Server Status

## ✅ Application Status

**Django Application**: Running
- **Gunicorn**: Running on `127.0.0.1:8002`
- **Workers**: 3
- **Status**: Active and responding

**Nginx**: Configured
- **Configuration**: `/etc/nginx/conf.d/seminer.codinzy.com.conf`
- **Domain**: `seminer.codinzy.com`
- **Proxy**: `http://127.0.0.1:8002`

## 🌐 Access Information

- **Local Access**: `http://localhost:8002`
- **Domain Access**: `http://seminer.codinzy.com` (requires DNS configuration)

## 📋 Quick Commands

### Check Gunicorn Status
```bash
ps aux | grep "gunicorn.*kg_quality" | grep -v grep
```

### Check Nginx Status
```bash
systemctl status nginx
```

### View Gunicorn Logs
```bash
tail -f /root/seminer/logs/error.log
tail -f /root/seminer/logs/access.log
```

### Restart Services
```bash
# Restart Gunicorn
pkill -f "gunicorn.*kg_quality"
cd /root/seminer && venv/bin/gunicorn --bind 127.0.0.1:8002 --workers 3 --timeout 120 --access-logfile /root/seminer/logs/access.log --error-logfile /root/seminer/logs/error.log kg_quality.wsgi:application &

# Restart Nginx
systemctl restart nginx
```

## 🔧 DNS Configuration Required

For the domain `seminer.codinzy.com` to work, ensure:
1. DNS A record points to your server's IP address
2. Nginx is running and listening on port 80
3. Firewall allows incoming connections on port 80

## 📝 Next Steps

1. **Import Data**: Import your .docx file with frameworks data
   ```bash
   cd /root/seminer
   source venv/bin/activate
   python manage.py import_document "path/to/your/document.docx"
   # Or for PDF files:
   python manage.py import_document "path/to/your/document.pdf"
   ```

2. **Create Admin User** (optional):
   ```bash
   python manage.py createsuperuser
   ```

3. **Set up SSL** (recommended for production):
   ```bash
   apt install certbot python3-certbot-nginx
   certbot --nginx -d seminer.codinzy.com
   ```
