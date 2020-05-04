FROM python:3.6.2

WORKDIR /usr/src/canary

ADD . /usr/src/canary

RUN apt-get update
RUN pip3 install --trusted-host pypi.python.org -r requirements.txt


ENTRYPOINT ["python3", "src/bot.py"]