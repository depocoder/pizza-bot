import os

import requests


def get_all_entries(access_token):

    response = requests.get(
        'https://api.moltin.com/v2/flows/pizzeria/entries',
        headers={
            'Authorization': f'Bearer {access_token}',
            })

    response.raise_for_status()
    return response.json()


def get_access_token(redis_conn):
    access_token = redis_conn.get('access_token')
    if not access_token:
        data = {
            'client_id': os.getenv('MOTLIN_CLIENT_ID'),
            'client_secret': os.getenv('MOTLIN_CLIENT_SECRET'),
            'grant_type': 'client_credentials',
                }
        response = requests.get('https://api.moltin.com/oauth/access_token',
                                data=data)
        response.raise_for_status()
        token_info = response.json()
        time_to_expire_s = token_info['expires_in']
        access_token = token_info['access_token']
        redis_conn.set('access_token', access_token, ex=time_to_expire_s)
    return access_token


def create_product(access_token, name, description, price, id_pizza):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    data = {
        "data": {
            "type": "product",
            "name": name,
            "slug": id_pizza,
            "sku": id_pizza,
            "description": description,
            "manage_stock": False,
            "price": [
                {
                    "amount": price,
                    "currency": "RUB",
                    "includes_tax": True
                    }
                ],
            "status": "live",
            "commodity_type": "physical"
        }
    }
    response = requests.post(
        'https://api.moltin.com/v2/products',
        headers=headers, json=data)
    response.raise_for_status()
    return response.json()


def create_flow(access_token, id_flow, name_flow, description):
    headers = {
        'Authorization': 'Bearer {access_token}',
        'Content-Type': 'application/json',
        }

    data = {
        "data": {
            "type": "flow",
            "name": name_flow,
            "slug": id_flow,
            "description": description,
            "enabled": True
            }
        }
    response = requests.post(
        'https://api.moltin.com/v2/flows',
        headers=headers, json=data)
    response.raise_for_status()


def create_field_flow(
        access_token, flow_id, field_name, slug_id, field_type, description):

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    data = {
        "data": {
            "type": "field",
            "name": "field_name",
            "slug": "slug_id",
            "field_type": "field_type",
            "validation_rules": [
                {
                    "type": "between",
                    "options": {
                        "from": 1, "to": 5
                    }
                }
            ],
            "description": "description",
            "relationsihp": {
                "flow": {
                    "data": {
                        "type": "flow",
                        "id": "flow_id"
                    },
                }
            },
            "required": False,
            "default": 0,
            "enabled": True,
            "order": 1,
            "omit_null": False
        }
    }

    response = requests.post(
        'https://api.moltin.com/v2/fields', headers=headers, data=data)
    response.raise_for_status()


def create_an_entry(
        access_token, data, flow_slug):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        }

    response = requests.post(
        f'https://api.moltin.com/v2/flows/{flow_slug}/entries',
        headers=headers, json=data)
    response.raise_for_status()


def upload_file(access_token, image_path):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    with open(image_path, 'rb') as my_file:
        files = {
            'file': (image_path, my_file),
            'public': (None, 'true'),
        }

    response = requests.post(
        'https://api.moltin.com/v2/files', headers=headers, files=files)
    response.raise_for_status()
    return response.json()


def create_relationship(access_token, id_project, id_image):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    data = {
        "data": {
            "type": "main_image",
            "id": id_image}}
    response = requests.post(
        f'https://api.moltin.com/v2/products/{id_project}/relationships/main-image',
        headers=headers, json=data)
    response.raise_for_status()


def get_element_by_id(access_token, id):
    response = requests.get(
        f'https://api.moltin.com/v2/products/{id}',
        headers={
            'Authorization': f'Bearer {access_token}',
        })
    response.raise_for_status()
    return response.json()['data']


def get_products(access_token):
    response = requests.get('https://api.moltin.com/v2/products', headers={
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    })
    response.raise_for_status()
    return response.json()['data']


def add_to_cart(access_token, quantity, item_id, chat_id):
    data = {
        "data": {
            "id": item_id,
            "type": "cart_item",
            "quantity": quantity
            }
        }
    headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            }

    response = requests.post(
        f'https://api.moltin.com/v2/carts/{chat_id}/items', headers=headers,
        json=data)
    response.raise_for_status()
    return response.json()


def delete_from_cart(access_token, item_id, chat_id):
    response = requests.delete(
        f'https://api.moltin.com/v2/carts/{chat_id}/items/{item_id}',
        headers={
            'Authorization': f'Bearer {access_token}',
        }
    )
    response.raise_for_status()


def get_cart(access_token, chat_id):

    response = requests.get(
        f'https://api.moltin.com/v2/carts/{chat_id}/items',
        headers={
            'Authorization': f'Bearer {access_token}',
        }
    )
    response.raise_for_status()
    return response.json()


def get_image_link(access_token, id_image):
    response = requests.get(
        f'https://api.moltin.com/v2/files/{id_image}',
        headers={
            'Authorization': f'Bearer {access_token}'
            }
        )
    response.raise_for_status()
    return response.json()


def create_customer(access_token, chat_id, email):
    headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            }

    data = {
        "data": {
            "type": "customer",
            "name": chat_id,
            "email": email,
            "password": "erwedasdwqrwrqwead"
            }
        }
    response = requests.post(
        'https://api.moltin.com/v2/customers',
        headers=headers, json=data)
    response.raise_for_status()
