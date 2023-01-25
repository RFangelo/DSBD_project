# syntax=docker/dockerfile:1

FROM python:latest

WORKDIR /python-docker

COPY requirements.txt requirements.txt

#se hai mac apple silicon
#RUN apt update && apt -y install software-properties-common gcc
#RUN git clone https://github.com/edenhill/librdkafka
#RUN cd librdkafka && ./configure && make && make install && ldconfig


RUN pip install -r requirements.txt

COPY . .

CMD [ "python3", "app.py", "kafka:9092","prometheusdata"]