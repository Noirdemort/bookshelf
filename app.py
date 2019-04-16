from flask import Flask, request, render_template, redirect, session, url_for
import pymongo
import hashlib
from datetime import datetime as dt
import random
from predictor import recommendation_generator
import re

app = Flask(__name__)

books_list = []
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["bookshelf"]
users = db["users"]
books = db["books"]
transactions = db["transactions"]


def gen_hash(key):
    aa = hashlib.md5(key.encode("utf-8")).hexdigest()
    return aa


@app.route("/", methods=["GET", "POST"])
@app.route("/home")
def home():
    user = "Guest"
    action = {"text": "Log in", "route": "/login"}
    books_for_home = books_list.copy()
    books_list.clear()
    options = {}
    if 'username' in session:
        user = session['username']
        user_data = users.find_one({"email": user})
        options = {"Edit Profile": "/edit_profile", "Transactions": "/transactions"}
        if "seller" in user_data.keys():
            options["Add Book"] = "/add_book"
            options["Statistics"] = "/stats"
        action = {"text": "Log out", "route": "/logout"}
    if not books_for_home:
        books_for_home.extend(generate_books(user))
    return render_template("home.html", name=user, options=options, action=action, books=books_for_home)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    credentials = dict(request.form)
    username = credentials["email"]
    password = credentials["password"]
    rex = users.find_one({"email": username})
    print(rex)
    if rex is None:
        return "<h1>No such user!</h1>"
    if rex["password"] == gen_hash(password+username[:7]):
        session['username'] = rex['email']
        return redirect(url_for("home"))
    else:
        return "<h1>Invalid credentials!</h1>"


def generate_books(email):
    records = list(transactions.find({"buyer": email}))
    if records:
        book_name = random.choice(records)['title']
        author = books.find_one({"book_id": random.choice(records)['book_id']})['author']
        return recommendation_generator(title=book_name, author=author)
    all_books = list(books.find())
    results = random.choices(all_books, k=10)
    mod_results = []
    for result in results:
        mod_results.append([result['book_id'], result['title'], result['author']])
    return mod_results


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    data = dict(request.form)
    print(data)
    already_exist = users.find_one({"email": data["email"]})
    if already_exist is not None:
        return "<h1>User already registered!</h1>"
    register = {"email": data["email"], "password": data["password"], "address": data["address"]}
    if "seller" in data.keys():
        register["seller"] = "on"
        register["payment_url"] = data["payment_url"]
    register["password"] = gen_hash(register["password"] + register["email"][:7])
    register['token'] = gen_hash(register["email"]+register["password"])
    users.insert_one(register)
    session['username'] = register['email']
    return "Your token is {}. Don't share it with anyone. Go to <a href='/home'>Home</a>".format(register['token'])


@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    if 'username' in session:
        if request.method == "GET":
            user_info = users.find_one({"email": session['username']})
            token = user_info['token']
            address = user_info['address']
            return render_template("edit_profile.html", address=address, token=token)
        else:
            data = dict(request.form)
            user = session['username']
            message = ""
            print(data)
            if data['password'] != '' and data['cpassword'] != '':
                if data['password'] != data['cpassword']:
                    return "<h1>Passwords do not match</h1>"
                new_password = gen_hash(data['password'] + user[:7])
                users.update_one(
                    {"email": user}, {
                        "$set": {
                            "password": new_password
                        }
                    })
                message += "Password successfully updated. "
            if data['address'] != '':
                users.update_one(
                    {"email": user}, {
                        "$set": {
                            "address": data['address']
                        }
                    })
                message += "Address successfully updated. "
            if 'seller' in data:
                if data['payment_url'] == '':
                    return "<h1> Add payment url to become a seller.</h1>"
                users.update_one(
                    {"email": user}, {
                        "$set": {
                            "seller": "on",
                            "payment_url": data['payment_url']
                        }
                    })
                message += "Seller capabilities successfully added. "
            else:
                user_info = users.find_one({"email": user})
                if 'seller' in user_info:
                    users.update_one(
                        {"email": user}, {
                            "$unset": {
                                "seller": 1,
                                "payment_url": 1
                            }
                        })
                    message += "Seller capabilities successfully removed. "
            if not message:
                message = "No changes made."
            return "<h2>{} Go to <a href='/'>Home</a></h2>".format(message)
    else:
        return redirect(url_for("login"))


