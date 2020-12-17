from dotenv import load_dotenv

from loguru import logger


@logger.catch
def main():
    load_dotenv()


if __name__ == "__main__":
    main()
