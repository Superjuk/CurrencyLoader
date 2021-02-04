import requests as reqs
import json
import datetime as dt
import telebot
import threading
import os
import configparser as cp
import time

from telebot import types
from multiprocessing import Value
from timeloop import Timeloop
from datetime import timedelta
from requests.models import Response

# Инициализация #
config = cp.ConfigParser(interpolation=None)
config.read('settings.conf')

# Сохранение в конфиг
def saveToConfig(file = 'settings.conf', config = config):
    with open(file, 'w') as configfile:
        config.write(configfile)

# Запись в конфиг
def commitToConfig(section, key, value, config = config):
    config[section][key] = value

# Загрузка из конфига
def getFromConfig(section, key, defaultValue, config = config):
    try:
        return config[section][key]
    except KeyError:
        return defaultValue

# Загрузка даты/времени UTC из конфига
def getDateTimeFromConfig(section, key, defaultValue, config = config):
    return dt.datetime.fromtimestamp(float(getFromConfig(section, key, defaultValue, config)))

# Чтение конфига
getCourseUrl = getFromConfig('main', 'url', '')
token = getFromConfig('telegram', 'token', 'Empty-Token')
lastDateTime = getDateTimeFromConfig('tmp', 'lastDateTime', 0)
lastUsdSell = float(getFromConfig('tmp', 'lastUsdSell', 0.01))
lastUsdBuy = float(getFromConfig('tmp', 'lastUsdBuy', 0.01))
lastEurSell = float(getFromConfig('tmp', 'lastEurSell', 0.01))
lastEurBuy = float(getFromConfig('tmp', 'lastEurBuy', 0.01))
# users = config['subscribe']['users'].split(',')
# config['subscribe']['users']='12,13,14'
# with open('settings.conf', 'w') as configfile:
#     config.write(configfile)

bot = telebot.TeleBot(token)

usdSell = Value('d', lastUsdSell)
eurSell = Value('d', lastEurSell)

usdCsvDir = os.getcwd()+'\\USD\\'
if not os.path.exists(usdCsvDir):
    os.mkdir(usdCsvDir)

eurCsvDir = os.getcwd()+'\\EUR\\'
if not os.path.exists(eurCsvDir):
    os.mkdir(eurCsvDir)

rubleSign = '\u20bd'
eurSign = '\u20ac'
usdSign = '\u0024'

tempDateUsd = lastDateTime
tempDateEur = lastDateTime

usdRate = []
eurRate = []

users = []

setUsdLimitFlag = False
setEurLimitFlag = False

# Создание кнопок
getCourseButtonSet = types.InlineKeyboardMarkup()
currentCourseBtn = types.InlineKeyboardButton(text='Показать курс', callback_data='current')
getCourseButtonSet.add(currentCourseBtn)

subscribeButtonsSet = types.InlineKeyboardMarkup()
subscribeAllBtn = types.InlineKeyboardButton(text='всё', callback_data='sub_all')
subscribeUsdBtn = types.InlineKeyboardButton(text='доллары', callback_data='sub_usd')
subscribeEurBtn = types.InlineKeyboardButton(text='евро', callback_data='sub_eur')
subscribeButtonsSet.add(subscribeUsdBtn)
subscribeButtonsSet.add(subscribeEurBtn)
subscribeButtonsSet.add(subscribeAllBtn)

unsubscribeButtonsSet = types.InlineKeyboardMarkup()
unsubscribeAllBtn = types.InlineKeyboardButton(text='всего', callback_data='unsub_all')
unsubscribeUsdBtn = types.InlineKeyboardButton(text='долларов', callback_data='unsub_usd')
unsubscribeEurBtn = types.InlineKeyboardButton(text='евро', callback_data='unsub_eur')
unsubscribeButtonsSet.add(unsubscribeUsdBtn)
unsubscribeButtonsSet.add(unsubscribeEurBtn)
unsubscribeButtonsSet.add(unsubscribeAllBtn)

