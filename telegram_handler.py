import logging
import pymongo
import requests
from telegram import ReplyKeyboardMarkup
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Database store
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["bookshelf_telegram"]
users = db["users"]

CHOOSING, TYPING_REPLY, TYPING_CHOICE = range(3)

reply_keyboard = [['Add Account'],
                  ['Search', 'Buy'],
                  ['Done']]


markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)


def facts_to_str(user_data):
    facts = list()

    for key, value in user_data.items():
        facts.append('{} - {}'.format(key, value))

    return "\n".join(facts).join(['\n', '\n'])


def start(update, context):
    update.message.reply_text("Hi! Welcome to BookShelf...", reply_markup=markup)
    user_data = update.message.from_user
    if not users.find_one({"user_id": user_data["id"]}):
            update.message.reply_text("Seems like you are using this for the first time, please choose add Account.", reply_markup=markup)
    update.message.reply_text("Use search to search any book and use the book id to place an order.", reply_markup=markup)
    return CHOOSING


def statistics(update, context):
    update.message.reply_text("Daily stats")
    print(update.message.text)
    text = update.message.text.rstrip()
    text = text.split(' ')
    if len(text) == 1:
        dex = "-1"
    else:
        dex = text[1]
    seller = update.message.from_user['id']
    seller = users.find_one({"user_id": seller})
    if not seller:
        update.message.reply_text("Please add your account first!!!")
        return CHOOSING
    r = requests.post("http://localhost:5000/report_daily/{}_{}".format(seller['token'], dex), data={})
    update.message.reply_text(r.text)
    return CHOOSING


def statistics_yearly(update, context):
    update.message.reply_text("Yearly stats")
    print(update.message.text)
    text = update.message.text.rstrip()
    text = text.split(' ')
    if len(text) == 1:
        dex = "-1"
    else:
        dex = text[1]
    seller = update.message.from_user['id']
    seller = users.find_one({"user_id": seller})
    if not seller:
        update.message.reply_text("Please add your account first!!!")
        return CHOOSING
    r = requests.post("http://localhost:5000/report_yearly/{}_{}".format(seller['token'], dex), data={})
    update.message.reply_text(r.text)
    return CHOOSING


def statistics_monthly(update, context):
    update.message.reply_text("Monthly stats")
    print(update.message.text)
    text = update.message.text.rstrip()
    text = text.split(' ')
    if len(text) == 1:
        dex = "-1"
    else:
        dex = text[1]
    seller = update.message.from_user['id']
    seller = users.find_one({"user_id": seller})
    if not seller:
        update.message.reply_text("Please add your account first!!!")
        return CHOOSING
    r = requests.post("http://localhost:5000/report_monthly/{}_{}".format(seller['token'], dex), data={})
    update.message.reply_text(r.text)
    return CHOOSING



def regular_choice(update, context):
    text = update.message.text
    context.user_data['choice'] = text
    if text == 'Buy':
        update.message.reply_text("Yippie! We are shopping...", reply_markup=markup)
        update.message.reply_text("Send us details as book_isbn-quantity-address", reply_markup=markup)
        update.message.reply_text("Example: 828282828-3-'2/3 block 283 - Road'", reply_markup=markup)
    elif text == 'Done':
        update.message.reply_text('Packing up...', reply_markup=markup)
        context.user_data.clear()
    elif text == "Search":
        update.message.reply_text("Search your book using name, author, isbn, genre...", reply_markup=markup)
    elif text == "Add Account":
        update.message.reply_text("Send us the token generated on website", reply_markup=markup)
    elif text.lower() == "report":
        statistics(update, context)
    else:
        update.message.reply_text("OOPS! Wrong option!!", reply_markup=markup)
        return CHOOSING

    return TYPING_REPLY


def custom_choice(update, context):
    print(update.message.text)
    update.message.reply_text('Alright, please send me the category first, '
                              'for example "Search"')

    return CHOOSING


def received_information(update, context):
    user_data = context.user_data.copy()
    text = update.message.text
    category = user_data['choice']
    user_data[category] = text

    if user_data['choice'] == 'Search':
        r = requests.post("http://localhost:5000/search_telegram/{}".format(user_data['Search']), data={})
        update.message.reply_text(r.text, reply_markup=markup)
        user_data.clear()
    elif user_data['choice'] == 'Buy':
        data = list(user_data[category].split('-'))
        if len(data) != 3:
            update.message.reply_text("Wrong Format! Resend Data as in Example!", reply_markup=markup)
            del user_data[category]
            return TYPING_REPLY
        user = users.find_one({"user_id": update.message.from_user['id']})
        if not user:
            update.message.reply_text("Please add your account first!!!")
            user_data.clear()
            return CHOOSING
        user = user['token']
        r = requests.post("http://localhost:5000/buy_over_the_wire/{}_{}".format(user_data['Buy'], user), data={})
        if r.text != "Failed":
            update.message.reply_text(r.text, reply_markup=markup)
        else:
            update.message.reply_text("Something went wrong, try again!", reply_markup=markup)
        user_data.clear()
    elif user_data['choice'] == 'Add Account':
        r = requests.post("http://localhost:5000/validate/{}".format(user_data['Add Account']), data={})
        print(r.text)
        if r.text == "True":
            users.insert_one({"user_id": update.message.from_user["id"], "token": user_data['Add Account']})
            update.message.reply_text("Your account has been successfully added!", reply_markup=markup)
        else:
            update.message.reply_text("INVALID TOKEN!!!", reply_markup=markup)
        user_data.clear()

    return CHOOSING


def done(update, context):
    user_data = context.user_data
    # Your last transaction
    update.message.reply_text("Last Transaction")
    update.message.reply_text(user_data)

    user_data.clear()
    return ConversationHandler.END


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater("key goes here", use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            CHOOSING: [RegexHandler('^(Add Account|Search|Buy)$', regular_choice, pass_user_data=True),
                       # RegexHandler('^Something else...$', regular_choice, p),
                       CommandHandler('report', statistics, pass_user_data=True),
                       CommandHandler('report_yearly', statistics_yearly, pass_user_data=True),
                       CommandHandler('report_monthly', statistics_monthly, pass_user_data=True)
                       ],

            TYPING_CHOICE: [MessageHandler(Filters.text,
                                           custom_choice,
                                           pass_user_data=True),
                            ],

            TYPING_REPLY: [MessageHandler(Filters.text,
                                          received_information,
                                          pass_user_data=True),
                           ],
        },

        fallbacks=[CommandHandler('Done', done, pass_user_data=True)]
    )

    dp.add_handler(conv_handler)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