@app.route("/buy", methods=["GET", "POST"])
@app.route("/buy/<book_id>", methods=["GET", "POST"])
def buy_book(book_id):
    if 'username' not in session:
        return redirect(url_for("login"))
    if request.method == "GET":
        user = session['username']
        user = users.find_one({"email": user})
        book = books.find_one({"book_id": book_id})
        return render_template("buy_book.html", book_id=book_id, book_name=book["title"], book_author=book["author"], price=book["price"], address=user["address"])
    data = dict(request.form)
    print(data)
    user = session['username']
    count = data["count"]
    book_id = data["book_id"]
    address = data["address"]
    book = books.find_one({"book_id": book_id})
    price = book["price"]
    title = book["title"]
    cost = int(price)*int(count)
    t = dt.now()
    transaction = {
        "count": int(count),
        "cost": cost,
        "book_id": book_id,
        "title": title.lower(),
        "buyer": user,
        "address": address,
        "seller": book["seller"],
        "day": t.day,
        "month": t.month,
        "year": t.year
    }
    print(transaction)
    transactions.insert_one(transaction)
    order = "{} copies of {} were ordered for Rs {} at address {}. <br>".format(transaction['count'], transaction['title'].title(), transaction['cost'], transaction['address'])
    return "<h2>{} <br> Order Placed! <br> Go to <a href='/home'>Home</a></h2>".format(order)


@app.route("/search", methods=["GET", "POST"])
def search_book():
    data = dict(request.form)
    print(data)
    word = data["search"].lower()
    search_expr = re.compile(f".*{word}.*", re.I)

    search_request = {
        '$or': [
            {'author': {'$regex': search_expr}},
            {'title': {'$regex': search_expr}},
            {'genre': {'$regex': search_expr}},
            {'isbn': {'$regex': search_expr}}
        ]
    }
    results = list(books.find(search_request))
    global books_list
    mod_results = []
    for result in results:
        mod_results.append([result['book_id'], result['title'], result['author']])
    books_list = mod_results[:10]
    return redirect(url_for("home"))


@app.route("/transactions")
def server_records():
    if 'username' not in session:
        return redirect(url_for("login"))
    user = session['username']
    search_expr = re.compile(user, re.I)

    search_request = {
        '$or': [
            {'buyer': {'$regex': search_expr}},
            {'seller': {'$regex': search_expr}}
        ]
    }
    sell_records = list(transactions.find({"seller": user}))
    buy_records = list(transactions.find({"buyer": user}))
    print(sell_records)
    return render_template("transactions.html", sell_records=sell_records, buy_records=buy_records)


@app.route("/add_book", methods=["GET", "POST"])
def add_to_database():
    if 'username' not in session:
        return redirect(url_for("login"))
    if request.method == "GET":
        seller = session['username']
        options = {"Edit Profile": "/edit_profile", "Add Book": "/add_book", "Statistics": "/stats", "Transactions": "/transactions"}
        action = {"text": "Log out", "route": "/logout"}
        return render_template("addBook.html", seller=seller, options=options, action=action)
    seller = session['username']
    data = dict(request.form)
    data["genre"] = data["genre"].lower().replace(",", " ")
    book = {"title": data["title"].lower(), "author": data["author"].lower(), "genre": data['genre'],
            "price": data["price"].lower(), "seller": seller, "book_id": gen_hash(data["title"].lower()+seller)}
    if 'isbn' in data:
        book['isbn'] = data['isbn']
    if book["title"] == book["author"] == "":
        return "invalid, enter at least book name or author or isbn"
    books.insert_one(book)
    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    del session['username']
    return redirect(url_for("login"))


@app.route("/stats")
def stats():
    if 'username' in session:
        seller = session['username']
    else:
        return redirect(url_for("login"))
    transaction = list(transactions.find({"seller": seller, "year": dt.now().year}).sort("cost", pymongo.DESCENDING))
    if not transaction:
        return "No transactions available for this seller in current year. For previous year transactions use " \
               "Telegram bot. "
    total = 0
    book_count = 0
    records = []
    for t in transaction:
        records.append(t)
        total += int(t['cost'])
        book_count += int(t['count'])

    transaction = records
    top_buyers = []
    for s in transaction:
        print(s)
        top_buyers.append(s['title'])
        if len(top_buyers) == 10:
            break

    print(top_buyers)
    # results = concoction(total, transaction, top_buyers)
    return render_template("stats.html", buyers=top_buyers, year=dt.now().year, total=total, book_count=book_count)


# Telegram Section


