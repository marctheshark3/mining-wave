FROM python:3.9

WORKDIR /app

COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Add this line to ensure Python output isn't buffered
ENV PYTHONUNBUFFERED=1

# Change the CMD to use the --reload flag and add some logging
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]
