# TCG Hunters Automation

Automation tools for TCG Hunters, including scrapers and automated tasks.

## 🚀 Deployment

The project is automatically deployed via GitHub Actions when a new tag is pushed.

### 1. Nginx Configuration

The image server and automation host are configured via Nginx. See [nginx/README.md](nginx/README.md) for detailed instructions.

### 2. Cron Jobs

To automate the Bulbapedia scraper, you need to load the crontab file on the server.

```bash
# Connect to the server
ssh user@5.39.73.113

# Load the crontab
crontab /var/www/auto.tcghunters.com/crontab

# Verify it's loaded
crontab -l
```

The cron job is set to run every 5 minutes and logs output to `/var/www/auto.tcghunters.com/logs/cron.log`.

### 3. Logs

You can monitor the scraper's execution:

```bash
tail -f /var/www/auto.tcghunters.com/logs/cron.log
```

## 🛠 Features

- **Bulbapedia Scraper**: Automatically fetches new cards from Bulbapedia based on active tasks.
- **Image Serving**: Optimized image serving with Nginx, caching, and CORS support.
- **Automated Deployment**: GitHub Actions workflow for seamless updates.
