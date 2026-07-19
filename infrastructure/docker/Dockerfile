FROM python:3.10-slim

WORKDIR /app

# 1. Copy and install standard requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

EXPOSE 8000

#CMD ["python","-m","uvicorn", "apps.identity.identity_main:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["python"]