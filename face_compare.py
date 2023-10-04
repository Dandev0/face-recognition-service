import face_recognition
from ftp_uploader import Ftp
import os
from logger_ import LOGGER, extra_name

logger = LOGGER


class Compare:
    def compare_faces(self):
        try:
            if os.path.isdir('Faces') is False:
                os.mkdir('Faces')
            path = 'Faces/'
            list_files = os.listdir(path)
            for i in list_files:
                img1 = face_recognition.load_image_file(path + i)
                img_1en = face_recognition.face_encodings(img1)[0]

                img2 = face_recognition.load_image_file('detection_movement.jpg')
                img_2en = face_recognition.face_encodings(img2)[0]
                result = face_recognition.compare_faces([img_1en], img_2en)[0]
                if result == True:
                    logger.info(msg='Обнаружено лицо!',
                                extra={extra_name: f'Name: {i}'})
                    return result
                else:
                    logger.info(msg='Обнаруженное лицо не входит в список добавленных пользователем!',
                                extra={extra_name: f'Нет в списке: {str(list_files)}'})
        except IndexError:
            logger.error(msg='Не удалось корректно обработать полученное лицо',
                         extra={extra_name: f''})
