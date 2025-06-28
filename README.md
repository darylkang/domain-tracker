# 🔍 Domain Drop Tracker

A Python CLI tool for monitoring domain availability and sending Slack alerts when domains become available. Perfect for tracking expired or dropping domains that you want to register.

[![CI](https://github.com/darylkang/domain-tracker/workflows/CI/badge.svg)](https://github.com/darylkang/domain-tracker/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Automated Domain Checking](https://github.com/darylkang/domain-tracker/workflows/Automated%20Domain%20Availability%20Checker/badge.svg)](https://github.com/darylkang/domain-tracker/actions)

## ✨ Features

- **🔄 Automated Domain Monitoring**: Hourly checks via GitHub Actions
- **📱 Slack Notifications**: Instant alerts when domains become available
- **⚡ Fast CLI Interface**: Check individual domains or batch process from file
- **🛡️ Robust Error Handling**: Graceful failure handling with notification alerts
- **🔧 Easy Configuration**: Simple environment variable setup
- **📊 WhoisXML API Integration**: Reliable domain availability checking

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/darylkang/domain-tracker.git
cd domain-tracker

# Install dependencies (using hatch)
make install

# OR install with pip in a virtual environment
pip install -e .
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your actual keys
WHOIS_API_KEY=your_whoisxml_api_key_here
SLACK_WEBHOOK_URL=your_slack_webhook_url_here
```

### 3. Add Domains to Monitor

Edit `domains.txt` and add domains you want to monitor (one per line):

```
spectre.cx
example-domain.com
another-domain.org
```

### 4. Test the Setup

```bash
# Check a single domain
vibe check example.com

# Check all domains from domains.txt
vibe check-domains

# Check with debug logging
vibe check-domains --debug
```

## 📋 CLI Usage

### Single Domain Check
```bash
# Check availability of a specific domain
vibe check example.com
vibe check spectre.cx
```

### Batch Domain Check
```bash
# Check all domains from domains.txt
vibe check-domains

# Check with notifications for all domains (not just available ones)
vibe check-domains --notify-all

# Enable debug logging
vibe check-domains --debug
```

### Other Commands
```bash
# Show help
vibe --help
vibe check --help
vibe check-domains --help

# Show version
vibe --version
```

## 🔧 Configuration Guide

### Required Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# WhoisXML API Key (Required)
# Get your free API key at: https://whoisxml.whoisapi.com/
WHOIS_API_KEY=at_1234567890abcdef...

# Slack Webhook URL (Required) 
# Create a webhook at: https://api.slack.com/messaging/webhooks
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
```

### Optional Configuration

```bash
# Check interval for automated runs (default: 1 hour)
CHECK_INTERVAL_HOURS=1

# Custom path to domains file (default: domains.txt)
DOMAINS_FILE_PATH=custom-domains.txt
```

## 📱 Slack Setup

### 1. Create a Slack Webhook

1. Go to [Slack API: Incoming Webhooks](https://api.slack.com/messaging/webhooks)
2. Click "Create your Slack app"
3. Choose "From scratch"
4. Name your app (e.g., "Domain Tracker") and select your workspace
5. Go to "Incoming Webhooks" and activate it
6. Click "Add New Webhook to Workspace"
7. Choose the channel for notifications
8. Copy the webhook URL to your `.env` file

### 2. Test Slack Integration

```bash
# This should send a test message to your Slack channel
vibe check example.com
```

### Expected Slack Messages

- **Available Domain**: "✅ Domain available: example.com"
- **Unavailable Domain**: "❌ Domain NOT available: example.com" (only with `--notify-all`)
- **Error Alert**: "🚨 Domain Tracker Error: [error details]" (when automation fails)

## 🔑 WhoisXML API Setup

### 1. Get Your API Key

1. Visit [WhoisXML API](https://whoisxml.whoisapi.com/)
2. Sign up for a free account
3. Go to your dashboard and find your API key
4. Add it to your `.env` file as `WHOIS_API_KEY`

### 2. API Limits

- **Free Tier**: 500 requests/month
- **Paid Plans**: Higher limits available
- The tool handles rate limiting and errors gracefully

## 🤖 GitHub Actions Automation

### Automated Hourly Checking

The project includes a GitHub Actions workflow that automatically checks your domains every hour.

### Setup Steps

1. **Fork/Clone the Repository**
2. **Configure GitHub Secrets**:
   - Go to your repo → Settings → Secrets and variables → Actions
   - Add these secrets:
     - `WHOIS_API_KEY`: Your WhoisXML API key
     - `SLACK_WEBHOOK_URL`: Your Slack webhook URL

3. **Enable GitHub Actions**:
   - The workflow file is already included: `.github/workflows/check-domains.yml`
   - It runs automatically every hour at minute 0
   - You can also trigger it manually from the Actions tab

### Manual Workflow Trigger

```bash
# Go to your repo → Actions → "Automated Domain Availability Checker" → "Run workflow"
```

### Workflow Features

- **Automated Runs**: Every hour using cron schedule
- **Error Handling**: Failures are reported to Slack
- **Environment Setup**: Python 3.11 with all dependencies
- **Timeout Protection**: 10-minute safety timeout

For detailed setup instructions, see [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md).

## 📁 Project Structure

```
domain-tracker/
├── .github/
│   └── workflows/
│       ├── check-domains.yml     # Automated domain checking
│       └── python-ci.yml         # CI/CD pipeline
├── src/
│   └── domain_tracker/
│       ├── __init__.py           # Package initialization
│       ├── cli.py                # Command-line interface
│       ├── core.py               # Core business logic
│       ├── domain_management.py  # Domain file handling
│       ├── settings.py           # Configuration management
│       ├── slack_notifier.py     # Slack integration
│       └── whois_client.py       # WhoisXML API client
├── tests/                        # Comprehensive test suite
├── domains.txt                   # Domains to monitor
├── .env.example                  # Environment template
├── pyproject.toml               # Project configuration
├── Makefile                     # Development commands
└── README.md                    # This file
```

## 🧪 Development

### Running Tests

```bash
# Run all tests
make test

# Run tests with coverage
make test-cov

# Run specific test
pytest tests/test_cli.py -v

# TDD watch mode
pytest --looponfail
```

### Code Quality

```bash
# Lint code
make lint

# Format code
make format

# Type checking
make type-check

# Run all quality checks
make lint format type-check test
```

### Development Environment

```bash
# Install development dependencies
make install

# Install pre-commit hooks
pre-commit install

# Clean up build artifacts
make clean
```

## 🔒 Security Considerations

- **API Keys**: Never commit API keys to version control
- **Webhook URLs**: Keep Slack webhook URLs secure
- **Rate Limiting**: The tool respects API rate limits
- **Error Handling**: Sensitive data is not logged in error messages

## 📊 Monitoring & Troubleshooting

### Common Issues

**1. "Invalid API Key" Error**
```bash
# Check your .env file has the correct API key
cat .env | grep WHOIS_API_KEY
```

**2. Slack Notifications Not Working**
```bash
# Test your webhook URL
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test message"}' \
  $SLACK_WEBHOOK_URL
```

**3. GitHub Actions Failing**
- Check that GitHub Secrets are configured correctly
- Review the Actions log for specific error messages
- Ensure domains.txt is not empty

### Debug Mode

```bash
# Enable detailed logging
vibe check-domains --debug
```

### Manual Testing

```bash
# Test individual components
python -c "from domain_tracker.settings import Settings; print(Settings())"
python -c "from domain_tracker.domain_management import load_domains; print(load_domains())"
python -c "from domain_tracker.whois_client import check_domain_availability; print(check_domain_availability('google.com'))"
```

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature`
3. **Write tests first** (TDD approach)
4. **Implement your changes**
5. **Run tests**: `make test`
6. **Submit a pull request**

### Development Workflow

This project follows **Test-Driven Development (TDD)**:
- Write failing tests first
- Implement minimal code to pass
- Refactor and improve
- All tests must pass before merging

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🚀 Deployment Options

### Personal Use
- Run locally with cron job
- Use GitHub Actions (recommended)

### Team/Organization Use
- Deploy to cloud server with scheduled tasks
- Use container deployment (Docker)
- Integrate with existing monitoring systems

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/darylkang/domain-tracker/issues)
- **Documentation**: This README and inline code documentation
- **API Documentation**: [WhoisXML API Docs](https://whoisxml.whoisapi.com/documentation)

---

**Happy Domain Hunting! 🎯**

Made with ❤️ for domain enthusiasts and developers who want to automate their domain monitoring workflow.
