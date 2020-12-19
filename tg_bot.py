import os
import textwrap
from pprint import pprint
from operator import itemgetter

from loguru import logger
from requests.exceptions import HTTPError
from validate_email import validate_email
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Filters, Updater
from telegram.ext import (
    CallbackQueryHandler, CommandHandler, MessageHandler, CallbackContext)
import redis
from geopy import distance

from motlin_api import (
    get_products, get_access_token, get_element_by_id,
    get_image_link, add_to_cart, get_cart, delete_from_cart, create_customer,
    get_all_entrys)
from yandex_api import fetch_coordinates


def format_description(product_info):
    name = product_info['name']
    description = product_info['description']
    price = product_info['meta']['display_price']['with_tax']['formatted']
    text_mess = (
        f'''\
        {name}
        Стоимость: {price}

        {description}
        ''')
    return textwrap.dedent(text_mess)


def format_cart(cart):
    filtred_cart = []
    pizza_names = []
    pizza_ids = []
    for pizza in cart['data']:
        filtred_cart.append({
            'name': pizza['name'],
            "description": pizza['description'],
            'price': pizza['meta']['display_price']['without_tax']['unit']['formatted'],
            'total': pizza['meta']['display_price']['without_tax']['value']['formatted'],
            'quantity': pizza['quantity']

        })
        pizza_names.append(pizza["name"])
        pizza_ids.append(pizza["id"])
    total_to_pay = cart['meta']['display_price']['without_tax']['formatted']
    text_message = ''
    for pizza in filtred_cart:
        text_message += (
            f'''\

            {pizza["name"]}
            {pizza['description']}
            Стоимость пиццы {pizza['price']}
            {pizza['quantity']} пицц в корзине на сумму {pizza['total']}

            ''')
    text_message += f'{total_to_pay}'
    return textwrap.dedent(text_message), pizza_names, pizza_ids


def start(update: Update, context: CallbackContext):
    access_token = get_access_token(redis_conn)
    keyboard_product = [
        [InlineKeyboardButton(product['name'], callback_data=product['id'])] for product in get_products(access_token)]
    keyboard_product.append(
        [InlineKeyboardButton('Корзина', callback_data='Корзина')])
    reply_markup = InlineKeyboardMarkup(keyboard_product)

    context.bot.send_message(
        text='Пожалуйста выберите: ', chat_id=update.effective_user.id,
        reply_markup=reply_markup)
    return 'HANDLE_MENU'


