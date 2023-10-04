import ftplib
import os
from os import path
from logger_ import LOGGER, extra_name


logger = LOGGER


class Ftp:
    def __init__(self, filename=None, ftp_data=None):
        self.host = ftp_data['host']
        self.ftp_login = ftp_data["ftp_login"]
        self.ftp_password = ftp_data["ftp_password"]
        self.filename = filename

    def connect(self):
        try:
            self.ftp_server = ftplib.FTP(self.host, self.ftp_login, self.ftp_password)
            logger.info(msg='Подключился к ftp', extra={extra_name: f'Host: {self.host}  Username: {self.ftp_login}'})
            return self.ftp_server
        except ftplib.all_errors as error:
            logger.warning(msg='Не удалось подключиться к ftp',
                           extra={extra_name: f'Host: {self.host}  Username: {self.ftp_login}\nError: {error}'})

    def download_photo_face_from_ftp(self):
        try:
            self.ftp_server_ = ftplib.FTP(self.host, self.ftp_login, self.ftp_password)
            self.ftp_server_.retrbinary("RETR " + f'/Faces/{self.filename}', open(f"Faces/{self.filename}", 'wb').write)
            logger.info(msg='Фото скачано с FTP',
                        extra={extra_name: f'Host: {self.host}  Username: {self.ftp_login} Filename: {self.filename}'})
        except ftplib.all_errors as error:
            logger.warning(msg='Не удалось скачать фото с FTP', extra={
                extra_name: f'Host: {self.host}  Username: {self.ftp_login} Filename: {self.filename}\nError: {error}'})

    def ftp_upload_video(self):
        try:
            self.conn = self.connect()
            with open(self.filename, "rb") as file:
                self.conn.storbinary(f"STOR /Archive/{self.filename}", file)
                logger.info(msg='Успешно загрузил видео архив на FTP', extra={extra_name: f'Host: {self.host} Filename: {self.filename}'})
                self.del_file()
        except ftplib.all_errors as error:
            logger.warning(msg='Ошибка при загрузке архива на ftp',
                           extra={extra_name: f'Host: {self.host}  Username: {self.ftp_login}\nError: {error}'})
            # Пришлось писать метод для удаления с локальной машины вместо использования деструктора класса,
            # видимо, пайтон неправильно считает ссылки на объект
            # при создании не блокирующих процессов.

    def del_file(self):
        try:
            os.remove(self.filename)
            logger.debug(msg='Локальный файл удален',
                         extra={extra_name: f'File: {self.filename}'})
        except Exception as exc:
            logger.error(msg='Локальный файл не был удален',
                         extra={extra_name: f'File: {self.filename}\nError: {exc}'})
