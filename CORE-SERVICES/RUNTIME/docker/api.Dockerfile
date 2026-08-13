FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY CORE-SERVICES/BACKEND-API/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY AI5R-SDK /app/AI5R-SDK
COPY CORE-SERVICES /app/CORE-SERVICES
COPY PRODUCTS /app/PRODUCTS
COPY REGISTRY /app/REGISTRY

WORKDIR /app/CORE-SERVICES/BACKEND-API

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
