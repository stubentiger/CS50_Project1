# pull official base image
FROM python:3.8.3-slim-buster


# install nc (required for wait.sh script)
RUN apt-get update \
 && apt-get install -y netcat \
# remove unnecessary metadata got by update command
 && rm -rf /var/lib/apt/lists/*

# add script to delay start until DB is available
COPY ./wait-for.sh /app/wait-for.sh

WORKDIR /app

# install dependencies
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# copy project
COPY application.py /app
COPY static /app/static
COPY templates /app/templates

# set flask environment variables
ENV FLASK_APP application.py

# start script to delay start until DB is available
ENTRYPOINT ["./wait-for.sh", "db:5432", "--"]
# start flask
# set public network interface to make it possible to assess docker container from outside (in our case, localhost)
CMD ["flask", "run", "--host", "0.0.0.0"]
