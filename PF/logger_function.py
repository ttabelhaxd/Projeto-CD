import logging

logging.basicConfig(level=logging.DEBUG)

def save(module):
    return logging.getLogger(module)