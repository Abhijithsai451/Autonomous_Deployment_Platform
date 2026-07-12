FROM python:3.10-slim

WORKDIR /app

# 1. Copy and install standard requirements
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 2. Copy all code structures (including apps/ and packages/)
COPY . .

EXPOSE 8000

# 3. Explicitly execute the main entrypoint down the nested apps package path
CMD ["uvicorn", "apps.identity.main:app", "--host", "0.0.0.0", "--port", "8000"]