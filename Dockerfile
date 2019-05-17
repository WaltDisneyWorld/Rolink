FROM python:3.6

WORKDIR /usr/src/bloxlink

ADD . /usr/src/bloxlink

RUN apt-get update
RUN apt-get install -y git python3-pip libopus0 libav-tools
RUN pip3 install --trusted-host pypi.python.org -r requirements.txt

ENV RELEASE LOCAL
ENV TOKEN 0

EXPOSE 8000
EXPOSE 8765
