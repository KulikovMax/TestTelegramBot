from telegram.ext import Updater, CommandHandler
from bob_telegram_tools.bot import TelegramBot
from datetime import datetime, date, timedelta

import matplotlib.pyplot as plt
import sqlite3 as sl

import requests


updater = Updater(token='1701773507:AAHP6g_N_QH275tWDvhVzCphsJ0f9nAtNfU', use_context=True)
dispatcher = updater.dispatcher


def get_response(link='https://api.exchangeratesapi.io/latest?base=USD'):
    """This function takes link as an argument and takes JSON data from it. Then it converts JSON to dictionary."""
    response = requests.get(link)
    json_data = response.json()
    exchange_rates = dict()

    for key, value in json_data.get('rates').items():
        exchange_rates.update({key: value})
    return exchange_rates


def write_to_database(exchange_rates, timestamp_now, message):
    """This function insert currency rates to database. It also creates message that will be shown to user."""
    exchange_rates = get_response()
    conn = sl.connect('exchanges.sqlite')
    cur = conn.cursor()
    keys_to_insert = ''
    values_to_insert = ''
    for key, value in exchange_rates.items():
        message += key + ": " + str(round(value, 2)) + "\n"
        keys_to_insert += key + ','
        values_to_insert += str(round(value, 2)) + ','
    keys_to_insert = keys_to_insert[:-1]
    values_to_insert = values_to_insert[:-1]
    cur.execute('INSERT INTO exchange_rates(%s) VALUES (%s)' % (keys_to_insert, values_to_insert))
    conn.commit()
    conn.close()


def read_from_database():
    """This function select currency rates from databases and return dictionary."""
    conn = sl.connect('exchanges.sqlite')
    conn.row_factory = sl.Row
    cur = conn.cursor()
    cur.execute('SELECT * FROM exchange_rates WHERE id=(SELECT MAX(id) FROM exchange_rates);')
    rows = cur.fetchall()
    names = [description[0] for description in cur.description][1:]
    values = [row for row in rows[0][1:]]
    kv_dict = dict(zip(names, values))
    return kv_dict


def lst(update, context):
    """Function that send user currencies exchange rates based on USD."""
    exchange_rates = dict()
    message = ""
    with open('timestamp.txt', 'r') as ts_file:
        line = ts_file.readline()
        timestamp = datetime.strptime(line, '%Y-%m-%d %H:%M:%S.%f')
        timestamp_now = datetime.now()
        if timestamp_now > timestamp + timedelta(minutes=10):
            write_to_database(exchange_rates, timestamp_now, message)
            with open('timestamp.txt', 'w') as ts_file_write:
                ts_file_write.write(str(timestamp_now))
        else:
            exchange_rates = read_from_database()

    for k, v in exchange_rates.items():
        message += k + ': ' + str(v) + '\n'

    context.bot.sendMessage(chat_id=update.message.chat_id, text=message)


def exchange(update, context):
    """Function that converts USD to other currencies."""
    exchange_rates = get_response()

    exchange_message = update.message.text.replace('/exchange', '')
    exchange_message = exchange_message.replace('to', '')
    exchange_message = exchange_message.replace(' ', '')

    usd_to_convert = ''

    for symbol in exchange_message:
        if symbol.isdigit():
            usd_to_convert += symbol
    if usd_to_convert == '':
        context.bot.sendMessage(chat_id=update.message.chat_id, text='Enter sum to convert.')

    usd_to_exchange = int(usd_to_convert)

    currency_to_convert = exchange_message[len(exchange_message) - 3:len(exchange_message)].upper()
    result = round(exchange_rates.get(currency_to_convert) * usd_to_exchange, 2)

    context.bot.sendMessage(chat_id=update.message.chat_id, text=str(result) + " " + currency_to_convert)


def history(update, context):
    """Function shows plot of the exchange rate changes for selected currency fo last 7 days."""
    message = update.message.text.replace('/history ', '')
    first_currency = message[0:3].upper()
    second_currency = message[4:].upper()

    end_at = date.today()
    start_at = date.today() - timedelta(days=7)

    link = f'https://api.exchangeratesapi.io/history?' + \
           f'start_at={start_at.year}-{start_at.month}-{start_at.day}&' + \
           f'end_at={end_at.year}-{end_at.month}-{end_at.day}&' + \
           f'base={first_currency}&symbols={second_currency}'

    exchange_rates = get_response(link)
    exchange_rates_by_time = dict()
    for key, value in exchange_rates.items():
        for k, v in value.items():
            exchange_rates_by_time.update({key: v})

    if len(exchange_rates_by_time) < 7:
        context.bot.sendMessage(chat_id=update.message.chat_id,
                                text='No exchange rate data is available for selected currency.')
    else:
        plt_data = exchange_rates_by_time.items()
        plt_data = sorted(plt_data)
        x, y = zip(*plt_data)

        plt.plot(x, y)

        token = '1701773507:AAHP6g_N_QH275tWDvhVzCphsJ0f9nAtNfU'
        chat_id = update.message.chat_id
        bot = TelegramBot(token, chat_id)
        bot.send_plot(plt)
        bot.clean_tmp_dir()


def hlp(update, context):
    text = '''
    /lst - Shows exchange rates of currencies based on USD. Example of usage: /lst
    /exchange - Convert USD to another currency. Example of usage: /exchange 100USD to EUR
    /history - Shows plot of exchange rate changes for selected currency. Example of usage: /history EUR
    '''
    context.bot.sendMessage(chat_id=update.message.chat_id, text=text)


lst_handler = CommandHandler('lst', lst)
dispatcher.add_handler(lst_handler)

exchange_handler = CommandHandler('exchange', exchange)
dispatcher.add_handler(exchange_handler)

history_handler = CommandHandler('history', history)
dispatcher.add_handler(history_handler)

hlp_handler = CommandHandler('hlp', hlp)
dispatcher.add_handler(hlp_handler)

updater.start_polling()
