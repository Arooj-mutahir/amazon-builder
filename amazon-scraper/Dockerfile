# Python 3.12 slim image use karein
FROM python:3.12-slim

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Working directory set karein
WORKDIR /app

# Pehle requirements copy karein (taake cache use ho)
COPY requirements.txt .

# Dependencies install karein
RUN python -m pip install --no-cache-dir -r requirements.txt

# Baaki saari files copy karein (dist folder included)
COPY . .

# Railway ke liye port expose karein (FastAPI 8080 use kar raha hai)
EXPOSE 8080

# App ko run karein (Agar aapke paas run.py hai toh usko yahan rakh sakte hain, warna main.py)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]