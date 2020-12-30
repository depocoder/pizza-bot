# pizza-bot
 
 
Этот проект позволяет создать своего телеграм бота для ресторанов пицц (Telegram, Facebook). Этого бота еще нужно улучшать, стандарты MVP выполнены.
Бот работает на [CMS](https://www.elasticpath.com/).  
    
## О фейсбук боте
Бот с минимальным функционалом, в отличие от телеграм бота, его надо допиливать.   
Если хотите запустить бота делайте это через [ngrok](https://ngrok.com/) на своем ПК или деплойте на [heroku](https://dashboard.heroku.com/apps) к примеру.

## О телеграм боте
Весь функционал полностью исправен и отлажен, подключена платежка. На данном этапе бот почти готов для прода. Для телеграм бота не нужен ngrok, можете его запускать на своем пк или деплойте на [heroku](https://dashboard.heroku.com/apps) к примеру.
     
## Заполнение Flow
Перед началом работы вам надо вручную создать Flow ваших пиццерий с `slug = pizzeria` указанным ниже.   
Дальше создаете поля для Flow. Поля указаны в формате `slug - тип данных`.     
`address` - str,	`alias` - str,	`Longitude` - float,	`Latitude` - float,	`courier_id_telegram` - str         
`courier_id_telegram` - Указывайте `Required Field` - `No`. Позже укажите id курьеров для всех ваших пиццерий в этом поле.    
создать Flow для ваших покупателей с `slug = customer_address`          
`latitude` - float, 	`longitude` - float    
      
## Подготовка к запуску Mac OS    
Сначала зарегестрируйтесь на [redis](https://redis.io/)     
Уставновить [Python 3+](https://www.python.org/downloads/)

Установить, создать и активировать виртуальное окружение

```
pip3 install virtualenv
python3 -m venv env
source env/bin/activate
```

Установить библиотеки командой

```
pip3 install -r requirements.txt
```
Загрузка меню и адресов в CMS      
```
python3 upload.py       
```
Запуск бота   

```
python3 tg_bot.py
python3 app.py
```

Создайте файл ".env" в него надо прописать ваши token'ы.   
В переменную `TG_TOKEN` его можно получить в отце всех ботов @botfather в телеграме.    
В переменную `MOTLIN_CLIENT_ID` его можно получить после регистрации на [сайте](https://www.elasticpath.com/request-free-trial).    
В переменную `MOTLIN_CLIENT_SECRET` его можно получить после регистрации на [сайте](https://www.elasticpath.com/request-free-trial).    
В переменную `REDIS_HOST` адрес базы данных.    
В переменную `REDIS_PORT` порт базы данных.    
В переменную `REDIS_PASSWORD` пароль от базы данных.    
В переменную `YANDEX_GEOCODER` полезный гайд как его получить [сайте](https://devman.org/encyclopedia/api-docs/yandex-geocoder-api/).    
В переменную `TRANZZO_TOKEN` меню payments у BotFather /mybots, выберите бота, Payments. Выбрать банк и получить тестовый токен.    
В переменную `FB_PAGE_ACCESS_TOKEN` его надо получить [тут](https://developers.facebook.com/apps/1000505683769580/messenger/settings/).    
В переменную `FB_VERIFY_TOKEN` случайное значение для синхронизации в FB.    
    
**Пример**  
```
TG_TOKEN=1499092860:AAEcuJMYVUCxS36fEiWgov3DyLbFXjUDBmY
MOTLIN_CLIENT_ID=gqZ3frdWUpxnfnKaQzTJn5cfL4WwSGAYgHMke7mz8d
MOTLIN_CLIENT_SECRET=lsbe7iCNANxS2tU25DHcoHYTBq3fqmPeEss3UwapTG
REDIS_HOST=redis-14295.c92.us-east-1-3.ec2.cloud.redislabs.com
REDIS_PORT=144895
REDIS_PASSWORD=s2aH9KMoj24afChrCtOxxKbdvwRO2hSR
YANDEX_GEOCODER=b8f9b3eb-bb4c-4eb1-129e-68369f9d7ebe
TRANZZO_TOKEN=410694247:TEST:66734346-4a12-4092-b816-92cb0744489e
FB_PAGE_ACCESS_TOKEN=EAAON9GfseOwBAGxyWIbv32ZAh42pFbAQo2YfAVnUMPgZApfWhmG6HngL7yh8pQtJVtchGTLrW3dpZC08qQNKYOEGGKqaUkICzB9wiWSmHhepXRdD9J1IGggQZCrZBHWoBKwPZBg5kJYBIZAYiweqtKrAuwWyWmUlj1yK8PbBzErZAQZDZD
FB_VERIFY_TOKEN=23112314213241241
```
