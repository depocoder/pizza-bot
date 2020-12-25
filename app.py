import os
import sys
import json
import redis

from pprint import pprint
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger
import requests
from flask import Flask, request

from motlin_api import (
    get_access_token, get_products, get_image_link,
    get_products_by_category_id)

app = Flask(__name__)


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


@app.route('/', methods=['POST'])
def webhook():
    """
    Основной вебхук, на который будут приходить сообщения от Facebook.
    """
    data = request.get_json()
    if data["object"] == "page":
        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                if messaging_event.get("message"):  # someone sent us a message
                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    message_text = messaging_event["message"]["text"]  # the message's text
                    send_keyboard(sender_id)
                    send_message(sender_id, message_text)
    return "ok", 200


def get_keyboard_products(category_id):
    keyboard_elements = [{ 
                'title': 'Меню',
                'subtitle': "Здесь вы можете выбрать один из вариантов",
                'image_url': 'https://image.similarpng.com/very-thumbnail/2020/05/Pizza-logo-design-template-Vector-PNG.png',
                'buttons': [
                    {
                        'type': 'postback',
                        'title': 'Корзина',
                        'payload': 'some text',
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
    return keyboard_elements


def send_keyboard(recipient_id):
    params = {"access_token": os.getenv("PAGE_ACCESS_TOKEN")}
    headers = {"Content-Type": "application/json"}

    keyboard_elements = get_keyboard_products("68ff879e-9b22-4cab-ab32-23cac76a40d9")
    data = json.dumps({
        'recipient': {
            "id": recipient_id
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
    print(response.json())
    response.raise_for_status()


def send_message(recipient_id, message_text):
    params = {"access_token": os.getenv("PAGE_ACCESS_TOKEN")}
    headers = {"Content-Type": "application/json"}
    request_content = json.dumps({
        "recipient": {
            "id": recipient_id
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