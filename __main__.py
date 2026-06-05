import cv2
from detector import MovementDetector
from audio import AudioPlayer


def main():
    # Если ты настроил VB-Cable, раскомментируй строку ниже, узнай ID устройства
    # и передай его в AudioPlayer(..., device_index=ID)
    # AudioPlayer.list_devices()

    # Инициализация
    audio_player = AudioPlayer("sound.mp3")  # Укажи путь к своему звуку
    detector = MovementDetector(movement_threshold=0.03)
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Ошибка: Не удалось открыть веб-камеру.")
        return

    print("Приложение запущено. Нажми 'q' для выхода.")

    while True:
        success, frame = cap.read()
        if not success:
            break

        # Отражаем кадр зеркально для удобства восприятия
        frame = cv2.flip(frame, 1)

        # Обработка кадра
        processed_frame, trigger_sound = detector.process_frame(frame)

        # Если движение зафиксировано - проигрываем звук
        if trigger_sound:
            audio_player.play()
            # Для наглядности рисуем индикатор на экране
            cv2.putText(processed_frame, "MOVEMENT DETECTED!", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Вывод на экран
        cv2.imshow("Hand Movement Detector", processed_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
