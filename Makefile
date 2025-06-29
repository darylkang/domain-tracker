.PHONY: help install test test-watch test-cov test-file lint format type-check clean dev-setup tdd-demo

help: ## Show available commands
	@echo "🔍 Domain Tracker - Available Commands:"
	@echo ""
	@echo "📦 Setup & Installation:"
	@awk 'BEGIN {FS = ":.*?## "} /^install.*:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "🧪 TDD & Testing:"
	@awk 'BEGIN {FS = ":.*?## "} /^test.*:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "🔧 Code Quality:"
	@awk 'BEGIN {FS = ":.*?## "} /^(lint|format|type-check).*:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "🧹 Maintenance:"
	@awk 'BEGIN {FS = ":.*?## "} /^(clean|dev-setup).*:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "🔍 Domain Commands:"
	@awk 'BEGIN {FS = ":.*?## "} /^(run|check-single|validate-config|setup-env).*:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "🎓 Learning:"
	@awk 'BEGIN {FS = ":.*?## "} /^tdd-demo.*:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

install: ## Install package in development mode
	@echo "🔧 Installing package..."
	hatch env create
	hatch run pip install -e .
	@echo "✅ Installation complete!"
	@echo ""
	@echo "🧪 Try the TDD workflow:"
	@echo "  make test-watch    # Start TDD watch mode"
	@echo "  make tdd-demo      # See TDD example"

# TDD & Testing Commands
test: ## Run all tests
	@echo "🧪 Running all tests..."
	hatch run test

test-watch: ## Run tests in watch mode for TDD (Red-Green-Refactor)
	@echo "🔄 Starting TDD watch mode..."
	@echo "💡 TDD Workflow: 🔴 Write failing test → 🟢 Make it pass → 🔄 Refactor"
	@echo "   Press Ctrl+C to stop"
	hatch run pytest --looponfail

test-cov: ## Run tests with coverage report
	@echo "📊 Running tests with coverage..."
	hatch run pytest --cov=src --cov-report=html --cov-report=term-missing
	@echo "📄 Coverage report available at: htmlcov/index.html"

test-file: ## Run specific test file (usage: make test-file FILE=tests/test_example.py)
	@echo "🎯 Running specific test file: $(FILE)"
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Please specify FILE=tests/test_example.py"; \
		exit 1; \
	fi
	hatch run pytest $(FILE) -v

# Code Quality Commands
lint: ## Lint code with ruff
	@echo "🔍 Linting code..."
	hatch run lint

format: ## Format code with ruff  
	@echo "🎨 Formatting code..."
	hatch run format

type-check: ## Type check with mypy
	@echo "🔍 Type checking..."
	hatch run type-check

# Development & Maintenance
dev-setup: install ## Complete development environment setup
	@echo "🛠️  Setting up complete development environment..."
	@echo "📋 Installing pre-commit hooks..."
	hatch run pip install pre-commit
	hatch run pre-commit install
	@echo "🧪 Running initial test suite..."
	$(MAKE) test
	@echo ""
	@echo "✅ Development environment ready!"
	@echo "🎯 Next steps:"
	@echo "  1. Run 'make tdd-demo' to see TDD in action"
	@echo "  2. Start coding with 'make test-watch'"
	@echo "  3. Check '.cursor/rules/' for TDD guidelines"

clean: ## Clean build artifacts and caches
	@echo "🧹 Cleaning up..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	@echo "✅ Cleanup complete!"

# Domain Tracker Commands
run: ## Run domain checking with basic Slack messages
	@echo "🔍 Running domain availability check..."
	@vibe check-domains

run-debug: ## Run with debug logging enabled
	@echo "🔍 Running domain check with debug logging..."
	@vibe check-domains --debug

run-all: ## Run with notifications for all domains
	@echo "🔍 Running domain check with all notifications..."
	@vibe check-domains --notify-all

run-enhanced: ## Run with enhanced Slack messages (rich format)
	@echo "🔍 Running domain check with enhanced Slack messages..."
	@vibe check-domains --enhanced-slack

run-enhanced-all: ## Run with enhanced Slack messages for all domains
	@echo "🔍 Running domain check with enhanced Slack messages for all domains..."
	@vibe check-domains --enhanced-slack --notify-all

check-single: ## Check single domain (usage: make check-single DOMAIN=example.com)
	@if [ -z "$(DOMAIN)" ]; then \
		echo "❌ Please specify a domain: make check-single DOMAIN=example.com"; \
	else \
		echo "🔍 Checking $(DOMAIN)..."; \
		vibe check $(DOMAIN); \
	fi

check-single-enhanced: ## Check single domain with enhanced Slack messages (usage: make check-single-enhanced DOMAIN=example.com)
	@if [ -z "$(DOMAIN)" ]; then \
		echo "❌ Please specify a domain: make check-single-enhanced DOMAIN=example.com"; \
	else \
		echo "🔍 Checking $(DOMAIN) with enhanced messages..."; \
		vibe check $(DOMAIN) --enhanced-slack; \
	fi

setup-env: ## Create .env file from template
	@echo "🔧 Setting up environment configuration..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ Created .env file from template"; \
		echo "📝 Please edit .env with your actual API keys"; \
		echo "   - WHOIS_API_KEY: Get from https://whoisxml.whoisapi.com/"; \
		echo "   - SLACK_WEBHOOK_URL: Create at https://api.slack.com/messaging/webhooks"; \
	else \
		echo "⚠️  .env file already exists"; \
	fi

validate-config: ## Validate environment configuration
	@echo "🔍 Validating configuration..."
	@python -c "from domain_tracker.settings import Settings; s = Settings(); print('✅ Configuration valid!')" || echo "❌ Configuration invalid - check your .env file"

# TDD Learning & Demo
tdd-demo: ## Show TDD workflow example
	@echo "🎓 TDD (Test-Driven Development) Workflow Example"
	@echo "=================================================="
	@echo ""
	@echo "🔴 RED Phase: Write a failing test first"
	@echo "   def test_add_numbers():"
	@echo "       assert add_numbers(2, 3) == 5"
	@echo ""
	@echo "🟢 GREEN Phase: Write minimal code to pass"
	@echo "   def add_numbers(a, b):"
	@echo "       return a + b"
	@echo ""
	@echo "🔄 REFACTOR Phase: Improve code quality"
	@echo "   def add_numbers(a: int, b: int) -> int:"
	@echo "       \"\"\"Add two numbers and return the result.\"\"\""
	@echo "       return a + b"
	@echo ""
	@echo "💡 Key TDD Commands:"
	@echo "   make test-watch    # Continuous testing"
	@echo "   make test-cov      # Coverage analysis"
	@echo "   make test-file FILE=tests/test_module.py"
	@echo ""
	@echo "📚 Learn more: Check .cursor/rules/ for comprehensive TDD guidance"
