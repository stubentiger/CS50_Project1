# Small website with books ratings and reviews

## Description

Was done according to the task from Harvard CS50 "Web Programming with Python and JavaScript" course.

It is a pet project aimed at demonstrating the usage of:
- HTML5, SCSS, Bootstrap
- python3, Flask in particular
- integration using 3d party REST API
- SQL
- sqlalchemy (the usage is limited according to CS50 task requirements)
- Docker

Some aspects are excluded from the scope of the project (for example, password hashing and input data validation) and will be implemented in the other pet projects :)

## Installation

1. download all the files from repository
2. make sure you have Docker [installed](https://docs.docker.com/get-docker/) and launched
3. navigate to the project directory and run this command
> $ docker-compose up

4. the website will be available on http://0.0.0.0:5000/

## Usage

1. For a quick glance use a test user credentials:
> login: test@test.com
> password:password

Example of a book page with user's review:
http://0.0.0.0:5000/books/0380795272

2. Using Goodreads API
You can obtain book data using Goodreads API.
Make a GET request to /api/<isbn> route, where <isbn> is an ISBN number. The website will return a JSON response containing the book’s title, author, publication date, ISBN number, review count, and average score.
