import os
import json
import redis

from pprint import pprint
from dotenv import load_dotenv
from loguru import logger
import requests
from flask import Flask, request

from motlin_api import (
    get_access_token, get_image_link,
    get_products_by_category_id, get_all_categories)
from motlin_api import (
    get_products, get_access_token, get_element_by_id,
    get_image_link, add_to_cart, get_cart, delete_from_cart,
    get_all_entries, create_an_entry)

app = Flask(__name__)


def handle_start(sender_id, payload):
    if payload is None:
        payload = '68ff879e-9b22-4cab-ab32-23cac76a40d9'
    keyboard_elements = get_keyboard_products(sender_id, payload)
    pprint(keyboard_elements)
    send_keyboard(sender_id, keyboard_elements)
    return "HANDLE_DESCRIPTION"


def handle_description(sender_id, payload):
    """Отправляет по хэндлам"""
    if payload is not None:
        title = payload['title']
        payload = payload['payload']
    else:
        title, payload = None, None
    access_token = get_access_token(redis_conn)

    if title in ['В меню', 'Сытные', 'Основные']:
        handle_start(sender_id, payload)
        return 'HANDLE_DESCRIPTION'

    elif title == 'Корзина':
        handle_cart(sender_id, payload)
        return "HANDLE_DESCRIPTION"

    elif title in ['Оплатить', 'Доставка', 'Самовывоз']:
        send_message(sender_id, "Эта функция пока не доступна!")
        return "HANDLE_WAITING"

    elif title == 'Убрать из корзины':
        delete_from_cart(access_token, payload, sender_id)
        handle_cart(sender_id, payload)
        return "HANDLE_DESCRIPTION"
    elif title in ['Положить в корзину', 'Добавить еще одну']:
        send_message(sender_id, f"Добавлена payload - {title}{payload}")
        add_to_cart(access_token, 1, payload, sender_id)
        return 'HANDLE_DESCRIPTION'
    return 'HANDLE_DESCRIPTION'
    


def format_cart(cart):
    """Форматирует корзину"""
    keyboard_cart = []
    for pizza in cart['data']:
        pprint(pizza)
        keyboard_cart.append(
            {
                'title': pizza['name'],
                'subtitle': pizza['description'],
                'image_url': pizza['image']['href'],
                'buttons': [
                    {
                        'type': 'postback',
                        'title': 'Добавить еще одну',
                        'payload': pizza["id"],
                    },
                    {
                        'type': 'postback',
                        'title': 'Убрать из корзины',
                        'payload': pizza["id"],
                    }
                ]
            })

    total_to_pay = cart['meta']['display_price']['without_tax']['amount']
    return keyboard_cart, total_to_pay


def handle_cart(sender_id, payload):
    """Показывает корзину"""
    access_token = get_access_token(redis_conn)
    cart = get_cart(access_token, sender_id)

    if not cart['data']:
        send_keyboard(
            sender_id,
            {
                'title': "Ваша корзина пуста :C",
                'buttons': [
                    {
                        'type': 'postback',
                        'title': 'В меню',
                        'payload': "68ff879e-9b22-4cab-ab32-23cac76a40d9",
                    },
                ]
            })
        return "HANDLE_DESCRIPTION"
    keyboard_cart, total_to_pay = format_cart(cart)
    keyboard_elements = [
        {
                'title': f"Ваш заказ на сумму {total_to_pay}",
                'image_url': 'https://internet-marketings.ru/wp-content/uploads/2018/08/idealnaya-korzina-internet-magazina-1068x713.jpg',
                'buttons': [
                    {
                        'type': 'postback',
                        'title': 'Доставка',
                        'payload': 'Кнопка не работает',
                    },
                    {
                        'type': 'postback',
                        'title': 'Самовывоз',
                        'payload': 'Кнопка не работает',
                    },
                    {
                        'type': 'postback',
                        'title': 'В меню',
                        'payload': "68ff879e-9b22-4cab-ab32-23cac76a40d9",
                    },
                ]
        }
    ]
    keyboard_elements += keyboard_cart
    send_keyboard(sender_id, keyboard_elements)
    return "HANDLE_DESCRIPTION"


