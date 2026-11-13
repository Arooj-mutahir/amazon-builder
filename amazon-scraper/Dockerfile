FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Working directory set karein (Root mein)
WORKDIR /app

# Pehle dependencies install karein (Caching ke liye)
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

# Saari files copy karein (Jisme aapka 'dist' folder bhi shamil hai)
COPY . .

# Railway internally port 8080 use karta hai
EXPOSE 8080

# Uvicorn ko directly run karein
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]