menuButtonsSet = types.InlineKeyboardMarkup()
menuSubBtn = types.InlineKeyboardButton(text='Подписка', callback_data='subscribe')
menuUnsubBtn = types.InlineKeyboardButton(text='Отписка', callback_data='unsubscribe')
menuInfoBtn = types.InlineKeyboardButton(text='Информирование', callback_data='inform')
menuExitBtn = types.InlineKeyboardButton(text='Выход из настроек', callback_data='exit_settings')
menuButtonsSet.add(menuSubBtn)
menuButtonsSet.add(menuUnsubBtn)
menuButtonsSet.add(menuInfoBtn)
menuButtonsSet.add(menuExitBtn)

infoButtonsSet = types.InlineKeyboardMarkup()
infoLimitBtn = types.InlineKeyboardButton(text='Установка предела', callback_data='limit')
infoGraphBtn = types.InlineKeyboardButton(text='График в конце дня', callback_data='graph')
infoButtonsSet.add(infoLimitBtn)
infoButtonsSet.add(infoGraphBtn)

limitButtonsSet = types.InlineKeyboardMarkup()
limitSetBtn = types.InlineKeyboardButton(text='Установить предел', callback_data='limit_set')
limitCancelBtn = types.InlineKeyboardButton(text='Отменить предел', callback_data='limit_cancel')
limitButtonsSet.add(limitSetBtn)
limitButtonsSet.add(limitCancelBtn)

graphButtonsSet = types.InlineKeyboardMarkup()
graphSetBtn = types.InlineKeyboardButton(text='Формировать график', callback_data='graph_set')
graphCancelBtn = types.InlineKeyboardButton(text='Отменить формирование', callback_data='graph_cancel')
graphButtonsSet.add(graphSetBtn)
graphButtonsSet.add(graphCancelBtn)

# Конец инициализации #

# Поиск в строке данными из массива
def findArrayInMessage(substrings, message):
    for item in substrings:
        if item in message:
            return True
    return False

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

# Конвертер валют
def convert(raw, course, currencyName):
    array = raw.split()
    if len(array) != 2:
        return 'Неверный формат данных.\n Попробуйте отправить, например, '"'100 rub'"'\n'
    return format(float(array[0]) * course, '.2f') + ' ' + currencyName + '\n'

# Сохранение настроек пользователя
def saveUserSettings(id, key, value, users = users):
    for user in users:
        if user['id'] == id:
            user[key] = value
            print(users)
            return
    users.append({'id': id, key: value})
    print(users)

# Загрузка настройки пользователя
def loadUserSettings(id, key, default=0, users = users):
    for user in users:
        if user['id'] == id:
            try:
                return user[key]
            except KeyError:
                return default
    return default

# Конвертирование текста в число с плавающей запятой
def toFloat(str):
    num = str.replace(',', '.')
    try:
        return float(num)
    except ValueError:
        return 0.0

# Форматирование результата курса в текст
def courseToText(course, rawData):
    sell = lastUsdSell
    buy  = lastUsdBuy
    if len(rawData) == 4:
        sell = rawData[2]
        buy  = rawData[3]
    elif course == 'EUR':
        sell = lastEurSell
        buy  = lastEurBuy

    result = course + ': \n'
    result += 'Продажа: ' + str(sell) + ' ' + rubleSign + '\n'
    result += 'Покупка: ' + str(buy) + ' ' + rubleSign
    return result

