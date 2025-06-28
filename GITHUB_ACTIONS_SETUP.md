# GitHub Actions Setup for Domain Tracker

This document explains how to configure automated domain checking using GitHub Actions.

## Overview

The GitHub Actions workflow (`.github/workflows/check-domains.yml`) automatically runs every hour to:
- Check domain availability from `domains.txt`
- Send Slack notifications for available domains
- Alert you via Slack if the automation fails

## Required GitHub Secrets

You must configure these secrets in your GitHub repository for the automation to work:

### 1. `WHOIS_API_KEY`
- **Purpose**: WhoisXML API authentication
- **How to get**: Sign up at [WhoisXML API](https://whoisxml.whoisapi.com/)
- **Format**: Your API key string (e.g., `at_1234567890abcdef...`)

### 2. `SLACK_WEBHOOK_URL`
- **Purpose**: Send notifications to Slack
- **How to get**: Create a Slack webhook in your workspace
- **Format**: Full webhook URL (e.g., `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX`)

## Setting Up GitHub Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret:
   ```
   Name: WHOIS_API_KEY
   Value: your_whoisxml_api_key_here
   ```
   ```
   Name: SLACK_WEBHOOK_URL
   Value: your_slack_webhook_url_here
   ```

## Workflow Details

### Schedule
- **Frequency**: Every hour at minute 0 (e.g., 1:00 PM, 2:00 PM, etc.)
- **Cron Expression**: `0 * * * *`
- **Timezone**: UTC (GitHub Actions default)

### What It Does
1. **Checks out your repository** with latest `domains.txt`
2. **Sets up Python 3.11** with pip caching for faster builds
3. **Installs dependencies** from `pyproject.toml`
4. **Runs domain checking** using `vibe check-domains`
5. **Sends Slack alerts** for available domains (normal operation)
6. **Notifies on failure** if the workflow encounters errors

### Error Handling
- **Timeout**: Workflow will timeout after 10 minutes
- **Failure Notifications**: Automatic Slack alert with:
  - Error description
  - Workflow run ID for debugging
  - Timestamp of failure
  - Link to GitHub Actions logs

## Testing the Workflow

### Manual Trigger
You can test the workflow manually without waiting for the scheduled run:

1. Go to **Actions** tab in your GitHub repository
2. Select **Automated Domain Availability Checker**
3. Click **Run workflow** → **Run workflow**
4. Monitor the execution in real-time

### Local Testing
Test the CLI command locally before relying on automation:

```bash
# Set up environment variables
export WHOIS_API_KEY="your_api_key"
export SLACK_WEBHOOK_URL="your_webhook_url"

# Test the command
vibe check-domains
```

## Monitoring

### GitHub Actions Logs
- View detailed logs in the **Actions** tab
- Each step shows individual progress and errors
- Logs are retained for 90 days by default

### Slack Notifications
- **Success**: Normal domain availability alerts (same as manual CLI)
- **Failure**: Special workflow failure alerts with debugging info

### Expected Behavior
- **Available Domain Found**: Slack message "✅ Domain available: example.com"
- **No Available Domains**: No Slack message (silent success)
- **Workflow Failure**: Slack message "🚨 Domain Tracker GitHub Action Failed..."

## Troubleshooting

### Common Issues

**"Secret not found" errors:**
- Verify secret names match exactly: `WHOIS_API_KEY`, `SLACK_WEBHOOK_URL`
- Ensure secrets are set at repository level, not organization level

**WhoisXML API errors:**
- Check API key validity and account limits
- Verify API key has sufficient credits

**Slack webhook errors:**
- Test webhook URL manually with curl
- Ensure webhook is active in Slack workspace

**Installation failures:**
- Check `pyproject.toml` syntax
- Verify all dependencies are available on PyPI

### Debug Commands

Test individual components:

```bash
# Test WhoisXML API access
curl "https://www.whoisxml.com/whoisserver/WhoisService?apiKey=YOUR_KEY&domainName=example.com&outputFormat=JSON"

# Test Slack webhook
curl -X POST -H 'Content-type: application/json' --data '{"text":"Test message"}' YOUR_WEBHOOK_URL

# Test CLI installation
pip install -e .
vibe --help
```

## Customization

### Change Schedule
Modify the cron expression in `.github/workflows/check-domains.yml`:

```yaml
schedule:
  # Every 30 minutes
  - cron: '*/30 * * * *'
  
  # Daily at 9 AM UTC
  - cron: '0 9 * * *'
  
  # Business hours only (9 AM - 5 PM UTC, weekdays)
  - cron: '0 9-17 * * 1-5'
```

### Add More Notifications
You can extend the workflow to send notifications to multiple channels or services by adding steps.

### Custom Domain Lists
The workflow reads from `domains.txt` in the repository root. Update this file to change which domains are monitored.

## Security Considerations

- **Never commit API keys or webhook URLs to the repository**
- **Use GitHub Secrets for all sensitive data**
- **Regularly rotate API keys and webhooks**
- **Monitor usage to detect unauthorized access**

## Cost Considerations

- **GitHub Actions**: Free tier includes 2,000 minutes/month
- **WhoisXML API**: Check your account limits and pricing
- **Slack**: Webhooks are free for most Slack plans

At hourly checking, you'll use approximately:
- **GitHub Actions**: ~30 minutes/month (well within free tier)
- **WhoisXML API**: ~720 API calls/month per domain 