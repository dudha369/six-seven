import sounddevice as sd
import soundfile as sf
import threading
import time

class AudioPlayer:
    def __init__(self, file_path, device_index=None):
        """
        device_index: ID аудиоустройства (виртуального кабеля).
        Если None - будет играть в стандартные динамики.
        """
        self.data, self.fs = sf.read(file_path)
        self.device_index = device_index
        self.is_playing = False

    def play(self):
        """Запускает воспроизведение в отдельном потоке, чтобы не тормозить камеру."""
        if not self.is_playing:
            threading.Thread(target=self._play_thread, daemon=True).start()

    def _play_thread(self):
        self.is_playing = True
        try:
            # Воспроизводим звук
            sd.play(self.data, self.fs, device=self.device_index)
            sd.wait() # Ждем окончания трека
        except Exception as e:
            print(f"Ошибка аудио: {e}")
        finally:
            # Защита от спама: кулдаун 1 секунда после завершения звука
            time.sleep(1)
            self.is_playing = False

    @staticmethod
    def list_devices():
        """Полезно для поиска ID твоего виртуального аудиокабеля"""
        print(sd.query_devices())
