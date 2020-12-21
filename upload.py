from dotenv import load_dotenv
import json
import os
from pathlib import Path
import shutil

import requests
from loguru import logger
from urllib.parse import urlparse
import redis

from motlin_api import (
    get_access_token, create_product, upload_file, create_relationship,
    create_an_entry)


def download_photo(id_pizza, url_img):
    response = requests.get(url_img)
    response.raise_for_status()
    disassembled_url = urlparse(url_img)
    file_ext = os.path.splitext(
        os.path.basename(disassembled_url.path))[-1]
    rel_img_path = os.path.join('images', id_pizza + file_ext)
    with open(rel_img_path, 'wb') as file:
        file.write(response.content)
    return rel_img_path


def upload_catalogue(redis_conn):
    with open("menu.json", "r", encoding='utf-8') as my_file:
        menu_pizza = json.load(my_file)
    Path(os.getcwd(), 'images').mkdir(parents=True, exist_ok=True)
    for pizza in menu_pizza:
        name = pizza['name']
        description = pizza['description']
        url_img = pizza['product_image']['url']
        price = pizza['price']
        id_pizza = str(pizza['id'])

        access_token = get_access_token(redis_conn)
        download_photo(id_pizza, url_img)

        id_project = create_product(
            access_token, name, description, price, id_pizza)['data']['id']

        rel_img_path = download_photo(id_pizza, url_img)
        id_image = upload_file(access_token, rel_img_path)['data']['id']

        create_relationship(access_token, id_project, id_image)

    path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'images')
    shutil.rmtree(path)


@logger.catch
def main():
    load_dotenv()
    redis_conn = redis.Redis(
        host=os.getenv('REDIS_HOST'), password=os.getenv('REDIS_PASSWORD'),
        port=os.getenv('REDIS_PORT'), db=0, decode_responses=True)
    upload_catalogue(redis_conn)
    with open("addresses.json", "r", encoding='utf-8') as my_file:
        addresses = json.load(my_file)
    access_token = get_access_token(redis_conn)
    flow_slug = "pizzeria"
    for entry in addresses:
        coordinates = entry['coordinates']
        #  Обязательно не забудьте создать Flow адресов, и поля для него!
        data = {
            "data": {
                "type": "entry",
                "address": entry['address']['full'],
                "alias": entry['alias'],
                "latitude": coordinates['lat'],
                "longitude": coordinates['lon'],
                }
            }
        create_an_entry(
            access_token, data, flow_slug)


if __name__ == "__main__":
    main()
