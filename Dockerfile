FROM python:3.6.5

WORKDIR /usr/src/bloxlink

ADD . /usr/src/bloxlink

RUN apt-get update
RUN pip3 install --trusted-host pypi.python.org -r requirements.txt


ENTRYPOINT ["python3", "src/bot.py"]