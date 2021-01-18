import requests as reqs
import json
import datetime as dt
import telebot
import threading
import os
import configparser as cp

from telebot import types
from multiprocessing import Value
from timeloop import Timeloop
from datetime import timedelta

# Инициализация
# Чтение конфига
config = cp.ConfigParser(interpolation=None)
config.read('settings.conf')
getCourseUrl = config['main']['url']
token = config['telegram']['token']

bot = telebot.TeleBot(token)

usdSell = Value('d', 0.01)
eurSell = Value('d', 0.01)

usdCsvDir = os.getcwd()+'\\USD\\'
if not os.path.exists(usdCsvDir):
    os.mkdir(usdCsvDir)

eurCsvDir = os.getcwd()+'\\EUR\\'
if not os.path.exists(eurCsvDir):
    os.mkdir(eurCsvDir)

# Сохранение курса в файл
def saveCourseToCsv(currency, date, data):
    raw = ''
    csvPath=''
    for item in data:
        raw += item + ','
    raw += '\n'
    
    if currency == 'USD':
        csvPath = usdCsvDir + date + '.csv'
    if currency == 'EUR':
        csvPath = eurCsvDir + date + '.csv'
    
    if not os.path.exists(csvPath):
        raw = 'Текущее время,Актуальность,Продажа,Покупка\n' + raw

    csv = open(csvPath, 'a')
    csv.write(raw)
    csv.close()

def convert(raw, course, currencyName):
    array = raw.split()
    if len(array) != 2:
        return 'Неверный формат данных.\n Попробуйте отправить, например, '"'100 rub'"'\n'
    return format(float(array[0]) * course, '.2f') + ' ' + currencyName + '\n'

# Получение курса валюты
def getCourse():
    # Запрос курса валюты
    resp = reqs.get(getCourseUrl)
    data = resp.json()
    
    # Разбор полученного json
    # и запись результата в usdRate и eurRate
    usd = 'USD'
    eur = 'EUR'
    breakCount = 2
    usdRate = []
    eurRate = []
    currencies = data['GroupedRates']
    for i in range(len(currencies)):
        moneyRate = currencies[i]['MoneyRates']
        fromCurrency = moneyRate[0]['FromCurrency']
        fromCode = fromCurrency['Code']
        sell = moneyRate[0]['BankSellAt']
        buy = moneyRate[0]['BankBuyAt']
        date = dt.datetime.fromisoformat(moneyRate[0]['StartDate'])
    
        if fromCode == usd:
            with usdSell.get_lock():
                usdSell.value = sell
            usdRate.append(dt.datetime.now().strftime('%X'))
            usdRate.append(date.strftime('%X'))
            usdRate.append(str(sell))
            usdRate.append(str(buy))
            saveCourseToCsv(fromCode, date.strftime('%Y-%m-%d'), usdRate)
            breakCount -= 1
    
        if fromCode == eur:
            with eurSell.get_lock():
                eurSell.value = sell
            eurRate.append(dt.datetime.now().strftime('%X'))
            eurRate.append(date.strftime('%X'))
            eurRate.append(str(sell))
            eurRate.append(str(buy))
            saveCourseToCsv(fromCode, date.strftime('%Y-%m-%d'), eurRate)
            breakCount -= 1
    
        if breakCount == 0:
            break


    result = usd + ': \n'
    result += 'Продажа: ' + str(usdRate[2]) + '\n'
    result += 'Покупка: ' + str(usdRate[3]) + '\n'
    result += '----\n'
    
    result += eur + ': \n'
    result += 'Продажа: ' + str(eurRate[2]) + '\n'
    result += 'Покупка: ' + str(eurRate[3])

    return result

# Обработка входящего сообщения
@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    factor = 0.0
    if message.text == 'Текущий курс':
        response = getCourse()
        bot.send_message(message.from_user.id, response)
    elif 'rub' in message.text.lower() or 'rur' in message.text.lower():
        factor = 1/usdSell.value
        bot.send_message(message.from_user.id, convert(message.text, factor, 'usd'))
        factor = 1/eurSell.value
        bot.send_message(message.from_user.id, convert(message.text, factor, 'eur'))
    elif 'usd' in message.text.lower():
        factor = usdSell.value
        bot.send_message(message.from_user.id, convert(message.text, factor, 'rur'))
    elif 'eur' in message.text.lower():
        factor = eurSell.value
        bot.send_message(message.from_user.id, convert(message.text, factor, 'rur'))
    else:
        bot.send_message(message.from_user.id, 'Ошибка!')

# Запуск бота
def start_bot_polling():
    print('polling start\n')
    bot.polling(none_stop=True, interval=0)

# __run__
getCourse()

t = threading.Thread(target=start_bot_polling, daemon=True)
t.start()

# Запуск периодического опроса курса
tl = Timeloop()
@tl.job(interval=timedelta(seconds=300))
def auto_send_message():
    getCourse()

tl.start(block=True)

# Завершение работы скрипта
bot.stop_polling()
t.join()
usdSell.close()
usdSell.unlink()
eurSell.close()
eurSell.unlink()
print('polling end\n')