# Получение курса валюты
def getCourse():
    global tempDateUsd
    global tempDateEur
    global usdRate
    global eurRate
    global lastDateTime
    global lastUsdSell
    global lastUsdBuy
    global lastEurSell
    global lastEurBuy
    # Запрос курса валюты
    while True:
        try:
            resp = reqs.get(getCourseUrl)
            break
        except ConnectionError:
            time.sleep(10)
    data = resp.json()

    # Разбор полученного json
    # и запись результата в usdRate и eurRate
    usd = 'USD'
    eur = 'EUR'
    breakCount = 2
    currencies = data['GroupedRates']
    for i in range(len(currencies)):
        moneyRate = currencies[i]['MoneyRates']
        fromCurrency = moneyRate[0]['FromCurrency']
        fromCode = fromCurrency['Code']
        sell = moneyRate[0]['BankSellAt']
        buy = moneyRate[0]['BankBuyAt']
        date = dt.datetime.fromisoformat(moneyRate[0]['StartDate'])

        if fromCode == usd and tempDateUsd < date:
            with usdSell.get_lock():
                usdSell.value = sell
            usdRate.clear()
            usdRate.append(dt.datetime.now().strftime('%X'))
            usdRate.append(date.strftime('%X'))
            usdRate.append(str(sell))
            usdRate.append(str(buy))
            saveCourseToCsv(fromCode, date.strftime('%Y-%m-%d'), usdRate)
            tempDateUsd = date
            lastDateTime = date
            lastUsdSell = sell
            lastUsdBuy = buy
            breakCount -= 1

        if fromCode == eur and tempDateEur < date:
            with eurSell.get_lock():
                eurSell.value = sell
            eurRate.clear()
            eurRate.append(dt.datetime.now().strftime('%X'))
            eurRate.append(date.strftime('%X'))
            eurRate.append(str(sell))
            eurRate.append(str(buy))
            saveCourseToCsv(fromCode, date.strftime('%Y-%m-%d'), eurRate)
            tempDateEur = date
            lastDateTime = date
            lastEurSell = sell
            lastEurBuy = buy
            breakCount -= 1

        if breakCount == 0:
            commitToConfig('tmp', 'lastDateTime', str(lastDateTime.timestamp()))
            commitToConfig('tmp', 'lastUsdSell', str(lastUsdSell))
            commitToConfig('tmp', 'lastUsdBuy', str(lastUsdBuy))
            commitToConfig('tmp', 'lastEurSell', str(lastEurSell))
            commitToConfig('tmp', 'lastEurBuy', str(lastEurBuy))
            break

    result = {usd: usdRate, eur: eurRate}
    # result = usd + ': \n'
    # result += 'Продажа: ' + str(usdRate[2]) + ' ' + rubleSign + '\n'
    # result += 'Покупка: ' + str(usdRate[3]) + ' ' + rubleSign + '\n'
    # result += '----\n'

    # result += eur + ': \n'
    # result += 'Продажа: ' + str(eurRate[2]) + ' ' + rubleSign + '\n'
    # result += 'Покупка: ' + str(eurRate[3]) + ' ' + rubleSign

    return result

@bot.message_handler(commands=['start'])
def get_course(message):
    bot.send_message(message.chat.id, 'Настройка работы:', reply_markup=menuButtonsSet)

# Обработка входящего сообщения
@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    global setUsdLimitFlag
    global setEurLimitFlag
    #
    factor = 0.0
    response = ''
    #
    id = message.from_user.id
    #
    if setUsdLimitFlag:
        saveUserSettings(id, 'usdLimit', toFloat(message.text))
        setUsdLimitFlag = False
        if setEurLimitFlag:
            response = 'Установите нижний лимит для евро:'
            bot.send_message(id, response)
        else:
            response = 'Установка лимитов завершена.'
            bot.send_message(id, response, reply_markup=menuButtonsSet)
    elif setEurLimitFlag:
        saveUserSettings(id, 'eurLimit', toFloat(message.text))
        setEurLimitFlag = False
        response = 'Установка лимитов завершена.'
        bot.send_message(id, response, reply_markup=menuButtonsSet)
    elif findArrayInMessage(['rub', 'rur', 'руб'], message.text.lower()):
        factor = 1/usdSell.value
        bot.send_message(id, convert(message.text, factor, usdSign))
        factor = 1/eurSell.value
        bot.send_message(id, convert(message.text, factor, eurSign), reply_markup=getCourseButtonSet)
    elif findArrayInMessage(['usd', 'доллар'], message.text.lower()):
        factor = usdSell.value
        bot.send_message(id, convert(message.text, factor, rubleSign), reply_markup=getCourseButtonSet)
    elif findArrayInMessage(['eur', 'евро'], message.text.lower()):
        factor = eurSell.value
        bot.send_message(id, convert(message.text, factor, rubleSign), reply_markup=getCourseButtonSet)
    else:
        bot.send_message(id, 'Ошибка!', reply_markup=getCourseButtonSet)

