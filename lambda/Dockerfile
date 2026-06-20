# Local development — runs poll() which long-polls SQS in a loop.
# docker-compose uses this file. Not for AWS Lambda deployment.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY handler.py .
RUN addgroup --system app && adduser --system --ingroup app app
USER app
CMD ["python", "handler.py"]
