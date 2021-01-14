import requests as reqs
import json
import datetime as dt
import telebot
import threading
import os
import configparser as cp

from telebot import types
from timeloop import Timeloop
from datetime import timedelta

# Чтение конфига
config = cp.ConfigParser(interpolation=None)
config.read('settings.conf')
getCourseUrl = config['main']['url']
token = config['telegram']['token']

bot = telebot.TeleBot(token)

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
            usdRate.append(dt.datetime.now().strftime('%X'))
            usdRate.append(date.strftime('%X'))
            #usdRate.append(fromCode)
            usdRate.append(str(sell))
            usdRate.append(str(buy))
            saveCourseToCsv(fromCode, date.strftime('%Y-%m-%d'), usdRate)
            breakCount -= 1
    
        if fromCode == eur:
            eurRate.append(dt.datetime.now().strftime('%X'))
            eurRate.append(date.strftime('%X'))
            #eurRate.append(fromCode)
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
    if message.text == 'Текущий курс':
        response = getCourse()
        bot.send_message(message.from_user.id, response)
    else:
        bot.send_message(message.from_user.id, 'Ошибка!')

# Запуск бота
def start_bot_polling():
    print('polling start\n')
    bot.polling(none_stop=True, interval=0)

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
print('polling end\n')
