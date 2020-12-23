import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger
import requests
from flask import Flask, request

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
                    send_keyboard(recipient_id, message_text)
                    send_message(sender_id, message_text)
    return "ok", 200


@logger.catch
def send_keyboard(recipient_id, message_text):
    params = {"access_token": os.getenv("PAGE_ACCESS_TOKEN")}
    headers = {"Content-Type": "application/json"}
    data = {

        {"recipient": {
            "id": recipient_id
            },
         "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": [{
                        "title": "Welcome!",
                        "image_url": "https://petersfancybrownhats.com/company_image.png",
                        "subtitle": "We have the right hat for everyone.",
                        "default_action": {
                            "type": "web_url",
                            "url": "https://petersfancybrownhats.com/view?item': '103",
                            "messenger_extensions": False,
                            "webview_height_ratio": "tall",
                            "fallback_url": "https://petersfancybrownhats.com/"
                            },
                        "buttons": [
                            {
                                "type": "web_url",
                                "url": "https://petersfancybrownhats.com",
                                "title": "View Website"
                                },
                            {
                                "type": "postback",
                                "title": "Start Chatting",
                                "payload": "DEVELOPER_DEFINED_PAYLOAD"
                                }
                            ]
                        }]
                    }
                }
            }
        }
    }
    data = json.dumps(data)
    response = requests.post(
        'https://graph.facebook.com/v2.6/me/messages',
        headers=headers,
        params=params,
        data=(data)
        )
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

if __name__ == '__main__':
    load_dotenv()
    app.run(debug=True, host='0.0.0.0', port=80)