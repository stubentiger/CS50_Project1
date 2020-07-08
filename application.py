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
    user_name = logged_in_user()
    #remove else and change "is not" logic
    if user_name is not None:
        return redirect(url_for("books", name=user_name))
    else:
        return render_template("guest.html")


#check whether user is logged in and return her/his name
# ADD DECORATOR!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! - think about it

# Check that all forms contain expected fields and values because they
# can be missing.

# Look at tool called "black"

def logged_in_user():
    if "user_id" in session:
        return session["user_name"]
    return None


def authorize_user(user_id, name):
    session["user_id"] = user_id
    session["user_name"] = name
    return redirect(url_for("books", name=name))


@app.route("/registration", methods=["GET", "POST"])
def register():
    #create a separate func for this
    if request.method == "GET":
        user_name = logged_in_user()
        if user_name is not None:
            return redirect(url_for("books", name=user_name))
        else:
            return render_template("registration.html")
    #create a sep func and split this into functions
    # function with several args
    elif request.method == "POST":
        #check a user with this email isn't registered already
        email = request.form.get("email")
        email_from_db = db.execute(
        """
        SELECT user_id
        FROM users
        WHERE email = :email
        """,
        {"email": email}
        ).fetchone()
        if email_from_db is not None:
            return error_page("registration_error", "User with this email already exists.")

        name = request.form.get("name")
        password = request.form.get("password")
        # Use postgres RETURNS statement to return newly created user id
        db.execute(
        """
        INSERT INTO users (name, email, password)
        VALUES (:name, :email, :password)
        """,
        {"name": name, "email": email, "password": password}
        )
        db.commit()
        # log in this new user
        user = db.execute(
        """
        SELECT user_id
        FROM users
        WHERE email = :email
          AND password = :password
        """,
        {"email": email, "password": password}
        ).fetchone()
        return authorize_user(user.user_id, name)


@app.route("/login", methods=["GET", "POST"])
def login():
    #if a user opens a log in page
    if request.method == "GET":
        user_name = logged_in_user()
        if user_name is not None:
            return render_template("books.html", name=user_name)
        else:
            return render_template("login.html")
    #if a user filled in login data and submits the form
    #create new func for this
    elif request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = db.execute(
        """
        SELECT user_id, name, email, password
        FROM users
        WHERE email = :email
          AND password = :password
        """,
        {"email": email, "password": password}
        ).fetchone()
        if user is None:
            return error_page("login_error", "Login or email provided is incorrect.")
        else:
            return authorize_user(user.user_id, user.name)


def error_page(endpoint, message):
    return redirect(url_for(endpoint, message=message))


# app.route can be applied multiple times to the same function
@app.route("/login_error", endpoint="login_error")
@app.route("/registration_error", endpoint="registration_error")
@app.route("/books/error")
def render_error_page():
    return render_template("Error.html", message=request.args.get("message", "Go away!!!"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return render_template("guest.html")


@app.route("/books")
def books():
    user_name = logged_in_user()
    if user_name is None:
        return redirect(url_for("index"))

    search_string = request.args.get("search_input")

    #def render_books(books, error):
    #    return render_template(
    #        "books.html",
    #        search_string=search_string,
    #        books=books,
    #        error=error,
    #    )

    #if it's the first page opening and search wasn't made yet
    # look at jinja2 "is defined" thing, it allows to omit arguments to render_template
    if search_string is None:
        return render_template("books.html", name=user_name, books=None, search_string=None)
    if search_string == "":
        return render_template("books.html", search_string=search_string, books=None, error="Search request is empty. No books found.")

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
    if not books:
        return render_template("books.html", search_string=search_string, books=None, error="No books found for your search query")
    return render_template("books.html", search_string=search_string, books=books, error="")


def get_book_data(isbn):
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


@app.route("/books/<isbn>")
def book_page(isbn):
    user_name = logged_in_user()
    if user_name is None:
        return redirect(url_for("index"))

    book_data = get_book_data(isbn)
    #if there is no book
    if book_data is None:
        return error_page("render_error_page", "The book doesn't exist")
    else:
        #if a book is found obtain it's review rating from Goodreads API
        # make a separate function
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "quFd8ZfpGD5PkWZ5M20FDg", "isbns": isbn}).json()

        avg_review = res["books"][0]["average_rating"]
        if not avg_review:
            avg_review = "No rating"
        else:
            avg_review = avg_review + " / 5.00"

        total_reviews = res["books"][0]["work_ratings_count"]

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


@app.route("/books/<isbn>/review", methods=["GET", "POST"])
def submit_review(isbn):
    user_name = logged_in_user()
    if user_name is None:
        return redirect(url_for("index"))

    book_data = get_book_data(isbn)

    if request.method == "GET":
        if book_data is None:
            return redirect(url_for("book_error", message="You can't add a review. The book doesn't exist."))
        else:
            return render_template("review.html", title=book_data.title, isbn=isbn, error="")
    elif request.method == "POST":
        # check that current user hasn't left a review for this book
        user_id = session.get("user_id")
        review = db.execute(
        """
        SELECT user_id
        FROM reviews
        WHERE
          isbn = :isbn
          AND user_id = :user_id
        """,
        {"isbn": isbn, "user_id": user_id}
        ).fetchone()

        if review is not None:
            return render_template("review.html", title=book_data.title, isbn=isbn, error="You have already reviewed this book")

        # rating is a mandatory field
        rate = request.form.get("review")
        if rate is None:
            return render_template("review.html", title=book_data.title, isbn=isbn, error="Select a score for the book")


        rate = int(rate)
        revision_text = request.form.get("review_text")
        db.execute(
        """
        INSERT INTO reviews (isbn, user_id, rate, revision_text)
        VALUES
        (:isbn, :user_id, :rate, :revision_text)
        """,
        {"isbn": isbn, "user_id": user_id, "rate": rate, "revision_text": revision_text}
        )
        db.commit()

        return redirect(url_for("book_page", isbn=isbn))


@app.route("/api/<isbn>")
def get_book_api(isbn):
    book_data = get_book_data(isbn)
    #no book with such isbn in our db
    if book_data is None:
        return jsonify({"error": "Invalid book isbn"}), 404

    response = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "quFd8ZfpGD5PkWZ5M20FDg", "isbns": isbn})

    #if the book exists but there is no data about it in Goodreads
    if response.status_code == 404:
        avg_review = "no data"
        total_reviews = "no data"
    # TODO add else for the below block or wrap in try/except
    res = response.json()
    avg_review = res["books"][0]["average_rating"]
    total_reviews = res["books"][0]["work_ratings_count"]

    return jsonify({
        "title": book_data.title,
        "author": book_data.author,
        "year": book_data.author,
        "isbn": book_data.year,
        "review_count": total_reviews,
        "average_score": avg_review,
    })
