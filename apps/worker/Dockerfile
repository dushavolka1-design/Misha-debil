FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY packages/py_dar /tmp/py_dar
RUN pip install --no-cache-dir /tmp/py_dar

COPY apps/worker /app
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir .

CMD ["python", "-m", "worker.main"]
