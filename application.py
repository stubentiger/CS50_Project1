import os
import requests

from flask import Flask, session, render_template, request, redirect, url_for, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("books", name=session.get("user_name")))

    return render_template("guest.html")


# Check that all forms contain expected fields and values because they
# can be missing.

# Look at tool called "black"


def redirect_not_loggedin_user():
    if "user_id" not in session:
        return redirect(url_for("index"))


def authorize_user(user_id, name):
    session["user_id"] = user_id
    session["user_name"] = name
    return redirect(url_for("books", name=name))


def render_or_books(template):
    if "user_id" not in session:
        return render_template(template)
    return redirect(url_for("books", name=session.get("user_name")))


def email_exists(email):
    result = db.execute(
    """
    SELECT user_id
    FROM users
    WHERE email = :email
    """,
    {"email": email}
    ).fetchone()
    return result is not None


def register_user(name, email, password):
    user = db.execute(
    """
    INSERT INTO users (name, email, password)
    VALUES (:name, :email, :password)
    RETURNING user_id
    """,
    {"name": name, "email": email, "password": password}
    ).fetchone()
    db.commit()
    return user


@app.route("/registration", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_or_books("registration.html")

    try:
        email = request.form["email"]
        name = request.form["name"]
        password = request.form["password"]
    except KeyError:
        return error_page("registration_error", "Something went wrong. Try later.")
    #check a user with this email isn't registered already
    if email_exists(email):
        return error_page("registration_error", "User with this email already exists.")

    user = register_user(name, email, password)

    # log in this new user
    return authorize_user(user.user_id, name)


def get_user(email, password):
    user = db.execute(
    """
    SELECT user_id, name, email, password
    FROM users
    WHERE email = :email
      AND password = :password
    """,
    {"email": email, "password": password}
    ).fetchone()
    return user


@app.route("/login", methods=["GET", "POST"])
def login():
    #if a user opens a log in page
    if request.method == "GET":
        return render_or_books("login.html")

    try:
        email = request.form["email"]
        password = request.form["password"]
    except KeyError:
        return error_page("login_error", "Something went wrong. Try later.")

    user = get_user(email, password)
    if user is None:
        return error_page("login_error", "Login or email provided is incorrect.")

    return authorize_user(user.user_id, user.name)


def error_page(endpoint, message):
    return redirect(url_for(endpoint, message=message))


# app.route can be applied multiple times to the same function
@app.route("/login_error", endpoint="login_error")
@app.route("/registration_error", endpoint="registration_error")
@app.route("/book_error", endpoint="book_error")
@app.route("/books/error")
def render_error_page():
    return render_template("Error.html", message=request.args.get("message", "Go away!!!"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return render_template("guest.html")


def get_books_by_search(search_string):
    books = db.execute(
    """
    SELECT isbn, title, author
    FROM books
    WHERE
      isbn LIKE :search_phrase
      OR title LIKE :search_phrase
      OR author LIKE :search_phrase
    """,
    {"search_phrase": "%" + search_string + "%"}
    ).fetchall()
    return books


@app.route("/books")
def books():

    redirect_not_loggedin_user()

    search_string = request.args.get("search_input")

    def render_books(**kwargs):
        return render_template("books.html", search_string=search_string, **kwargs)

    #if it's the first page opening and search wasn't made yet
    if search_string is None:
        return render_books(name=session.get("user_name"))

    if search_string == "":
        return render_books(error="Search request is empty. No books found.")

    books = get_books_by_search(search_string)
    if not books:
        return render_books(error="No books found for your search query")

    return render_books(books=books)


def get_book_by_isbn(isbn):
    book_data = db.execute(
    """
    SELECT isbn, title, author, year
    FROM books
    WHERE
      isbn = :isbn
    """,
    {"isbn": isbn}
    ).fetchone()
    return book_data


def get_rating_from_provider(isbn):
    response = requests.get("https://www.goodreads.com/book/review_counts.json",
    params={"key": "quFd8ZfpGD5PkWZ5M20FDg", "isbns": isbn})
    if response.status_code == 404:
        avg_review = "no data"
        total_reviews = "no data"
        return {"review": avg_review, "total": total_reviews}
    res = response.json()
    avg_review = res["books"][0]["average_rating"]
    if not avg_review:
        avg_review = "No rating"
    else:
        avg_review = avg_review + " / 5.00"

    total_reviews = res["books"][0]["work_ratings_count"]

    return (avg_review, total_reviews)


#START FROM HERE!!!!!!!!!!!!!!!!
@app.route("/books/<isbn>")
def book_page(isbn):

    redirect_not_loggedin_user()

    book_data = get_book_by_isbn(isbn)
    #if there is no book
    if book_data is None:
        return error_page("render_error_page", "The book doesn't exist")

    #if a book is found obtain it's review rating from Goodreads API
    avg_review, total_reviews = get_rating_from_provider(isbn)

    reviews = db.execute(
    """
    SELECT name, date, rate, revision_text
    FROM
    reviews JOIN users ON reviews.user_id = users.user_id
      WHERE isbn = :isbn
    """,
    {"isbn": isbn}
    ).fetchall()

    return render_template(
        "book_data.html",
        title=book_data.title,
        author=book_data.author,
        isbn=book_data.isbn,
        year=book_data.year,
        avg_review=avg_review,
        total_reviews= total_reviews,
        reviews = reviews
    )


def get_reviewer(isbn, user_id):
    reviewer = db.execute(
    """
    SELECT user_id
    FROM reviews
    WHERE
      isbn = :isbn
    AND user_id = :user_id
    """,
    {"isbn": isbn, "user_id": user_id}
    ).fetchone()
    return reviewer


def add_review(isbn, user_id, rate, revision_text):
    db.execute(
    """
    INSERT INTO reviews (isbn, user_id, rate, revision_text)
    VALUES
    (:isbn, :user_id, :rate, :revision_text)
    """,
    {"isbn": isbn, "user_id": user_id, "rate": rate, "revision_text": revision_text}
    )
    db.commit()


def parse_review_form(form):
    try:
        review = form["review"]
        revision_text = form["review_text"]
    except KeyError:
        return (None, None)

    try:
        review = int(review)
    except ValueError:
        return ("error", None)

    return (review, revision_text)



@app.route("/books/<isbn>/review", methods=["GET", "POST"])
def submit_review(isbn):

    redirect_not_loggedin_user()

    book_data = get_book_by_isbn(isbn)

    def render_review(**kwargs):
        return render_template("review.html", title=book_data.title, isbn=isbn, **kwargs)

    if request.method == "GET":
        if book_data is None:
            return error_page("book_error", "You can't add a review. The book doesn't exist.")
        return render_review()

    # check that current user hasn't left a review for this book
    user_id = session.get("user_id")
    reviewer = get_reviewer(isbn, user_id)
    if reviewer is not None:
        return render_review(error="You have already reviewed this book")

    review, revision_text = parse_review_form(request.form)
    if review is None:
    # review is a mandatory field
        return error_page("book_error", "Select a score for the book")
    if review == "error":
        return error_page("book_error", "Review should be a number.")

    add_review(isbn, user_id, review, revision_text)

    return redirect(url_for("book_page", isbn=isbn))


#public API to obtain book data
@app.route("/api/<isbn>")
def get_book_api(isbn):
    book_data = get_book_by_isbn(isbn)
    #no book with such isbn in our db
    if book_data is None:
        return jsonify({"error": "Invalid book isbn"}), 404

    avg_review, total_reviews = get_rating_from_provider(isbn)

    return jsonify({
        "title": book_data.title,
        "author": book_data.author,
        "year": book_data.author,
        "isbn": book_data.year,
        "review_count": total_reviews,
        "average_score": avg_review,
    })
