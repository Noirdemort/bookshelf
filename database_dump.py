import pymongo
import faker
import random
import hashlib
from datetime import datetime as dt
from faker.providers import isbn
import json
import csv
import requests

fake = faker.Faker()
fake.add_provider(isbn)
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["bookshelf"]
users_collection = db["users"]
books_collection = db["books"]
transactions_collection = db["transactions"]


def gen_hash(key):
    aa = hashlib.md5(key.encode("utf-8")).hexdigest()
    return aa


# user = {email, password, seller, payment_url, address}
# book = {title, author, genre, isbn, quantity, price, seller}
# transaction = { count, cost, title, address, book['seller'], day, month, year}


sides_of_coin = [True, False]
users = []
users_clone = []
sellers = []
for i in range(200):
    email = fake.email()
    init_pass = fake.password()
    address = fake.address().replace("\n", ' ')
    password = gen_hash(init_pass + email[:7])
    token = gen_hash(init_pass + email)
    user = {"email": email, "password": password, "address": address, "token": token}
    user_clone = {"email": email, "password": init_pass, "address": address, "token": token}
    rat = random.choice(sides_of_coin)
    if rat:
        url = fake.url()
        user["seller"] = "true"
        user["payment_url"] = url
        user_clone["seller"] = "true"
        user_clone["payment_url"] = url
        sellers.append(user_clone)
    users.append(user)
    users_clone.append(user_clone)

users_collection.insert_many(users)
user_read = {"users": users_clone}
with open('user_data.json', 'w') as outfile:
    json.dump(user_read, outfile)

seller_read = {"sellers": sellers}
with open('seller_data.json', 'w') as outfile:
    json.dump(seller_read, outfile)

books = []
genres = ["fantasy", "romance", "thriller", "biography", "satire"]
csvfile = open("book_dataset.csv", 'w')
fieldnames = ['book_id', 'title', 'author', 'genre', 'isbn', 'price', 'seller']
writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
writer.writeheader()
for i in range(1000):
    # book = {title, author, genre, isbn, quantity, price, seller}
    book_name = fake.name().lower()
    seller = random.choice(sellers)["email"]
    book = {"book_id": gen_hash(book_name + seller),
            "title": book_name,
            "author": fake.name().lower(),
            "genre": " ".join(random.choices(genres)),
            "isbn": fake.isbn13(separator="").lower(),
            "price": random.randint(50, 1000),
            "seller": seller
            }
    writer.writerow(book)
    books.append(book)
csvfile.close()
books_collection.insert_many(books)

transactions = []
for i in range(1000):
    # transaction = { count, cost, title, address, book['seller'], day, month, year}
    book = random.choice(books)
    user = random.choice(users)
    seller = random.choice(sellers)
    x = random.randint(1, 6)
    t = dt.now()
    transaction = {"count": x,
                   "cost": book["price"] * x,
                   "title": book['title'],
                   "book_id": book['book_id'],
                   "address": user['address'],
                   "buyer": user['email'],
                   "seller": seller['email'],
                   "day": t.day - random.randint(-10, 10),
                   "month": t.month - random.randint(-2, 2),
                   "year": t.year
                   }
    transactions.append(transaction)
transactions_collection.insert_many(transactions)

print(users_clone[0])
print(books[0])
print(transactions[0])
