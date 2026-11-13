FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Dependencies install karein
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

# Saari files copy karein (dist folder included)
COPY . .

# Expose port (Railway isi port ko detect karta hai)
EXPOSE 8080

# ✅ run.py ki jagah main.py chalayein
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]