# GitHub Actions Scheduled Domain Checking Setup Guide

This document provides a comprehensive guide for setting up, monitoring, and troubleshooting the automated domain availability checking system using GitHub Actions.

## Overview

The system runs automatically every hour to check domain availability and sends Slack notifications when domains become available. It also provides heartbeat notifications to confirm the automation is working correctly.

## Configuration

### Required Secrets

Configure these secrets in your GitHub repository at `Settings > Secrets and variables > Actions`:

- **`WHOIS_API_KEY`**: Your WHOIS API key for domain lookups
- **`SLACK_WEBHOOK_URL`**: Your Slack incoming webhook URL for notifications

### Workflow Schedule

The automated check runs **every hour** at minute 0 (e.g., 12:00, 1:00, 2:00, etc.).

**Cron Schedule:** `0 * * * *`

To modify the schedule, edit `.github/workflows/check-domains.yml`:

```yaml
schedule:
  # Run every hour at minute 0
  - cron: '0 * * * *'
```

**Common Schedule Examples:**
- Every 30 minutes: `'*/30 * * * *'`
- Every 2 hours: `'0 */2 * * *'`
- Daily at 9 AM UTC: `'0 9 * * *'`
- Weekdays only at 9 AM UTC: `'0 9 * * 1-5'`

## Notification Behavior

### When Notifications Are Sent

| Scenario | Regular Mode | Heartbeat Mode |
|----------|-------------|----------------|
| ✅ Available domains found | ✅ Always | ✅ Always |
| 🚨 System errors occurred | ✅ Always | ✅ Always |
| 📭 No domains available | ❌ No notification | ✅ Sends heartbeat |
| 📄 Empty domains.txt | ❌ No notification | ✅ Sends heartbeat |

### Heartbeat Notifications

Heartbeat mode (`--heartbeat`) ensures you receive notifications even when no domains are available, confirming that the automation is running correctly.

**Scheduled runs automatically use heartbeat mode** to provide monitoring visibility.

## Testing the System

### 1. Local Testing

Test the CLI commands locally to verify functionality:

```bash
# Test scheduled run with heartbeat (simulates GitHub Actions)
vibe check-domains --scheduled --heartbeat

# Test manual run without heartbeat
vibe check-domains --manual

# Test with empty domains list
mv domains.txt domains.txt.backup
touch domains.txt
vibe check-domains --scheduled --heartbeat
mv domains.txt.backup domains.txt
```

### 2. Manual GitHub Actions Testing

Test the workflow manually through GitHub's web interface:

1. Go to `Actions` tab in your repository
2. Select `Automated Domain Availability Checker`
3. Click `Run workflow`
4. Choose whether to send heartbeat notification
5. Click `Run workflow`

### 3. Expected Outputs

**Console Output (Scheduled):**
```
🤖 Scheduled run detected - trigger_type: scheduled
🔧 Environment check:
   WHOIS_API_KEY: SET
   SLACK_WEBHOOK_URL: SET
💓 Heartbeat mode enabled - will send notification regardless of results
🔍 Checking domain availability...
⚠️  No domains found to check.
💓 Sending heartbeat notification for empty domain list...
💓 Heartbeat notification sent (scheduled trigger)
```

**Slack Message (Heartbeat):**
```
🤖 Domain Tracker: Scheduled Hourly Check

📊 No domains currently being monitored

🕐 Check completed at: 2024-01-15 14:00:00 UTC
🔄 Trigger: Scheduled hourly check
💓 This is a heartbeat notification confirming the automation is running correctly.
```

## Monitoring & Health Checks

### 1. Workflow Status

Monitor workflow health in several ways:

- **Actions Tab**: Check recent workflow runs at `github.com/yourusername/domain-tracker/actions`
- **Slack Notifications**: Receive both success and failure notifications
- **Workflow Badges**: Add status badges to your README

### 2. Understanding Logs

**In GitHub Actions logs, look for:**

✅ **Success Indicators:**
- `🤖 Scheduled run detected`
- `WHOIS_API_KEY: SET` and `SLACK_WEBHOOK_URL: SET`
- `💓 Heartbeat notification sent (scheduled trigger)`
- `Scheduled domain check completed successfully`

❌ **Warning Signs:**
- `WHOIS_API_KEY: MISSING` or `SLACK_WEBHOOK_URL: MISSING`
- `vibe command not found in PATH`
- `Domain check failed with exit code 1`
- `Failed to send Slack notification`

