.PHONY: setup start stop test ingest eval grade clean logs health grade-infra grade-rag grade-accuracy grade-guardrails grade-ui grade-multimodal grade-smoke
GRADER = docker compose -f ../auto-grader/docker-compose.grade.yml run --rm --build grader

setup:
	docker compose up --build -d --wait --wait-timeout 120
	@$(MAKE) health
	@$(MAKE) ingest
start:
	docker compose up -d --wait --wait-timeout 120
stop:
	docker compose down
test:
	docker compose run --rm --build -v "$(CURDIR)/tests:/app/tests:ro" api python -m pytest /app/tests/backend -q
	docker compose run --rm --build -v "$(CURDIR)/tests:/app/tests:ro" ui python -m pytest /app/tests/frontend -q
# Embeds data/knowledge-base/*.json into Qdrant; recreates the collection each run.
ingest:
	docker compose run --rm --build api python -m app.rag.ingest
# Reports search_past_claims recall@k/MRR against hand-written queries.
eval:
	docker compose run --rm --build -v "$(CURDIR)/backend/evals:/app/evals:ro" api python -m evals.claim_search_recall_eval
health:
	curl --fail --silent --show-error --retry 10 --retry-connrefused --retry-delay 2 http://localhost:8000/api/v1/health
	curl --fail --silent --show-error http://localhost:3000 > /dev/null
logs:
	docker compose logs -f
# Stops only this project. Persistent volumes are preserved.
clean:
	docker compose down --remove-orphans

# Public evaluation helpers. Report suspected defects; do not weaken checks to inflate scores.
# Interviewer evaluation uses a clean evaluator copy, independent of candidate edits.
grade:
	$(GRADER)
grade-infra:
	$(GRADER) python -m pytest tests/test_infrastructure.py -q
grade-rag:
	$(GRADER) python -m pytest tests/test_rag.py -q
grade-accuracy:
	$(GRADER) python -m pytest tests/test_accuracy.py -q -s
grade-guardrails:
	$(GRADER) python -m pytest tests/test_guardrails.py -q
grade-ui:
	$(GRADER) python -m pytest tests/test_ui.py -q
grade-multimodal:
	$(GRADER) python -m pytest tests/test_multimodal.py -q

# Three varied positive cases for iteration; never a substitute for make grade.
grade-smoke:
	$(GRADER) python -m pytest tests/test_accuracy.py -q -s --accuracy-smoke
