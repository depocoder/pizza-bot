from dotenv import load_dotenv
import json

from loguru import logger


@logger.catch
def main():
    load_dotenv()
    with open("addresses.json", "r") as my_file:
        addresses = json.load(my_file)
    print(addresses)


if __name__ == "__main__":
    main()
