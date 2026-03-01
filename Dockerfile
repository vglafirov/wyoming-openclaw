FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY wyoming_openclaw.py .

EXPOSE 10600

ENTRYPOINT ["python", "wyoming_openclaw.py"]
CMD ["--host", "0.0.0.0", "--port", "10600"]
