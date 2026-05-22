FROM python:3.11-slim

WORKDIR /app

# Installeer systeembenodigdheden voor sommige Python-pakketten
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Kopieer de benodigde pakketten en installeer ze
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopieer de rest van de applicatiecode
COPY . .

# Stel poort 8000 open binnen de container voor FastAPI
EXPOSE 8000

# Start Uvicorn op om je FastAPI app (genaamd 'app' in main.py) te serveren
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]