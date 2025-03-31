FROM python:3.11.4

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

ENV GOOGLE_APPLICATION_CREDENTIALS=/app/auditpulse-f5cef618d352.json

ENV TOKENIZERS_PARALLELISM=false

ENTRYPOINT ["python", "app.py"]
