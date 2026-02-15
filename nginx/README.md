# Nginx Image Server Configuration

This directory contains the Nginx virtual host configuration for serving images from the TCG Hunters automation project.

## Quick Setup

### 1. Deploy the configuration to your server

```bash
# Copy the configuration file to Nginx sites-available
sudo cp img.conf /etc/nginx/sites-available/img.tcghunters.com

# Create a symbolic link to enable the site
sudo ln -s /etc/nginx/sites-available/img.tcghunters.com /etc/nginx/sites-enabled/

# Test the Nginx configuration
sudo nginx -t

# Reload Nginx to apply changes
sudo systemctl reload nginx
```

### 2. Set up the image directory

```bash
# Create the directory structure on your server
sudo mkdir -p /var/www/tcg-hunters-automation/public/img/tmp

# Set proper permissions
sudo chown -R www-data:www-data /var/www/tcg-hunters-automation/public
sudo chmod -R 755 /var/www/tcg-hunters-automation/public
```

### 3. Update DNS

Point your domain (e.g., `img.tcghunters.com`) to your server IP address:
- A record: `img.tcghunters.com` → `5.39.73.113`

### 4. (Optional) Set up SSL with Let's Encrypt

```bash
# Install Certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx

# Obtain and install SSL certificate
sudo certbot --nginx -d img.tcghunters.com

# Certbot will automatically configure SSL and set up auto-renewal
```

## Configuration Details

### Features Included

- **CORS Support**: Allows cross-origin requests from any domain (adjust as needed)
- **Caching**: Images are cached for 30 days, temporary images for 1 day
- **Security Headers**: Prevents clickjacking and MIME-type sniffing
- **Directory Listing**: Enabled by default (can be disabled)
- **Gzip Compression**: Enabled for SVG files
- **Access Control**: Blocks hidden files, backups, and script execution

### Directory Structure

```
/var/www/tcg-hunters-automation/public/
└── img/
    ├── tmp/          # Temporary images (1 day cache)
    └── ...           # Other image directories
```

### Customization

#### Change the domain name
Edit `server_name` in the configuration:
```nginx
server_name your-domain.com;
```

#### Disable directory listing
Remove or comment out these lines:
```nginx
autoindex on;
autoindex_exact_size off;
autoindex_localtime on;
```

#### Restrict CORS to specific domains
Replace the wildcard with your domain:
```nginx
add_header Access-Control-Allow-Origin "https://tcghunters.com" always;
```

#### Adjust cache duration
Modify the `expires` directive:
```nginx
expires 7d;  # 7 days
```

## Deployment with GitHub Actions

To automate deployment, you can add this to your `.github/workflows/deploy.yaml`:

```yaml
- name: Deploy Nginx configuration
  run: |
    scp nginx/img.conf user@server:/tmp/img.conf
    ssh user@server 'sudo mv /tmp/img.conf /etc/nginx/sites-available/img.tcghunters.com && sudo nginx -t && sudo systemctl reload nginx'
```

## Testing

After deployment, test the configuration:

```bash
# Test from command line
curl -I http://img.tcghunters.com/img/tmp/test-image.jpg

# Expected response headers:
# HTTP/1.1 200 OK
# Access-Control-Allow-Origin: *
# Cache-Control: public
# Expires: ...
```

## Troubleshooting

### 403 Forbidden
- Check file permissions: `sudo chmod -R 755 /var/www/tcg-hunters-automation/public`
- Check ownership: `sudo chown -R www-data:www-data /var/www/tcg-hunters-automation/public`

### 404 Not Found
- Verify the file exists in the correct directory
- Check the root path in the Nginx configuration

### Configuration test fails
- Run `sudo nginx -t` to see detailed error messages
- Check for syntax errors in the configuration file

## Logs

View access and error logs:

```bash
# Access log
sudo tail -f /var/log/nginx/img-access.log

# Error log
sudo tail -f /var/log/nginx/img-error.log
```
