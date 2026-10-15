FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt

#Installing the CPU build from PyTorch's own
# index first means later installs (sentence-transformers depends on torch)
# find the requirement already satisfied and skip the CUDA packages entirely.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY tools ./tools

ENV PYTHONPATH=/app
ENV TOOLS_DIR=/app/tools

# Pre-download the local embedding model at build time so ingestion and querying
# have no network dependency at runtime beyond the LLM API key.
RUN python -c "from app.constants.rag.claim_embedding_config import EMBEDDING_MODEL_NAME; from sentence_transformers import SentenceTransformer; SentenceTransformer(EMBEDDING_MODEL_NAME)"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