def handle_users_reply(sender_id, payload):
    states_functions = {
        'START': handle_start,
        'HANDLE_DESCRIPTION': handle_description,
    }

    recorded_state = redis_conn.get(f"fb-{sender_id}")
    if recorded_state not in states_functions.keys():
        user_state = "START"
    else:
        user_state = recorded_state

    state_handler = states_functions[user_state]
    next_state = state_handler(sender_id, payload)
    redis_conn.set(f"fb-{sender_id}", next_state)


@app.route('/', methods=['POST'])
def webhook():
    """
    Основной вебхук, на который будут приходить сообщения от Facebook.
    """
    data = request.get_json()
    if data["object"] == "page":
        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                postback = messaging_event.get("postback")
                if postback:
                    pprint(postback)
                    payload = {}
                    payload['payload'] = postback['payload']
                    payload['title'] = postback['title']
                else:
                    payload = None
                if messaging_event.get("message") or postback:  # someone sent us a message
                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    handle_users_reply(sender_id, payload)
    return "ok", 200


@app.route('/', methods=['GET'])
def verify():
    """
    При верификации вебхука у Facebook он отправит запрос на этот адрес. На него нужно ответить VERIFY_TOKEN.
    """
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.getenv("VERIFY_TOKEN"):
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


def get_keyboard_products(sender_id, category_id):
    keyboard_elements = [{
                'title': 'Меню',
                'subtitle': "Здесь вы можете выбрать один из вариантов",
                'image_url': 'https://image.similarpng.com/very-thumbnail/2020/05/Pizza-logo-design-template-Vector-PNG.png',
                'buttons': [
                    {
                        'type': 'postback',
                        'title': 'Корзина',
                        'payload': sender_id,
                    },
                    {
                        'type': 'postback',
                        'title': 'Акции',
                        'payload': 'some text',
                    },
                    {
                        'type': 'postback',
                        'title': 'Сделать заказ',
                        'payload': 'some text',
                    }
                ]
            }]
    access_token = get_access_token(redis_conn)
    products = get_products_by_category_id(access_token, category_id)['data']
    for product in products:
        image_id = product['relationships']['main_image']['data']['id']
        access_token = get_access_token(redis_conn)
        image_link = get_image_link(access_token, image_id)['data']['link']['href']
        keyboard_elements.append(
            {
                'title': product['name'] + ' ' + product['meta']['display_price']['with_tax']['formatted'],
                'subtitle': product['description'],
                'image_url': image_link,
                'buttons': [
                    {
                        'type': 'postback',
                        'title': 'Положить в корзину',
                        'payload': product['id'],
                    }
                ]
            }
        )

    categories = get_all_categories(access_token)['data']
    keyboard_elements.append(
            {
                'title': 'Не нашли нужную пиццу?',
                'subtitle': 'Остальные пиццы можно посмотреть в одной из категории',
                'image_url': 'https://primepizza.ru/uploads/position/large_0c07c6fd5c4dcadddaf4a2f1a2c218760b20c396.jpg',
                'buttons': [
                    {
                        'type': 'postback',
                        'title': category['name'],
                        'payload': category['id'],
                    } for category in categories if category['id'] != category_id]
            }
    )
    return keyboard_elements


def send_keyboard(sender_id, keyboard_elements):
    params = {"access_token": os.getenv("PAGE_ACCESS_TOKEN")}
    headers = {"Content-Type": "application/json"}

    data = json.dumps({
        'recipient': {
            "id": sender_id
        },
        'message': {
            'attachment': {
                'type': 'template',
                'payload': {
                    'template_type': 'generic',
                    'elements': keyboard_elements
                }
            }
        }
    })
    response = requests.post(
        'https://graph.facebook.com/v2.6/me/messages',
        headers=headers,
        params=params,
        data=data
        )

    pprint(response.json())
    response.raise_for_status()


def send_message(sender_id, message_text):
    params = {"access_token": os.getenv("PAGE_ACCESS_TOKEN")}
    headers = {"Content-Type": "application/json"}
    request_content = json.dumps({
        "recipient": {
            "id": sender_id
        },
        "message": {
            "text": message_text
        }
    })
    response = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=request_content)
    response.raise_for_status()


@logger.catch
def main():
    load_dotenv()
    global redis_conn
    redis_conn = redis.Redis(
        host=os.getenv('REDIS_HOST'), password=os.getenv('REDIS_PASSWORD'),
        port=os.getenv('REDIS_PORT'), db=0, decode_responses=True)
    app.run(debug=True, host='0.0.0.0', port=80)


if __name__ == '__main__':
    main()
