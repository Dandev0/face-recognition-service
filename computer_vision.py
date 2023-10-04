import datetime
import os
import time
import cv2
import multiprocessing
from multiprocessing import Pipe
from face_compare import Compare
from ffmpeg import FFmpeg, Progress
from ftp_uploader import Ftp
from logger_ import LOGGER, extra_name

logger_cu = LOGGER
list_ch_pr_sender, recipient_list = Pipe()


class Exception(Exception):
    def few_core(self):
        logger_cu.info(msg='Недостаточно ядер процессора!',
                       extra={extra_name: f''})
        raise Exception('Few cores\nList rtsp url more than free cores.')

    def destroyed_data_from_camera(self):
        raise Exception('Data from camera is not valid')


class Camera:
    def __init__(self, rtsp_url: str = None):
        self.rtsp_url = rtsp_url

    def connect(self):
        self.camera = cv2.VideoCapture(self.rtsp_url)
        logger_cu.debug(msg='Подключение к rtsp Потоку выполнено!',
                        extra={extra_name: f'RTSP_URL: {self.rtsp_url}'})
        return self.camera


class Faces_detection:
    def faces_detection(self, url):
        i = 0
        camera = Camera(rtsp_url=url).connect()
        while camera.isOpened():
            ret, frame = camera.read()
            filter_path = 'haarcascade_frontalface_default.xml'
            clf = cv2.CascadeClassifier(cv2.data.haarcascades + filter_path)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = clf.detectMultiScale(
                gray,
                scaleFactor=1.5,
                minNeighbors=5,
                minSize=(30, 30),
                flags=cv2.CASCADE_SCALE_IMAGE
            )
            try:
                if ret == True:
                    for (x, y, width, height) in faces:
                        face = cv2.rectangle(frame, (x, y), (x + width, y + height), (255, 255, 0), 2)
                        if face is not None:
                            if i == 0:
                                cv2.imwrite(
                                    'detection_movement.jpg', frame)
                                multiprocessing.Process(target=Compare().compare_faces).start()
                            i += 1
                            i %= 80
            except Exception as ex:
                logger_cu.error(msg='Ошибка при распознавании лиц!',
                                extra={extra_name: f'Проблема на потоке: {url}, Ошибка: {ex}'})

            if cv2.waitKey(1) == ord('q'):
                cv2.imwrite('/home/danil/PycharmProjects/face_id_server_aiohttp/Test_face_photo.jpg', frame)
            cv2.imshow('frame', frame)

        else:
            logger_cu.error(msg='Ошибка при распознавании лиц! Камера недоступна!',
                            extra={extra_name: f'Проблема на потоке: {url} --- Переподключение к камере!'})
            time.sleep(5)
            self.faces_detection(url=url)


class Movement_detection:
    def movement_detection(self, url, timer, ftp_data):
        camera = Camera(rtsp_url=url).connect()
        camera.set(3, 1280)  # установка размера окна
        camera.set(4, 700)
        ret, frame1 = camera.read()
        ret, frame2 = camera.read()
        fps = camera.get(cv2.CAP_PROP_FPS)  # получаем fps с камеры
        while camera.isOpened():
            diff = cv2.absdiff(frame1, frame2)
            gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            _, thresh = cv2.threshold(blur, 20, 255,
                                      cv2.THRESH_BINARY)
            dilated = cv2.dilate(thresh, None, iterations=3)
            сontours, _ = cv2.findContours(dilated, cv2.RETR_TREE,
                                           cv2.CHAIN_APPROX_SIMPLE)
            for contour in сontours:
                (x, y, w, h) = cv2.boundingRect(
                    contour)

                if cv2.contourArea(contour) < 700:
                    continue
                cv2.rectangle(frame1, (x, y), (x + w, y + h), (0, 255, 0),
                              2)  # получение прямоугольника из точек кортежа
                cv2.putText(frame1, "Status: {}".format("Dvigenie"), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255),
                            3, cv2.LINE_AA)  # вставляем текст

                name = f'movement_detection {url}'
                process = Movement_detection().get_process(name=name)
                if process is None:
                    multiprocessing.Process(target=Write_archive().ffmpeg_writer,
                                            args=(url, timer, fps, name, ftp_data),
                                            name=name,
                                            daemon=False).start()

            cv2.imshow("frame1", frame1)
            frame1 = frame2  #
            ret, frame2 = camera.read()  #
            if cv2.waitKey(40) == 27:
                break
            if cv2.waitKey(1) == ord('q'):
                break
        else:
            logger_cu.error(msg='Ошибка при распознавании движения! Камера недоступна!',
                            extra={extra_name: f'Проблема на потоке: {url}, Переподключение к камере!'})
            time.sleep(5)
            self.movement_detection(url=url, timer=timer, ftp_data=ftp_data)

    def get_process(self, name):
        return next((p for p in multiprocessing.active_children() if p.name == name), None)


