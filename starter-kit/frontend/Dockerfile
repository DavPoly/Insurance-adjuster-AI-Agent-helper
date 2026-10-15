FROM python:3.12-slim

WORKDIR /app

COPY frontend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY frontend/ ./

ENV PYTHONPATH=/app

EXPOSE 3000

CMD ["chainlit", "run", "chainlit_app.py", "--host", "0.0.0.0", "--port", "3000", "--headless"]
