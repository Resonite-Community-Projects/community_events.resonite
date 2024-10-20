import logging

import colorlog

def get_logger(name):
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            '%(log_color)s[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s',
            "%Y-%m-%d %H:%M:%S %z",
        )
    )
    logger = colorlog.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    # TODO: Fix this, their should never be more than 1 logger handler
    if len(logger.handlers) > 1:
        logger.removeHandler(logger.handlers[0])

    return logger