# GitHub Actions Scheduled Domain Checking

This document explains how the automated domain checking system works in GitHub Actions and how to test and troubleshoot it.

## 🔄 **How It Works**

The system uses GitHub Actions to automatically check domain availability every hour and send Slack notifications when domains become available or when errors occur.

### Files Involved
- `.github/workflows/check-domains.yml` - Main workflow configuration
- `domains.txt` - List of domains to monitor
- `vibe check-domains` CLI command - Core checking logic

## ⏰ **Schedule Configuration**

### Automatic Schedule
- **Frequency**: Every hour at minute 0 (`0 * * * *`)
- **Trigger Type**: `scheduled`
- **Heartbeat**: Enabled (sends notification even when no domains available)
- **Command**: `vibe check-domains --scheduled --heartbeat`

### Manual Triggers
- **GitHub UI**: Actions tab → "Automated Domain Availability Checker" → "Run workflow"
- **Trigger Type**: `manual`
- **Heartbeat**: Optional (configurable via UI checkbox)
- **Command**: `vibe check-domains --manual [--heartbeat]`

## 📢 **Notification Behavior**

### When Notifications Are Sent

| Scenario | Scheduled Run | Manual Run | Manual Run + Heartbeat |
|----------|---------------|------------|------------------------|
| Domains available | ✅ Yes | ✅ Yes | ✅ Yes |
| API/System errors | ✅ Yes | ✅ Yes | ✅ Yes |
| No domains available | ✅ Yes (heartbeat) | ❌ No | ✅ Yes (heartbeat) |
| Empty domains.txt | ✅ Yes (heartbeat) | ❌ No | ✅ Yes (heartbeat) |

### Notification Content
- **Header**: Shows trigger type ("Scheduled hourly check" vs "Manual CLI Check")
- **Domain Details**: Status, expiration dates, registrar info
- **Summary**: Count of available/unavailable domains
- **Timestamp**: New York timezone for consistency

## 🧪 **Testing the System**

### 1. Test Manual Trigger (GitHub UI)
1. Go to your repository on GitHub
2. Click **Actions** tab
3. Select **"Automated Domain Availability Checker"**
4. Click **"Run workflow"**
5. Choose **"Send heartbeat notification"**: `true`
6. Click **"Run workflow"**
7. Check Slack for notification within ~2 minutes

### 2. Test Local Commands
```bash
# Test scheduled mode with heartbeat (simulates GitHub Actions)
vibe check-domains --scheduled --heartbeat

# Test manual mode without heartbeat (normal CLI usage)
vibe check-domains --manual

# Test manual mode with heartbeat
vibe check-domains --manual --heartbeat

# Test with debug output
vibe check-domains --scheduled --heartbeat --debug
```

### 3. Verify Workflow Logs
1. Go to **Actions** tab in GitHub
2. Click on the latest workflow run
3. Click **"Check Domain Availability"** job
4. Review logs for:
   - Domain check results
   - Notification status
   - Any error messages

## 🔧 **Troubleshooting**

### No Slack Notifications Received

1. **Check GitHub Secrets**
   ```
   Settings → Secrets and variables → Actions
   Verify these secrets exist:
   - WHOIS_API_KEY (your WhoisAPI.com key)
   - SLACK_WEBHOOK_URL (your Slack webhook URL)
   ```

2. **Test Slack Webhook**
   ```bash
   # Test webhook manually
   curl -X POST -H 'Content-type: application/json' \
     --data '{"text":"Test from curl"}' \
     YOUR_SLACK_WEBHOOK_URL
   ```

3. **Check Workflow Logs**
   - Look for "Domain check failed with exit code X"
   - Check for API key or webhook URL issues
   - Verify domain parsing errors

### Scheduled Jobs Not Running

1. **Verify Cron Syntax**
   - Current: `0 * * * *` (every hour at minute 0)
   - Use [Crontab Guru](https://crontab.guru/) to verify

2. **Check Repository Activity**
   - GitHub may disable workflows on inactive repositories
   - Make a commit to reactivate if needed

3. **Review GitHub Actions Limits**
   - Free tier: 2,000 minutes/month
   - Check your usage in Settings → Billing

### Webhook URL Format Issues

Ensure your Slack webhook URL follows this format:
```
https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
```

## 🚨 **Error Notifications**

If the workflow fails completely, a failure notification is automatically sent to Slack with:
- Error details
- GitHub Actions run link
- Timestamp
- Repository information

## 📋 **Monitoring Health**

### Heartbeat Notifications
- **Purpose**: Verify the system is running even when no domains are available
- **Content**: Shows "Scheduled check completed. No available domains."
- **Frequency**: Every hour (for scheduled runs)

### Success Indicators
- Regular hourly notifications in Slack
- Workflow runs showing in GitHub Actions
- No error notifications

### Red Flags
- No Slack notifications for several hours
- Error notifications in Slack
- Workflow runs failing in GitHub Actions
- Missing recent workflow runs in Actions tab

## 🔄 **Updating the Schedule**

To change the checking frequency, edit `.github/workflows/check-domains.yml`:

```yaml
on:
  schedule:
    # Examples:
    - cron: '0 */2 * * *'    # Every 2 hours
    - cron: '0 9 * * *'      # Daily at 9 AM UTC
    - cron: '0 9 * * 1-5'    # Weekdays at 9 AM UTC
```

Remember: Times are in UTC, convert accordingly for your timezone.

## 🏃‍♂️ **Quick Verification Steps**

1. **Check latest run**: Actions tab → Latest "Automated Domain Availability Checker"
2. **Verify Slack**: Look for recent domain check notifications
3. **Test manually**: Run workflow manually with heartbeat enabled
4. **Check secrets**: Ensure WHOIS_API_KEY and SLACK_WEBHOOK_URL are set
5. **Review logs**: Look for any error messages in workflow logs
