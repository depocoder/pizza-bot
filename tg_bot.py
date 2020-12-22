import os
import textwrap

from loguru import logger
from dotenv import load_dotenv
from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup, Update, LabeledPrice, ShippingOption)
from telegram.ext import (
    Filters, Updater, CallbackQueryHandler, CommandHandler, MessageHandler, CallbackContext,
    PreCheckoutQueryHandler, ShippingQueryHandler)
import redis
from geopy import distance

from motlin_api import (
    get_products, get_access_token, get_element_by_id,
    get_image_link, add_to_cart, get_cart, delete_from_cart,
    get_all_entries, create_an_entry)
from yandex_api import fetch_coordinates


def create_customer_adreess(redis_conn, lat, lon):
    access_token = get_access_token(redis_conn)

    data = {
        "data": {
            "type": "entry",
            "latitude": lat,
            "longitude": lon
            }
        }
    create_an_entry(
            access_token, data, "customer_address")


def format_description(product_info):
    """Формотирует описание для пиццы"""
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


def format_cart(cart, context):
    """Форматирует корзину"""
    filtred_cart = []
    pizza_names = []
    pizza_ids = []

    for pizza in cart['data']:
        filtred_cart.append(
            {
                'name': pizza['name'],
                "description": pizza['description'],
                'price': pizza['meta']['display_price']['without_tax']['unit']['formatted'],
                'total': pizza['meta']['display_price']['without_tax']['value']['formatted'],
                'quantity': pizza['quantity']
                        }
                    )

        pizza_names.append(pizza["name"])
        pizza_ids.append(pizza["id"])

    total_to_pay = cart['meta']['display_price']['without_tax']['amount']
    text_message = ''

    for pizza in filtred_cart:
        text_message += f'''\

                        {pizza["name"]}
                        {pizza['description']}
                        Стоимость пиццы {pizza['price']}
                        {pizza['quantity']} пицц в корзине на сумму {pizza['total']}

                        '''

    context.user_data.update({"pizza_cost": total_to_pay})
    text_message += f'к оплате {total_to_pay}'
    return textwrap.dedent(text_message), pizza_names, pizza_ids


def start(update: Update, context: CallbackContext):
    """Выводит все товары"""
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
    """Показывает корзину"""
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

    text_message, pizza_names, pizza_ids = format_cart(cart, context)
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
    """Отправляет по хэндлам"""
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
            text="Отправьте мне вашу локацию или адрес", chat_id=chat_id)
        return "HANDLE_WAITING"

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


def get_min_distance(distance):
    return distance['distance']


def get_near_entry(current_pos, redis_conn):
    """Возвращает ближайщую пиццерию и расстояние до неё в км"""
    distances = []
    access_token = get_access_token(redis_conn)
    distances = []
    entries = get_all_entries(access_token)['data']

    for entry in entries:
        distances.append({
            "entry": entry,
            "distance": distance.distance(
                (entry['latitude'], entry['longitude']), current_pos).km
                    }
                        )
    min_entry = min(distances, key=get_min_distance)
    return min_entry['entry'], min_entry['distance']


def generate_message_dilivery(update, context, entry, min_distance):
    if min_distance <= 0.5:
        text_message = (
            f'''\
            Может, заберете пиццу у нашей пиццерии неподалёку?
            Она всего в {int(min_distance*100)} метрах от вас!
            Вот её адрес: {entry['address']}.

            А можем доставить бесплатно нам не сложно!
            ''')
        context.user_data.update({"price_delivery": 0})
        can_we_deliver = True

    elif min_distance <= 5:
        text_message = (
            '''\
            Похоже ехать до вас придется на самокате.
            Доставка будет стоить 100р. Доставляем или самовывоз?
            ''')
        can_we_deliver = True
        context.user_data.update({"price_delivery": 100})

    elif min_distance <= 20:
        text_message = (
            '''\
            Похоже ехать до вас придется на самокате.
            Доставка будет стоить 300р. Доставляем или самовывоз?
            ''')
        context.user_data.update({"price_delivery": 300})
        can_we_deliver = True

    else:
        text_message = (
            f'''\
            Простите, но вы слишком далеко мы пиццу не доставим.
            Ближайщая пиццерия аж в {round(min_distance)}километрах от вас!
            ''')
        can_we_deliver = False

    return textwrap.dedent(text_message), can_we_deliver


def send_the_order_to_the_courier(
        update, context, entry, user_chat_id, lat, lon):

    access_token = get_access_token(redis_conn)
    cart = get_cart(access_token, user_chat_id)
    text_message = format_cart(cart, context)[0]
    courier_id = entry['courier_id_telegram']
    context.bot.send_message(
            text=text_message,
            chat_id=courier_id)
    context.bot.send_location(
            latitude=lat,
            longitude=lon,
            chat_id=courier_id
            )


def callback_alarm(context):
    job = context.job
    text_message = (
        '''\
        Приятного аппетита! *место для рекламы*

        *сообщение что делать если пицца не пришла*
        ''')
    text_message = textwrap.dedent(text_message)
    context.bot.send_message(chat_id=job.context, text=text_message)


