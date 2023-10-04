import pika
import ast
import time
from config import RABBITMQ_LOGIN, RABBITMQ_IP, RABBITMQ_PASSWORD, RABBITMQ_PORT, SERVICE_NAME
from computer_vision import *
from logger_ import LOGGER, extra_name
import logging

logger = LOGGER


class Rabbit_base:
    def __init__(self, message: str = None, queue_=None):
        self.credentials = pika.PlainCredentials(username=RABBITMQ_LOGIN, password=RABBITMQ_PASSWORD)
        self.parameters = pika.ConnectionParameters(host=RABBITMQ_IP, port=RABBITMQ_PORT, virtual_host='/',
                                                    credentials=self.credentials)
        self.connection = None
        self.channel = None
        self.message = message
        self.queue = queue_

    def connect(self):
        try:
            if not self.connection or self.connection.is_closed:
                self.connection = pika.BlockingConnection(self.parameters)
                self.channel = self.connection.channel()
                if self.connection:
                    return self.connection

        except pika.exceptions.AMQPConnectionError as error:
            logging.warning(msg='Подключение к очереди Rabbit закончилось неудачей!',
                           extra={extra_name: f'Host: {RABBITMQ_IP}  Username: {RABBITMQ_LOGIN}\nError: {error}'})
            time.sleep(3)
            self.connect()

        except pika.exceptions.ConnectionClosedByBroker as error:
            logging.warning(msg='Подключение к очереди Rabbit закончилось неудачей!',
                           extra={extra_name: f'Host: {RABBITMQ_IP}  Username: {RABBITMQ_LOGIN}\nError: {error}'})
            time.sleep(3)
            self.connect()

        except pika.exceptions.ConnectionWrongStateError as error:
            logging.warning(msg='Подключение к очереди Rabbit закончилось неудачей!',
                           extra={extra_name: f'Host: {RABBITMQ_IP}  Username: {RABBITMQ_LOGIN}\nError: {error}'})
            time.sleep(3)
            self.connect()


class Rabbit_listener(Rabbit_base):
    @staticmethod
    def pr(ch, method, properties, data):
        try:
            str_data = data.decode('utf-8')
            data = ast.literal_eval(str_data)
            command = data['data']['command']
            if command == 'download_photo':
                name = data['data']['name_photo']
                return multiprocessing.Process(target=Ftp(filename=name).download_photo_face_from_ftp).start()
            rtsp_url = data['data']['rtsp_url']
            type_camera = data['data']['type_camera']
            if type_camera == 'movement':
                timer = data['data']['time_archive_write']
                return Setup_camera(rtsp_url=rtsp_url, type_=type_camera, command=command,
                             timer=timer, ftp_data=data['ftp_data']).manager_main_processes()
            elif type_camera == 'face':
                return Setup_camera(rtsp_url=rtsp_url, type_=type_camera, command=command, ftp_data=data['ftp_data']).manager_main_processes()

        except KeyError:
            return logger.error(msg=f'{SERVICE_NAME}: Отправленные данные не валидны!',
                                extra={extra_name: f'Сервис получил следующие данные: {data}'})

    def get_message(self):
        try:
            self.connect()
            self.channel.basic_consume(queue=self.queue,
                                       auto_ack=True,
                                       on_message_callback=self.pr)
            self.channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as error:
            logging.warning(msg='Подключение к очереди Rabbit прервалось!',
                           extra={extra_name: f'Host: {RABBITMQ_IP}  Username: {RABBITMQ_LOGIN}\nError: {error}'})
            time.sleep(3)
            self.connect()

        except pika.exceptions.ConnectionClosedByBroker as error:
            logging.warning(msg='Подключение к очереди Rabbit прервалось!',
                           extra={extra_name: f'Host: {RABBITMQ_IP}  Username: {RABBITMQ_LOGIN}\nError: {error}'})
            time.sleep(3)
            self.connect()

        except pika.exceptions.ConnectionWrongStateError as error:
            logging.warning(msg='Подключение к очереди Rabbit прервалось!',
                           extra={extra_name: f'Host: {RABBITMQ_IP}  Username: {RABBITMQ_LOGIN}\nError: {error}'})
            time.sleep(3)
            self.connect()


class Rabbit_sender(Rabbit_base):
    def send_message(self):
        self.connect()
        if self.connection:
            self.channel.basic_publish(exchange='',
                                       routing_key='log_queue', body=self.message)


if __name__ == '__main__':
    Rabbit_listener(queue_='recognitions-service').get_message()