@app.route("/report_daily/<seller>_<day>", methods=["GET", "POST"])
def report_daily(seller, day):
    print(day)
    print(type(day))
    if day == "-1":
        day = dt.now().day
    seller = users.find_one({"token": seller})
    if 'seller' not in seller:
        return "You are not a seller."
    transaction = list(transactions.find({"seller": seller['email'], "day": int(day), "month": dt.now().month, "year": dt.now().year}).sort("cost", pymongo.DESCENDING))
    total = 0
    for t in transaction:
        print(t['cost'])
        total += int(t['cost'])

    top_buyers = []
    highest_grossing = []
    for t in transaction:
        top_buyers.append(t['buyer'])
        highest_grossing.append(t['title'])
        if len(top_buyers) == 5:
            break

    results = concoction(total, highest_grossing, top_buyers)
    return results


@app.route("/report_monthly/<seller>_<month>", methods=["GET", "POST"])
def report_monthly(seller, month):
    if month == "-1":
        month = dt.now().month
    seller = users.find_one({"token": seller})
    if 'seller' not in seller:
        return "You are not a seller."
    transaction = list(transactions.find({"seller": seller['email'], "month": int(month), "year": dt.now().year}).sort("cost", pymongo.DESCENDING))
    total = 0
    for t in transaction:
        total += int(t['cost'])

    top_buyers = []
    highest_grossing = []
    for t in transaction:
        top_buyers.append(t['buyer'])
        highest_grossing.append(t['title'])
        if len(top_buyers) == 10:
            break

    results = concoction(total, highest_grossing, top_buyers)
    return results


@app.route("/report_yearly/<seller>_<year>", methods=["GET", "POST"])
def report_yearly(seller, year=None):
    if year == "-1":
        year = dt.now().year
    seller = users.find_one({"token": seller})
    if 'seller' not in seller:
        return "You are not a seller."
    transaction = list(transactions.find({"seller": seller['email'], "year": year}).sort("cost", pymongo.DESCENDING))
    total = 0
    for t in transaction:
        total += int(t['cost'])

    top_buyers = []
    highest_grossing = []
    for t in transaction:
        top_buyers.append(t['buyer'])
        highest_grossing.append(t['title'])
        if len(top_buyers) == 14:
            break

    print(top_buyers, highest_grossing)

    results = concoction(total, highest_grossing, top_buyers)
    return results


def concoction(total, highest_grossing, top_buyers):
    final_string = "Your total sale was {}. \n".format(total)

    final_string += "Your best selling books were: \n"
    for i in range(len(highest_grossing)):
        final_string += '{}. {}\n'.format(i+1, highest_grossing[i])

    final_string += "Your top buyer were:\n"
    for i in range(len(top_buyers)):
        final_string += "{}. {}\n".format(i+1, top_buyers[i])

    return final_string


@app.route("/validate/<token>", methods=["POST"])
def validate_email(token):
    if users.find_one({"token": token}) is not None:
        return "True"
    return "False"


@app.route("/search_telegram/<word>", methods=["POST"])
def search_it(word):
    word = word.lower()
    search_expr = re.compile(f".*{word}.*", re.I)

    search_request = {
        '$or': [
            {'author': {'$regex': search_expr}},
            {'title': {'$regex': search_expr}},
            {'genre': {'$regex': search_expr}},
            {'isbn': {'$regex': search_expr}}
        ]
    }
    results = list(books.find(search_request))
    top_picks = results[:10]

    # format it
    message = f"Search results for {word} are:- \n"

    count = 1
    for book in top_picks:
        message += f"{count}. {book['title']} - {book['author']} {book['book_id']}  at Rs. {book['price']}/-\n"
        count += 1
    return message


@app.route("/buy_over_the_wire/<data>_<user>", methods=["POST"])
def buy_over_the_phone(data, user):
    user = users.find_one({"token": user})
    data = list(data.split("-"))
    count = int(data[1])
    book_id = data[0]
    address = data[2]
    if address == "1":
        address = user['address']
    user = user['email']
    book = books.find_one({"book_id": book_id})
    price = book["price"]
    title = book["title"].lower()
    cost = int(price)*int(count)
    t = dt.now()
    transaction = dict(count=int(count), cost=cost, title=title, book_id=book_id, buyer=user, address=address,
                       seller=book["seller"], day=t.day, month=t.month, year=t.year)
    transactions.insert_one(transaction)
    return 'Your Order was Placed Successfully!'


if __name__ == "__main__":
    app.secret_key = "bookShelf"
    app.run(debug=True)
