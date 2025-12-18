# SSL Certificate Fix for seminer.codinzy.com

## Problem
The site is being accessed via HTTPS, but the SSL certificate doesn't match `seminer.codinzy.com`, causing `ERR_CERT_COMMON_NAME_INVALID` error.

## Current Situation
- Port 443 is handled by a Docker proxy (likely a reverse proxy container)
- There's an nginx instance redirecting HTTP to HTTPS
- The SSL certificate is for a different domain

## Solutions

### Option 1: Access via HTTP (Temporary)
Access the site using HTTP instead of HTTPS:
- **URL**: `http://seminer.codinzy.com` (note: http, not https)
- This will work immediately without SSL issues

### Option 2: Fix SSL Certificate (Recommended)

#### If using Docker/Reverse Proxy:
1. Find the Docker container handling SSL:
   ```bash
   docker ps | grep 443
   docker exec -it <container_name> bash
   ```

2. Update the SSL certificate configuration in the container to include `seminer.codinzy.com`

#### If using Let's Encrypt:
1. Install certbot properly:
   ```bash
   apt update
   apt install -y certbot python3-certbot-nginx
   ```

2. Get SSL certificate:
   ```bash
   certbot certonly --standalone -d seminer.codinzy.com --email your-email@example.com --agree-tos --non-interactive
   ```

3. Configure nginx to use the certificate (update `/etc/nginx/conf.d/seminer.codinzy.com.conf`)

### Option 3: Disable HTTPS Redirect Temporarily
If you have access to the reverse proxy/Docker configuration:
- Disable the HTTP to HTTPS redirect temporarily
- Allow HTTP access until SSL is properly configured

## Current Configuration
- **Gunicorn**: Running on `127.0.0.1:8002` ✅
- **Nginx Config**: `/etc/nginx/conf.d/seminer.codinzy.com.conf` ✅
- **HTTP Access**: Should work at `http://seminer.codinzy.com` ✅
- **HTTPS Access**: Needs SSL certificate fix ⚠️

## Quick Test
```bash
# Test HTTP (should work)
curl -I http://seminer.codinzy.com

# Test HTTPS (will fail until SSL is fixed)
curl -I https://seminer.codinzy.com
```

## Next Steps
1. **Immediate**: Access via `http://seminer.codinzy.com` (HTTP)
2. **Short-term**: Configure proper SSL certificate for the domain
3. **Long-term**: Set up automatic SSL renewal with certbot
