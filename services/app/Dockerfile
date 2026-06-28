FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

COPY services/app/app/ app/
COPY services/app/migrations/ migrations/
COPY wsgi.py .

RUN addgroup --system app && adduser --system --ingroup app app
ENV HOME=/tmp
USER app

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "--worker-tmp-dir", "/dev/shm", "wsgi:app"]
