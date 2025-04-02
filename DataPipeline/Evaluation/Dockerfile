FROM python:3.11.4

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

ENV TOKENIZERS_PARALLELISM=false

EXPOSE 5000

ENTRYPOINT ["python", "app.py"]
