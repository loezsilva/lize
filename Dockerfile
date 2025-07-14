FROM python:3.13-slim

RUN apt-get update && apt-get install bash-completion gcc python3-dev libpq-dev poppler-utils libzbar0 libzbar-dev ffmpeg libsm6 libxext6 libgnutls28-dev libcurl4-gnutls-dev -y

ENV PYTHONUNBUFFERED 1

RUN mkdir /code

WORKDIR /code

COPY requirements.txt /code/

RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /code/

RUN ["chmod", "+x", "entrypoint.sh", "predeploy.sh"]