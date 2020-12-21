# pizza-bot
 
 
Этот проект позволяет создать своего телеграм бота для ресторанов пицц (Telegram). Этого бота еще нужно улучшать, стандарты MVP выполнены.
Бот работает на [CMS](https://www.elasticpath.com/).    
     
## Заполнение Flow
Перед началом работы вам надо вручную создать Flow ваших пиццерий с `slug = 1`    
И со всеми полями ниже, в этом же порядке `slug от 1 до 5`, обязательно укажите тип данных     
`Address` тип данных str,	`Alias` тип данных str,	`Longitude` тип данных float,	`Latitude` тип данных float,	`courier id telegram` тип данных str         
`courier id telegram` - Указывайте `Required Field` - `No`    
Позже укажите id курьеров для всех ваших пиццерий    
создать Flow для ваших покупателей с `slug = 2`     
И со всеми полями ниже, в этом же порядке `slug от 1 до 2`     
`Latitude` тип данных float, 	`Longitude` тип данных float    
      
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
```

Создайте файл ".env" в него надо прописать ваши token'ы.   
В переменную `TG_TOKEN` его можно получить в отце всех ботов @botfather в телеграме.    
В переменную `MOTLIN_CLIENT_ID` его можно получить после регистрации на [сайте](https://www.elasticpath.com/request-free-trial).    
В переменную `MOTLIN_CLIENT_SECRET` его можно получить после регистрации на [сайте](https://www.elasticpath.com/request-free-trial).    
В переменную `REDIS_HOST` адрес базы данных.    
В переменную `REDIS_PORT` порт базы данных.    
В переменную `REDIS_PASSWORD` пароль от базы данных.    
В переменную `YANDEX_GEOCODER` полезный гайд как его получить [сайте](https://devman.org/encyclopedia/api-docs/yandex-geocoder-api/).    
В переменную `TRANZZO_TOKEN` Меню Payments у BotFather /mybots, выберите бота, Payments. Выбрать банк и получить тестовый токен.    
    
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
```
