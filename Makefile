.PHONY: install run dev clean

install:
	uv sync
	@echo "🍋 Lemon installed. Try: uv run lemon dev"

run:
	uv run lemon dev

dev:
	$(MAKE) run

clean:
	rm -rf .venv __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned."
