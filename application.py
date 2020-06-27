import os
import requests

from flask import Flask, session, render_template, request, redirect, url_for
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
    if user_name is not None:
        return redirect(url_for("books", name=user_name))
    else:
        return render_template("guest.html")

#check whether user is logged in and return her/his name
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
    if request.method == "GET":
        user_name = logged_in_user()
        if user_name is not None:
            return redirect(url_for("books", name=user_name))
        else:
            return render_template("registration.html")
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
            return redirect(url_for("registration_error", message="User with this email already exists."))

        name = request.form.get("name")
        password = request.form.get("password")
        db.execute(
        """
        INSERT INTO users (name, email, password) VALUES (:name, :email, :password)
        """,
        {"name": name, "email": email, "password": password}
        )
        db.commit()
        # log in this recently registered users
        user_id = db.execute(
        """
        SELECT user_id
        FROM users
        WHERE email = :email
          AND password = :password
        """,
        {"email": email, "password": password}
        ).fetchone()
        return authorize_user(user_id, name)



@app.route("/login", methods=["GET", "POST"])
def login():
    #if a user opens a log in page
    if request.method == "GET":
        user_name = logged_in_user()
        if user_name is not None:
            return render_template("books.html", name = user_name)
        else:
            return render_template("login.html")
    #if a user filled in login data and submits the form
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
            return redirect(url_for("login_error", message="Login or email provided is incorrect."))
        else:
            return authorize_user(user.user_id, user.name)


def render_error_page():
    return render_template("Error.html", message=request.args.get("message", "Go away!!!!"))

@app.route("/login_error")
def login_error():
    return render_error_page()

@app.route("/registration_error")
def registration_error():
    return render_error_page()

@app.route("/books/error")
def book_error():
    return render_error_page()


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return render_template("guest.html")


@app.route("/books", methods=["GET", "POST"])
def books():
    if request.method == "POST":
        return redirect(url_for("logout"))
    elif request.method == "GET":
        user_name = logged_in_user()
        if user_name is not None:
            return render_template("books.html", name=user_name)
        else:
            return redirect(url_for("index"))

@app.route("/books/search")
def search():
    search_phrase = request.args.get("search_input")
    if search_phrase == "" or search_phrase is None:
        return render_template("search.html", search_string=search_phrase, books=None, error="Search request is empty. No books found.")

    books = db.execute(
    """
    SELECT isbn, title, author
    FROM books
    WHERE
      isbn LIKE :search_phrase
      OR title LIKE :search_phrase
      OR author LIKE :search_phrase
    """,
    {"search_phrase": "%" + search_phrase + "%"}
    ).fetchall()
    if len(books) == 0:
        return render_template("search.html", search_string=search_phrase, books=None, error="No books found")
    else:
        return render_template("search.html", search_string=search_phrase, books=books, error="")

@app.route("/books/search/<isbn>")
def book_page(isbn):
    book_data = db.execute(
    """
    SELECT isbn, title, author, year
    FROM books
    WHERE
      isbn = :isbn
    """,
    {"isbn": isbn}
    ).fetchone()
    #if there is no book
    if book_data is None:
        return redirect(url_for("book_error", message="The book doesn't exist"))
    else:
        #if a book is found obtain it's review rating from Goodreads API
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "quFd8ZfpGD5PkWZ5M20FDg", "isbns": isbn}).json()

        avg_review = res["books"][0]["average_rating"]

        if avg_review == "":
            avg_review = "No rating"
        else:
            avg_review = avg_review + " / 5.00"

        total_reviews = res["books"][0]["work_ratings_count"]

        return render_template(
            "book_data.html",
            title=book_data.title,
            author=book_data.author,
            isbn=book_data.isbn,
            year=book_data.year,
            avg_review=avg_review,
            total_reviews= total_reviews
        )


@app.route("/books/search/<isbn>/review", methods=["GET", "POST"])
def submit_review(isbn):
    if request.method == "GET":
        return render_template("review.html")
    elif request.method == "POST":
        pass
