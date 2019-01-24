FROM debian:latest

RUN apt update
RUN apt upgrade -y
RUN apt install -y \
         git \
         postgresql-10 \
         python3 \
         python3-dev \
         python3-setuptools \
         python3-pip \
         nginx
RUN pip3 install pipenv

# PostgreSQL

# Nginx
COPY nginx-logstf.conf /etc/nginx/sites-available/default
RUN systemctl reload nginx.service

# Run server
RUN pip3 install pipenv
RUN pipenv install --system --deploy
RUN pipenv run python -m pipenv run uwsgi --ini uwsgi.ini

EXPOSE 80