# Обработчик нажатий на кнопки
@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    global setUsdLimitFlag
    global setEurLimitFlag
    #
    id = call.message.chat.id
    if call.data == 'current':
        data = getCourse()
        response = 'Подпишитесь хотя бы на одну валюту!'
        buttonsSet = subscribeButtonsSet
        isUsdResponse = False
        if loadUserSettings(id, 'usdSub'):
            response = courseToText('USD', data['USD'])
            isUsdResponse = True
            buttonsSet = getCourseButtonSet
        if loadUserSettings(id, 'eurSub'):
            if isUsdResponse:
                response += '\n\n'
                response += courseToText('EUR', data['EUR'])
            else:
                response = courseToText('EUR', data['EUR'])
            buttonsSet = getCourseButtonSet
        bot.send_message(id, response, reply_markup=buttonsSet)
    elif call.data == 'subscribe':
        bot.send_message(id, 'Подписаться на ...', reply_markup=subscribeButtonsSet)
    elif call.data == 'unsubscribe':
        bot.send_message(id, 'Отписаться от ...', reply_markup=unsubscribeButtonsSet)
    elif call.data == 'inform':
        bot.send_message(id, 'Информирование:', reply_markup=infoButtonsSet)
    elif call.data == 'sub_all':
        response = 'Вы подписаны на все валюты.'
        saveUserSettings(id, 'usdSub', 1)
        saveUserSettings(id, 'eurSub', 1)
        bot.send_message(id, response, reply_markup=menuButtonsSet)
    elif call.data == 'sub_usd':
        response = 'Вы подписаны на курс доллара.'
        saveUserSettings(id, 'usdSub', 1)
        bot.send_message(id, response, reply_markup=menuButtonsSet)
    elif call.data == 'sub_eur':
        response = 'Вы подписаны на курс евро.'
        saveUserSettings(id, 'eurSub', 1)
        bot.send_message(id, response, reply_markup=menuButtonsSet)
    elif call.data == 'unsub_all':
        response = 'Вы отписались от всех валют.'
        saveUserSettings(id, 'usdSub', 0)
        saveUserSettings(id, 'eurSub', 0)
        bot.send_message(id, response, reply_markup=menuButtonsSet)
    elif call.data == 'unsub_usd':
        response = 'Вы отписались от курса доллара.'
        saveUserSettings(id, 'usdSub', 0)
        bot.send_message(id, response, reply_markup=menuButtonsSet)
    elif call.data == 'unsub_eur':
        response = 'Вы отписались от курса евро.'
        saveUserSettings(id, 'eurSub', 0)
        bot.send_message(id, response, reply_markup=menuButtonsSet)
    elif call.data == 'limit':
        setUsdLimitFlag = loadUserSettings(id, 'usdSub', False)
        setEurLimitFlag = loadUserSettings(id, 'eurSub', False)
        response = 'Установите нижний лимит для доллара:'
        if not setUsdLimitFlag:
            response = 'Установите нижний лимит для евро:'
        bot.send_message(id, response)
    elif call.data == 'graph':
        response = 'Слать график в конце дня:'
        bot.send_message(id, response, reply_markup=graphButtonsSet)
    elif call.data == 'limit_set':
        response='Включено уведомление при достижении нижнего лимита.'
        saveUserSettings(id, 'usdLimit', 1)
        saveUserSettings(id, 'eurSub', 1)
        bot.send_message(id, response, reply_markup=menuButtonsSet)
    elif call.data == 'limit_cancel':
        response='Уведомления по валютам отлючены.'
        saveUserSettings(id, 'usdLimit', 0)
        saveUserSettings(id, 'eurSub', 0)
        bot.send_message(id, response, reply_markup=menuButtonsSet)
    elif call.data == 'graph_set':
        response = 'График будет формироваться в конце дня.'
        saveUserSettings(id, 'chart', 1)
        bot.send_message(id, response, reply_markup=menuButtonsSet)
    elif call.data == 'graph_cancel':
        response = 'Формирование графика отменено.'
        saveUserSettings(id, 'chart', 0)
        bot.send_message(id, response, reply_markup=menuButtonsSet)
    elif call.data == 'exit_settings':
        response = 'Настройка завершена.'
        bot.send_message(id, response, reply_markup=getCourseButtonSet)

# Запуск бота
def start_bot_polling():
    print('polling start\n')
    bot.infinity_polling(interval=0)

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
print('polling end\n')
saveToConfig()
