import logging
from logging import StreamHandler, Formatter
import sys
from config import SERVICE_NAME


class Logger_base:
    def __init__(self, level='DEBUG'):
        self.logger = logging.getLogger(__name__)
        self.handler = StreamHandler(stream=sys.stdout)
        self.level = level

    def logger_configuration(self):
        self.logger.setLevel(self.level)
        self.handler.setFormatter(Formatter(fmt='[%(asctime)s: %(levelname)s] %(message)s'))
        self.logger.addHandler(self.handler)
        return self.logger


class Logger_more_information(Logger_base):
    def logger_configuration(self, extra=None):
        self.logger.setLevel(self.level)
        self.handler.setFormatter(Formatter(fmt=f'[%(asctime)s: %(levelname)s] %(message)s %({extra})s'))
        self.logger.addHandler(self.handler)
        self.logger.addHandler(Myhandler())
        return self.logger


class Myhandler(logging.Handler):
    def emit(self, record):
        from rabbitmq_ import Rabbit_sender
        import json
        reserved_keys = record.__dict__
        self.response_string = {"service-name": SERVICE_NAME, "level_event": reserved_keys['levelname'], "message": reserved_keys['msg'], "more_information": reserved_keys[extra_name], "datetime": reserved_keys['asctime']}
        self.json_data = json.dumps(self.response_string)
        Rabbit_sender(message=self.json_data).send_message()


extra_name = 'more_informations'
loggers = Logger_more_information(level='INFO').logger_configuration(extra=extra_name)
LOGGER = loggers
