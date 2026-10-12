.PHONY: up down logs seed test lint migrate shell gcp-push

up:            ## Build and start the local stack
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api worker litellm

migrate:
	docker compose run --rm migrate

seed:          ## Upload the synthetic SOPs through the API
	docker compose exec api python scripts/seed.py --api-url http://localhost:8000

test:
	docker compose exec api pytest -q

lint:
	docker compose exec api ruff check .

shell:
	docker compose exec api bash

# Usage: make gcp-push PROJECT=my-proj REGION=asia-southeast1 TAG=v0.1.0
gcp-push:
	docker build -t $(REGION)-docker.pkg.dev/$(PROJECT)/kyc/app:$(TAG) .
	docker build -f deploy/litellm/Dockerfile -t $(REGION)-docker.pkg.dev/$(PROJECT)/kyc/litellm:$(TAG) .
	docker push $(REGION)-docker.pkg.dev/$(PROJECT)/kyc/app:$(TAG)
	docker push $(REGION)-docker.pkg.dev/$(PROJECT)/kyc/litellm:$(TAG)