def handle_delivery(update: Update, context: CallbackContext):
    query = update.callback_query
    user_chat_id = update.effective_user.id
    query.answer()
    user_answer = query.data
    query.message.delete()
    user_order = context.user_data.get("user_order")

    if not user_order:
        context.bot.send_message(
            text='Произошла ошибка, возвращаю вас в корзину.',
            chat_id=user_chat_id)
        handle_cart(update, context)
        return "HANDLE_DESCRIPTION"

    if user_answer == 'Самовывоз':
        pizzeria_address = user_order['pizzeria_address']['address']
        context.bot.send_message(
            text=f'Спасибо за заказ, будем ждать вам в ресторане {pizzeria_address} Возвращаю вас в меню.',
            chat_id=user_chat_id)
        start(update, context)
        return "HANDLE_MENU"

    else:
        start_with_shipping_callback(update, context)
        return 'HANDLE_MENU'


def start_with_shipping_callback(update: Update, context: CallbackContext):
    chat_id = update.effective_user.id
    title = "Оплата пиццы"
    description = "Оплата пиццы из ресторана DDOS PIZZA"
    payload = "Custom-Payload"
    provider_token = os.getenv('TRANZZO_TOKEN')
    start_parameter = "test-payment"
    currency = "RUB"
    price_delivery = context.user_data.get("price_delivery")
    pizza_cost = context.user_data.get("pizza_cost")
    price = pizza_cost + price_delivery
    prices = [LabeledPrice("Test", price * 100)]

    context.bot.send_invoice(
        chat_id,
        title,
        description,
        payload,
        provider_token,
        start_parameter,
        currency,
        prices,
        need_name=True,
        need_phone_number=True,
        need_email=True,
        need_shipping_address=True,
        is_flexible=True,
    )


def shipping_callback(update: Update, context: CallbackContext):
    query = update.shipping_query
    if query.invoice_payload != 'Custom-Payload':
        query.answer(
            ok=False, error_message="Что-то сломалось.")
    options = list()
    options.append(ShippingOption('1', 'Shipping Option A', [LabeledPrice('A', 100)]))
    price_list = [LabeledPrice('B1', 150), LabeledPrice('B2', 200)]
    options.append(ShippingOption('2', 'Shipping Option B', price_list))
    query.answer(ok=True, shipping_options=options)


def precheckout_callback(update: Update, context: CallbackContext):
    query = update.pre_checkout_query
    if query.invoice_payload != 'Custom-Payload':
        query.answer(ok=False, error_message="ОШИБКА! Возвращаю в меню!")
        start(update, context)
    else:
        query.answer(ok=True)


def successful_payment_callback(update: Update, context: CallbackContext):
    user_chat_id = update.effective_user.id
    context.bot.send_message(
        text='Оплата успешно прошла! Отправили информацию курьеру!',
        chat_id=user_chat_id)

    user_order = context.user_data.get("user_order")
    lat = user_order['lat']
    lon = user_order['lon']
    create_customer_adreess(redis_conn, lat, lon)
    entry = user_order['pizzeria_address']
    send_the_order_to_the_courier(
        update, context, entry, user_chat_id, lat, lon)
    start(update, context)
    context.job_queue.run_once(
        callback_alarm, 3600, context=user_chat_id, name=str(user_chat_id))


def handle_waiting(update: Update, context: CallbackContext):
    if update.message.text:
        try:
            current_pos = fetch_coordinates(
                os.getenv('YANDEX_GEOCODER'), update.message.text)
            current_pos = [float(didgit) for didgit in current_pos]
            lon, lat = current_pos
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
        lat, lon = (message.location.latitude, message.location.longitude)

    entry, min_distance = get_near_entry([lat, lon], redis_conn)
    text_message, can_we_deliver = generate_message_dilivery(
        update, context, entry, min_distance)
    keyboard = [
        [InlineKeyboardButton('В меню', callback_data='В меню')]]

    if not can_we_deliver:
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(
            text=text_message,
            chat_id=update.effective_user.id,
            reply_markup=reply_markup)
        return "HANDLE_DESCRIPTION"

    user_order = {
        'lat': lat,
        'lon': lon,
        'pizzeria_address': entry}
    context.user_data.update({"user_order": user_order})

    keyboard = [
        [InlineKeyboardButton('Самовывоз', callback_data='Самовывоз')],
        [InlineKeyboardButton(
            'Доставка', callback_data='{user_order}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        text=text_message, chat_id=update.effective_user.id,
        reply_markup=reply_markup)
    return "HANDLE_DELIVERY"


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
        'HANDLE_WAITING': handle_waiting,
        'HANDLE_DELIVERY': handle_delivery,
        "PRECHECKOUT_CALLBACK": precheckout_callback,
    }

    state_handler = states_functions[user_state]
    next_state = state_handler(update, context)
    redis_conn.set(chat_id, next_state)


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
    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    dispatcher.add_handler(ShippingQueryHandler(shipping_callback))
    dispatcher.add_handler(MessageHandler(Filters.successful_payment, successful_payment_callback))
    dispatcher.add_handler(MessageHandler(Filters.location, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))

    updater.start_polling()


if __name__ == '__main__':
    main()