class Write_archive:
    def ffmpeg_writer(self, url, timer, fps, name, ftp_data):
        try:
            logger_cu.info(msg='Обнаружено движение!', extra={extra_name: f'Начинаю запись!'})
            date_time = datetime.datetime.now()
            formatted = date_time.strftime("%Y.%m.%d.%H.%M.%S")
            endpoint_camera = url.split('/')[-1]
            result_name = f"{endpoint_camera}_{formatted}.mp4"
            time_archive = int(timer) * int(fps)
            ffmpeg = (
                FFmpeg()
                .option("y")
                .input(
                    url=url,
                    rtsp_transport="tcp",
                    rtsp_flags="prefer_tcp",
                )
                .output(url=result_name, vcodec="copy")
            )

            @ffmpeg.on("progress")
            def time_to_terminate(progress: Progress):
                if progress.frame > time_archive:
                    ffmpeg.terminate()

            ffmpeg.execute()
            logger_cu.info(msg='Видео записано!',
                           extra={extra_name: f'Filename: {result_name} Duration: {time_archive} msec'})
            multiprocessing.Process(target=Ftp(filename=result_name, ftp_data=ftp_data).ftp_upload_video).start()

        except Exception as ex:
            logger_cu.warning(msg='Не удалось записать архив!',
                              extra={extra_name: f'Описание проблемы: {ex}'})


class Process_manager_base:
    def get_process(self, name):
        return next((p for p in multiprocessing.active_children() if p.name == name), None)


class Process_manager(Process_manager_base):
    def kill_process(self, name_process):
        process = self.get_process(name=name_process)
        if process is not None:
            process.kill()
            logger_cu.info(msg='Процесс был остановлен!',
                           extra={extra_name: f'Processname: {process}'})


class Setup_camera:
    def __init__(self, type_, rtsp_url, command, timer=None, ftp_data=None):
        self.type = type_
        self.rtsp_url = rtsp_url
        self.command = command
        self.timer = timer
        self.ftp_data = ftp_data

    def manager_main_processes(self):
        children_process = multiprocessing.active_children()
        max_process = multiprocessing.cpu_count()
        need_used_core = 1 + len(children_process)
        self.name_process = f'{self.type}: {self.rtsp_url}'
        if need_used_core <= max_process:
            if self.command == 'start':
                if max_process >= need_used_core:
                    if Process_manager_base().get_process(name=self.name_process) is None:
                        if self.type == 'face':
                            self.start_main_process_for_face_recognition()
                        elif self.type == 'movement':
                            self.start_main_process_for_movement_recognition()
                        elif self.type == 'qr':
                            pass
            elif self.command == 'stop':
                Process_manager().kill_process(name_process=self.name_process)

        else:
            raise Exception().few_core()

    def start_main_process_for_face_recognition(self):
        multiprocessing.Process(target=Faces_detection().faces_detection, args=(self.rtsp_url, self.ftp_data),
                                daemon=False, name=self.name_process).start()

    def start_main_process_for_movement_recognition(self):
        multiprocessing.Process(target=Movement_detection().movement_detection,
                                args=(self.rtsp_url, self.timer, self.ftp_data),
                                daemon=False, name=self.name_process).start()
