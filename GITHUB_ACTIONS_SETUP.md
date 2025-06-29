# GitHub Actions Scheduled Domain Checking Setup Guide

This document provides a comprehensive guide for setting up, monitoring, and troubleshooting the automated domain availability checking system using GitHub Actions.

## Overview

The system runs automatically every hour to check domain availability and sends Slack notifications when domains become available. It also provides heartbeat notifications to confirm the automation is working correctly.

## ⏰ **Important: GitHub Actions Timing Behavior**

### **Expected Scheduling Delays**
The workflow is configured to run at the top of each hour (`cron: '0 * * * *'`), but **GitHub Actions does not guarantee precise timing**:

- **Typical delays**: 5-30 minutes past the scheduled time
- **Peak time delays**: Can exceed 30 minutes during high GitHub usage
- **Best-effort scheduling**: GitHub treats cron schedules as approximate, not exact

### **Why Delays Occur**
1. **Resource queuing**: GitHub queues workflows based on runner availability
2. **Infrastructure load**: High demand can delay workflow execution
3. **Repository activity**: Busier repositories may experience longer delays
4. **No SLA guarantee**: GitHub doesn't provide timing guarantees for free scheduled workflows

### **Timing Alternatives (If Precise Timing Is Critical)**
1. **Accept delays** (recommended): Most practical for domain monitoring
2. **External scheduler**: Use a VPS with precise cron → trigger GitHub Actions via webhook
3. **Frequent checks**: Run every 15 minutes to ensure one runs near the target time
4. **Self-hosted runners**: More predictable but requires infrastructure investment

## 🔧 **Improved Architecture: Single Notification System**

### **How It Works**
The system now uses a **single, intelligent notification system** that eliminates redundancy:

1. **Main command handles all scenarios**: `vibe check-domains --scheduled --heartbeat`
2. **Smart notification logic**: Sends exactly one message per run based on results
3. **Heartbeat mode**: Ensures visibility even when no domains are available
4. **Failure notifications**: Only trigger if the entire workflow fails

### **Notification Matrix**
| Scenario | Heartbeat Flag | Notification Sent | Message Type |
|----------|---------------|------------------|--------------|
| Available domains found | Any | ✅ Yes | Domain results with alerts |
| No domains available | `--heartbeat` | ✅ Yes | Heartbeat confirmation |
| No domains available | No flag | ❌ No | Silent completion |
| Empty domains.txt | `--heartbeat` | ✅ Yes | Heartbeat with "no domains monitored" |
| API errors occurred | Any | ✅ Yes | Error notification with details |
| Workflow failure | Any | ✅ Yes | GitHub Actions failure alert |

## Configuration

### Required Secrets

Configure these secrets in your GitHub repository at `Settings > Secrets and variables > Actions`:

- **`WHOIS_API_KEY`**: Your WHOIS API key for domain lookups
- **`SLACK_WEBHOOK_URL`**: Your Slack incoming webhook URL for notifications

### Workflow Schedule

The automated check runs **approximately every hour** using the cron schedule:
```yaml
schedule:
  - cron: '0 * * * *'  # Target: top of each hour (actual: 5-30 min delays)
```

**Note**: Due to GitHub Actions limitations, expect 5-30 minute delays from the target time.

### Manual Triggers

You can manually trigger checks via:
1. **GitHub UI**: Go to Actions → "Automated Domain Availability Checker" → "Run workflow"
2. **Optional heartbeat**: Choose whether to send heartbeat notifications

## Monitoring and Troubleshooting

### **Expected Notifications**

#### **Scheduled Runs (Every ~Hour)**
- **One notification per hour** containing:
  - Domain check results (if domains are available)
  - Heartbeat confirmation (if no domains available)
  - Error details (if API issues occur)

#### **Manual Runs**
- **Immediate notification** (when heartbeat enabled) or silent (when disabled)
- Same content format as scheduled runs

### **Troubleshooting Guide**

