FROM python:3.6.2
ENV PYTHONUNBUFFERED TRUE
ENV C_FORCE_ROOT true
WORKDIR /src
ADD ./src /src
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
CMD gunicorn app:factory --bind 0.0.0.0:80 --access-logfile - --error-logfile - --log-syslog --log-level debug --worker-class aiohttp.GunicornWebWorker