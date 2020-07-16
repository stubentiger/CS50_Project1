import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


#create books
def create_books():
    db.execute(
    """
    CREATE TABLE IF NOT EXISTS books(
    isbn varchar(10) PRIMARY KEY,
    title text NOT NULL,
    author text NOT NULL,
    year integer NOT NULL
    )
    """)
    db.commit()


#create users
def create_users():
    db.execute(
    """
    CREATE TABLE IF NOT EXISTS users(
    user_id SERIAL,
    name varchar(100) NOT NULL,
    email varchar(254) NOT NULL,
    password char(1024) NOT NULL
    )
    """
    )
    db.commit()


#create reviews
def create_reviews():
    db.execute(
    """
    CREATE TABLE IF NOT EXISTS reviews(
    isbn varchar(10) REFERENCES books(isbn),
    user_id integer REFERENCES users(user_id),
    rate integer NOT NULL,
    revision_text text,
    date DATE NOT NULL DEFAULT CURRENT_DATE
    PRIMARY KEY (isbn, user_id)
    )
    """
    )
    db.commit()


def books_filled():
    books = db.execute(
    """
    SELECT * FROM books
    LIMIT 1
    """
    ).fetchall()
    return books


# fill in the books table
def main():
    create_books()
    create_users()
    create_reviews()

    if not books_filled():
        file = open("books.csv")
        reader = csv.reader(file)
        next(reader, None)
        for isbn, title, author, year in reader:
            db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
                {"isbn": isbn, "title": title, "author": author, "year": int(year)})
        db.commit()


if __name__ == "__main__":
    main()
