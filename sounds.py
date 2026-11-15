"""Sons do AudioMail: gera o som padrao e toca arquivos WAV."""
import math
import os
import struct
import wave


def make_default_wav(path, rate=44100):
    """Gera um 'ding' de duas notas (mi e si), curto e agradavel."""
    notes = [(659.25, 0.14), (987.77, 0.32)]
    frames = bytearray()
    for freq, dur in notes:
        total = int(rate * dur)
        for i in range(total):
            t = i / rate
            attack = min(1.0, i / (rate * 0.008))
            decay = math.exp(-6.0 * i / total)
            wave_value = (0.7 * math.sin(2 * math.pi * freq * t)
                          + 0.2 * math.sin(2 * math.pi * 2 * freq * t))
            sample = int(32767 * 0.55 * attack * decay * wave_value)
            frames += struct.pack("<h", max(-32768, min(32767, sample)))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))


def ensure_default(path):
    try:
        if not os.path.isfile(path) or os.path.getsize(path) < 1000:
            make_default_wav(path)
    except Exception:
        pass


def is_valid_wav(path):
    try:
        with wave.open(path, "rb") as w:
            return w.getnframes() > 0
    except Exception:
        return False


def play(path):
    """Toca um WAV sem travar a tela. Devolve True se conseguiu."""
    try:
        import winsound
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        return True
    except Exception:
        return False