#### **No Notifications Received**
1. **Check timing expectations**: Allow 5-30 minutes past the hour
2. **Verify secrets**: Ensure `WHOIS_API_KEY` and `SLACK_WEBHOOK_URL` are set
3. **Check workflow logs**: Go to Actions tab → latest run → examine logs
4. **Test manual trigger**: Use GitHub UI to run workflow manually with heartbeat

#### **Workflow Failures**
1. **Check the failure notification** in Slack (includes GitHub Actions link)
2. **Common causes**:
   - Missing or invalid API keys
   - WHOIS API rate limits exceeded
   - Slack webhook URL expired or incorrect
   - Network connectivity issues

#### **Testing the System**

##### **Local Testing**
```bash
# Test with heartbeat (should always send notification)
vibe check-domains --scheduled --heartbeat

# Test without heartbeat (silent if no available domains)
vibe check-domains --scheduled

# Test manual trigger
vibe check-domains --manual --heartbeat
```

##### **GitHub Actions Testing**
1. **Manual workflow trigger**: Actions → "Automated Domain Availability Checker" → "Run workflow"
2. **Enable heartbeat**: Check the "Send heartbeat notification" option
3. **Check execution**: Monitor logs for debugging output

##### **Monitoring Health**
- **Heartbeat notifications**: Confirm you receive hourly notifications when no domains are available
- **Workflow logs**: Check for environment variable status and execution details
- **GitHub Actions history**: Review recent run history for patterns

## System Architecture

### **Workflow Structure**
```
GitHub Actions (Hourly) → Python CLI → Domain Check Service → Slack Notifications
                                   ↓
                           Single, Smart Notification
                                   ↓
                        (Results, Heartbeat, or Errors)
```

### **Key Components**
1. **GitHub Actions workflow**: Scheduling and environment management
2. **Python CLI**: Command-line interface with trigger detection
3. **Domain Check Service**: Core business logic and API integration
4. **Slack Notifier**: Rich message formatting and delivery

### **Notification Flow**
1. **Check domains**: Query WHOIS API for each domain
2. **Analyze results**: Determine availability and problematic statuses
3. **Format message**: Create rich Slack message with results
4. **Send notification**: Deliver to Slack channel
5. **Log outcome**: Record success/failure in workflow logs

## Best Practices

### **Monitoring**
- **Enable heartbeat mode**: Ensures you know the system is working
- **Check GitHub Actions history**: Monitor for failures or timing patterns
- **Review Slack notifications**: Look for error patterns or API issues

### **Maintenance**
- **API key rotation**: Update secrets when WHOIS API keys expire
- **Webhook validation**: Test Slack webhook periodically
- **Domain list management**: Keep `domains.txt` updated with relevant domains

### **Troubleshooting**
- **Check logs first**: GitHub Actions logs contain detailed debugging information
- **Test locally**: Use CLI commands to reproduce issues
- **Verify secrets**: Ensure API keys and webhook URLs are correctly configured

## Advanced Configuration

### **Customizing the Schedule**
To change the frequency, modify the cron schedule in `.github/workflows/check-domains.yml`:
```yaml
schedule:
  - cron: '0 */6 * * *'  # Every 6 hours
  - cron: '0 9,17 * * *'  # 9 AM and 5 PM daily
```

### **Domain Management**
- **Add domains**: Update `domains.txt` with one domain per line
- **Remove domains**: Delete lines from `domains.txt`
- **Temporary disable**: Move domains to comments (prefix with `#`)

### **Notification Customization**
- **Disable heartbeat**: Remove `--heartbeat` flag from scheduled runs
- **Change trigger type**: Modify `--scheduled` or `--manual` flags as needed

---

## Summary

The system now provides:
- **Reliable hourly monitoring** (with expected 5-30 minute delays)
- **Single, non-redundant notifications** per check cycle
- **Intelligent heartbeat system** for automation health verification
- **Comprehensive error handling** and failure notifications
- **Rich Slack message formatting** with domain status details

The architecture eliminates redundant notifications while maintaining high visibility into system health and domain availability changes.
