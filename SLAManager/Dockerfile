# syntax=docker/dockerfile:1

FROM python:latest

WORKDIR /python-docker

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

CMD [ "python3", "app.py"]