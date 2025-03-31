FROM python:3.11.4

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

ENV TOKENIZERS_PARALLELISM=false

ENTRYPOINT ["python", "app.py"]
