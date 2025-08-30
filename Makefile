.PHONY: help setup test run docker-build-webhooks docker-build-issuer compose issue-license

help:
	@echo "Targets: setup, test, run, docker-build-webhooks, docker-build-issuer, compose, issue-license"

setup:
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements-test-client.txt

test:
	. .venv/bin/activate && pytest -v || true

run:
	. .venv/bin/activate && python server.py

docker-build-webhooks:
	docker build -t smsai-twilio:latest docker/twilio-webhook
	docker build -t smsai-msgr:latest docker/messenger-webhook

docker-build-issuer:
	docker build -t smsai-license-issuer:latest docker/license-issuer

compose:
	docker compose up --build

issue-license:
	@echo "LICENSE_ISSUER_SECRET=<base64> scripts/issue_license.sh --license-id LIC-001 --tier pro --expires 2026-12-31 --hardware-id ANY --features core,assist"

# Android builds (require Android SDK / or run in GitHub Actions)
.PHONY: bundle-store bundle-full
bundle-store:
	./gradlew bundleStoreRelease

bundle-full:
	./gradlew bundleFullRelease