def handle_cart(update: Update, context: CallbackContext):
    access_token = get_access_token(redis_conn)
    chat_id = update.effective_user.id
    cart = get_cart(access_token, chat_id)
    keyboard = []
    keyboard.append([InlineKeyboardButton('В меню', callback_data='В меню')])

    if not cart['data']:
        text_message = 'Ваша корзина пуста :C'
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(
            text=text_message, chat_id=chat_id, reply_markup=reply_markup)
        return "HANDLE_DESCRIPTION"

    text_message, pizza_names, pizza_ids = format_cart(cart)
    for name_pizza, id_pizza in zip(pizza_names, pizza_ids):
        keyboard.append(
            [InlineKeyboardButton(
                f'Убрать из корзины {name_pizza}',
                callback_data=f'Убрать|{id_pizza}')])

    keyboard.append([InlineKeyboardButton(
        'Оплатить', callback_data='Оплатить')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        text=text_message, chat_id=chat_id, reply_markup=reply_markup)
    return "HANDLE_DESCRIPTION"


def handle_description(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    access_token = get_access_token(redis_conn)
    chat_id = update.effective_user.id
    if query.data == 'В меню':
        start(update, context)
        query.message.delete()
        return 'HANDLE_MENU'
    elif query.data == 'Корзина':
        handle_cart(update, context)
        query.message.delete()
        return "HANDLE_DESCRIPTION"
    elif query.data == 'Оплатить':
        query.message.delete()
        context.bot.send_message(
            text='Пожалуйста укажите ваш email пример "myemail@gmail.com"',
            chat_id=chat_id)
        return "WAITING_EMAIL"
    elif 'Убрать' in query.data:
        item_id = query.data.split("|")[1]
        delete_from_cart(access_token, item_id, chat_id)
        handle_cart(update, context)
        query.message.delete()
        return "HANDLE_DESCRIPTION"
    item_id = query.data
    add_to_cart(access_token, 1, item_id, chat_id)
    context.bot.send_message(
        text='added', chat_id=chat_id)
    return 'HANDLE_DESCRIPTION'


def get_near_entry(current_pos, redis_conn):
    distances = []
    current_pos = [float(didgit) for didgit in current_pos]
    access_token = get_access_token(redis_conn)
    entrys = get_all_entrys(access_token)['data']
    for entry in entrys:
        distances.append(distance.distance(
            (float(entry['3']), float(entry['4'])), current_pos).km)
    min_distance = min(distances)
    index_near_entry = distances.index(min_distance)
    return entrys[index_near_entry], min_distance


def generate_message_dilivery(update, context, entry, min_distance):
    if min_distance <= 0.5:
        text_message = (
            f'''\
            Может, заберете пиццу у нашей пиццерии неподалёку?
            Она всего в {int(min_distance*100)} метрах от вас!
            Вот её адрес: {entry['1']}.

            А можем доставить бесплатно нам не сложно!
            ''')
    elif min_distance <= 5:
        text_message = (
            '''\
            Похоже ехать до вас придется на самокате.
            Доставка будет стоить 100р. Доставляем или самовывоз?
            ''')
    elif min_distance <= 20:
        text_message = (
            '''\
            Похоже ехать до вас придется на самокате.
            Доставка будет стоить 300р. Доставляем или самовывоз?
            ''')
    else:
        text_message = (
            f'''\
            Простите, но вы слишком далеко мы пиццу не доставим.
            Ближайщая пиццерия аж в {round(min_distance)}километрах от вас!
            ''')
    return textwrap.dedent(text_message)



def handle_waiting(update: Update, context: CallbackContext):
    if update.message.text:
        try:
            current_pos = fetch_coordinates(
                os.getenv('YANDEX_GEOCODER'), update.message.text)
        except IndexError:
            context.bot.send_message(
                text='Вы указали неправильно данные, попробуйте снова.',
                chat_id=update.effective_user.id)
            return "HANDLE_WAITING"
    else:
        message = None
        if update.edited_message:
            message = update.edited_message
        else:
            message = update.message
        current_pos = (message.location.latitude, message.location.longitude)
    entry, min_distance = get_near_entry(current_pos, redis_conn)
    text_message = generate_message_dilivery(
        update, context, entry, min_distance)
    context.bot.send_message(
        text=text_message,
        chat_id=update.effective_user.id)
    return "HANDLE_WAITING"



def handle_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.message.delete()
    if query.data == 'Корзина':
        handle_cart(update, context)
        return "HANDLE_DESCRIPTION"
    access_token = get_access_token(redis_conn)
    product_info = get_element_by_id(access_token, query.data)
    image_id = product_info['relationships']['main_image']['data']['id']
    text_mess = format_description(product_info)
    image_link = get_image_link(access_token, image_id)['data']['link']['href']
    keyboard = [
        [InlineKeyboardButton('В меню', callback_data='В меню')],
        [InlineKeyboardButton(
            'Положить в корзину', callback_data=query.data)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_photo(
        chat_id=update.effective_user.id, photo=image_link,
        caption=text_mess, reply_markup=reply_markup)['message_id']
    return "HANDLE_DESCRIPTION"


def waiting_email(update: Update, context: CallbackContext):
    users_reply = update.message.text
    is_valid = validate_email(users_reply)
    if is_valid:
        access_token = get_access_token(redis_conn)
        try:
            create_customer(
                access_token, str(update.effective_user.id), users_reply)
        except HTTPError:
            update.message.reply_text('Ошибка такой Email уже указывали!')
            return "WAITING_EMAIL"
        update.message.reply_text(
            f"Вы прислали мне эту почту - {users_reply}. Мы скоро свяжемся.")
        update.message.reply_text("Отправьте мне вашу локацию или адрес")
        return "HANDLE_WAITING"
    update.message.reply_text(f"Ошибка! неверный email - '{users_reply}'")
    return "WAITING_EMAIL"


def handle_users_reply(update: Update, context: CallbackContext):
    chat_id = update.effective_user.id
    if update.message:
        user_reply = update.message.text
    elif update.callback_query:
        user_reply = update.callback_query.data
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = redis_conn.get(chat_id)

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
        'WAITING_EMAIL': waiting_email,
        'HANDLE_WAITING': handle_waiting,
    }
    state_handler = states_functions[user_state]
    next_state = state_handler(update, context)
    redis_conn.set(chat_id, next_state)


def location(update: Update, context: CallbackContext):
    message = None
    if update.edited_message:
        message = update.edited_message
    else:
        message = update.message
    current_pos = (message.location.latitude, message.location.longitude)
    context.bot.send_message(
        text=current_pos, chat_id=update.effective_user.id)


def error_handler(update: Update, context: CallbackContext):
    logger.error(_Logger__message=context.error)


@logger.catch
def main():
    load_dotenv()
    global redis_conn
    redis_conn = redis.Redis(
        host=os.getenv('REDIS_HOST'), password=os.getenv('REDIS_PASSWORD'),
        port=os.getenv('REDIS_PORT'), db=0, decode_responses=True)
    updater = Updater(token=os.getenv("TG_TOKEN"), use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_error_handler(error_handler)
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.location, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    updater.start_polling()


if __name__ == '__main__':
    main()
