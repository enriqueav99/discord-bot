import logging
from logging.handlers import RotatingFileHandler


def start_logger():
    logger = logging.getLogger("discord")
    logger.setLevel(logging.INFO)

    file_handler = RotatingFileHandler(
        filename="discord.log",
        encoding="utf-8",
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
    )
    file_handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-8s %(name)s %(message)s")
    )
    logger.addHandler(stream_handler)
