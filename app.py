import os

from dotenv import load_dotenv
from loguru import logger
from flask import Flask, request

import fb_bot

app = Flask(__name__)


@app.route('/', methods=['POST'])
def webhook():
    """
    Основной вебхук, на который будут приходить сообщения от Facebook.
    """
    data = request.get_json()
    if data["object"] != "page":
        return "false", 500
    for entry in data["entry"]:
        for messaging_event in entry["messaging"]:
            postback = messaging_event.get("postback")
            if postback:
                payload = {}
                payload['payload'] = postback['payload']
                payload['title'] = postback['title']
            else:
                payload = None
            if messaging_event.get("message") or postback:  # someone sent us a message
                sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                fb_bot.send_message(sender_id, 'message_text')
                fb_bot.handle_users_reply(sender_id, payload)
    return "ok", 200


@app.route('/', methods=['GET'])
def verify():
    """
    При верификации вебхука у Facebook он отправит запрос на этот адрес. На него нужно ответить VERIFY_TOKEN.
    """
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.getenv("FB_VERIFY_TOKEN"):
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


@logger.catch
def main():
    fb_bot.main()
    load_dotenv()
    app.run(debug=True, host='0.0.0.0', port=80)


if __name__ == '__main__':
    main()
