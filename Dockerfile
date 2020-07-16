# pull official base image
FROM python:3.8.3-slim-buster

WORKDIR /app

# install dependencies
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# copy project
COPY application.py /app
COPY static /app/static
COPY templates /app/templates

# set environment variables
ENV FLASK_APP application.py

CMD ["flask", "run", "--host", "0.0.0.0"]
