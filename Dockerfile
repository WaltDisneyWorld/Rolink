FROM python:latest

RUN apt-get update
RUN apt-get install -y git python3-pip libopus0 libav-tools
RUN apt-get install -y liblua5.3-dev

WORKDIR /usr/src/bloxlink

ADD . /usr/src/bloxlink

RUN pip3 install --trusted-host pypi.python.org -r requirements.txt


ENV RELEASE CANARY 
ENV TOKEN 0

EXPOSE 8000


CMD ["sh", "-c", "python3 bot.py ${RELEASE} ${TOKEN}"]