FROM python:latest

RUN apt-get update
RUN apt-get install -y git python3-pip libopus0 libav-tools

WORKDIR /usr/src/bloxlink

ADD . /usr/src/bloxlink

RUN pip3 install --trusted-host pypi.python.org -r requirements.txt

ENV config config.py


CMD ["sh", "-c", "python3 bot.py ${config}"]