import requests as reqs
import json
import datetime as dt
import telebot
import threading
import os

from telebot import types
from timeloop import Timeloop
from datetime import timedelta

token = ''
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
    for item in data:
        raw += item + ','
    raw += '\n'
    if currency == 'USD':
        csv = open(usdCsvDir + date + '.csv', 'a')
        csv.write(raw)
        csv.close()
    if currency == 'EUR':
        csv = open(eurCsvDir + date + '.csv', 'a')
        csv.write(raw)
        csv.close()

# Получение курса валюты
def getCourse():
    # Запрос курса валюты
    getCourseUrl = 'https://www.vtb.ru/api/currency-exchange/table-info?contextItemId=%7BC5471052-2291-4AFD-9C2D-1DBC40A4769D%7D&conversionPlace=1&conversionType=1&renderingId=ede2e4d0-eb6b-4730-857b-06fd4975c06b&renderingParams=LegalStatus__%7BF2A32685-E909-44E8-A954-1E206D92FFF8%7D;IsFromRuble__1;CardMaxPeriodDays__5;CardRecordsOnPage__5;ConditionsUrl__%2Fpersonal%2Fplatezhi-i-perevody%2Fobmen-valjuty%2Fspezkassy%2F;Multiply100JPYand10SEK__1'
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