### 3. Fallback Monitoring

The workflow includes a completion notification that confirms the job ran successfully:

```
✅ GitHub Actions: Scheduled domain check completed

🕐 Workflow executed at: 2024-01-15 14:00:00 UTC
📊 This message confirms the scheduled job is running correctly.

This is a fallback notification to verify automation health.
```

## Troubleshooting

### Issue: No Slack Messages Received

**Possible Causes & Solutions:**

1. **Missing API Secrets**
   - Check: Repository Settings > Secrets and variables > Actions
   - Verify: `WHOIS_API_KEY` and `SLACK_WEBHOOK_URL` are set
   - Test: Run manual workflow to see error messages

2. **Workflow Not Running**
   - Check: `.github/workflows/check-domains.yml` exists in `main` branch
   - Verify: Cron syntax is correct and quoted
   - Test: Trigger manual run from Actions tab

3. **Invalid Slack Webhook**
   - Test: Send test message with `curl` command
   - Verify: Webhook URL format and permissions
   - Check: Slack app configuration

### Issue: Workflow Fails

**Common Error Scenarios:**

1. **Installation Error:**
   ```
   ERROR: Could not find a version that satisfies the requirement domain-drop-tracker
   ```
   **Solution:** Check `pyproject.toml` and dependencies

2. **Command Not Found:**
   ```
   vibe: command not found
   ```
   **Solution:** Verify package installation and console script setup

3. **Exit Code 1:**
   ```
   Domain check failed with exit code 1
   ```
   **Solution:** Check logs for specific error messages

### Issue: Scheduled Time Not Working

**Diagnostics:**

1. **Verify Cron Syntax:**
   - Must be in quotes: `cron: '0 * * * *'`
   - Uses UTC timezone
   - GitHub Actions may have 5-10 minute delays

2. **Check Repository Settings:**
   - Actions must be enabled
   - Workflow file must be in `main` branch
   - No branch protection blocking Actions

### Manual Debugging Steps

1. **Check Workflow Configuration:**
   ```bash
   # Verify cron syntax
   cat .github/workflows/check-domains.yml | grep -A2 schedule
   ```

2. **Test Local Environment:**
   ```bash
   # Test CLI functionality
   export WHOIS_API_KEY="your-api-key"
   export SLACK_WEBHOOK_URL="your-webhook-url"
   vibe check-domains --scheduled --heartbeat --debug
   ```

3. **Verify GitHub Secrets:**
   - Go to repository Settings > Secrets and variables > Actions
   - Confirm secrets are set (you can't view values, only confirm they exist)

4. **Check Recent Actions:**
   - Go to Actions tab
   - Look for failed or cancelled workflows
   - Review logs for error details

## Customization

### Modifying Notification Content

Edit the notification logic in `src/domain_tracker/core.py` and `src/domain_tracker/slack_notifier.py`.

### Changing Check Frequency

Modify the cron schedule in `.github/workflows/check-domains.yml`:

```yaml
schedule:
  - cron: '0 */6 * * *'  # Every 6 hours
```

### Adding More Domains

Add domains to `domains.txt`, one per line:

```
example.com
anotherdomain.org
coolsite.net
```

### Disabling Heartbeat

To disable heartbeat notifications, remove the `--heartbeat` flag from the scheduled workflow step.

## Security Considerations

1. **API Key Protection**: Never commit API keys to the repository
2. **Webhook Security**: Use specific Slack webhook URLs, not general bot tokens
3. **Repository Access**: Limit who can modify GitHub Actions workflows
4. **Secret Rotation**: Regularly rotate API keys and webhook URLs

## Support

If you encounter issues not covered in this guide:

1. Check the GitHub Actions logs for detailed error messages
2. Test the CLI commands locally with debug mode enabled
3. Verify all required secrets are properly configured
4. Review recent changes to workflow files or dependencies

## Quick Reference

**Manual Test Commands:**
```bash
# Local test with debugging
vibe check-domains --scheduled --heartbeat --debug

# Manual GitHub Actions trigger
# Go to: github.com/yourusername/domain-tracker/actions
# Click: "Run workflow" on "Automated Domain Availability Checker"
```

**Important Files:**
- `.github/workflows/check-domains.yml` - Workflow configuration
- `domains.txt` - List of domains to monitor
- `src/domain_tracker/cli.py` - CLI command implementation
- `src/domain_tracker/core.py` - Core checking logic
