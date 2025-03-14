FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Only copy the necessary application files
COPY app/ ./app/
COPY alembic.ini ./
COPY alembic/ ./alembic/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]