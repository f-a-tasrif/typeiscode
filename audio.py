
from __future__ import annotations

import os
import threading
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))

def _mci_set_volume(alias: str, volume: float):
    """Set volume for MCI alias. volume is 0.0-1.0"""
    if sys.platform != "win32":
        return
    try:
        from ctypes import c_buffer, windll
        from sys import getfilesystemencoding
        buf = c_buffer(255)
        vol_int = int(volume * 1000)
        cmd = f'setaudio {alias} volume to {vol_int}'.encode(getfilesystemencoding())
        errorCode = int(windll.winmm.mciSendStringA(cmd, buf, 254, 0))
        if errorCode:
            pass
    except Exception:
        pass

def _mci_get_status(alias: str, item: str) -> bytes:
    """Get MCI status for alias."""
    if sys.platform != "win32":
        return b''
    try:
        from ctypes import c_buffer, windll
        from sys import getfilesystemencoding
        buf = c_buffer(255)
        cmd = f'status {alias} {item}'.encode(getfilesystemencoding())
        errorCode = int(windll.winmm.mciSendStringA(cmd, buf, 254, 0))
        if errorCode:
            return b''
        return buf.value
    except Exception:
        return b''


class AudioManager:

    def __init__(self, path: str):
        self.path = self._resolve(path)
        self._volume = 0.8
        self._muted = False
        self._backend = "silent"
        self._playing = False
        self._lock = threading.Lock()
        self._loop_job: threading.Thread | None = None
        self._sfx: dict[str, object] = {}
        self._init_backend()


    def _resolve(self, path: str) -> str:
        candidates = [path]
        if not os.path.isabs(path):
            candidates.append(os.path.join(_HERE, path))
            candidates.append(os.path.join(_HERE, "assets",
                                           os.path.basename(path)))
        for cand in candidates:
            if os.path.isfile(cand):
                return cand
        return path

    @property
    def backend(self) -> str:
        return self._backend

    def _init_backend(self):
        if not os.path.isfile(self.path):
            return

        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(self.path)
            pygame.mixer.music.set_volume(self._applied_volume())
            self._backend = "pygame"
            return
        except Exception:
            pass

        try:
            import playsound
            self._backend = "playsound"
            return
        except Exception:
            pass

        self._backend = "silent"


    def _applied_volume(self) -> float:
        return 0.0 if self._muted else float(self._volume)

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, v: float):
        self.set_volume(v)

    def set_volume(self, v: float):
        try:
            v = float(v)
        except (TypeError, ValueError):
            return
        v = max(0.0, min(1.0, v))
        with self._lock:
            self._volume = v
        applied = self._applied_volume()
        if self._backend == "pygame":
            try:
                import pygame
                pygame.mixer.music.set_volume(applied)
            except Exception:
                pass
        elif self._backend == "playsound":
            pass



    def toggle_mute(self) -> bool:
        with self._lock:
            self._muted = not self._muted
            muted = self._muted
        if self._backend == "pygame":
            try:
                import pygame
                pygame.mixer.music.set_volume(0.0 if muted else self._volume)
            except Exception:
                pass
        elif self._backend == "playsound":
            pass
        return muted

    def is_muted(self) -> bool:
        return bool(self._muted)


    def play_loop(self):
        if self._backend == "silent":
            self._playing = True
            return
        self._playing = True
        if self._backend == "pygame":
            try:
                import pygame
                pygame.mixer.music.set_volume(self._applied_volume())
                pygame.mixer.music.play(loops=-1)
                return
            except Exception:
                self._backend = "silent"
                return
        if self._backend == "playsound":
            self._start_playsound_loop()

    def _start_playsound_loop(self):
        if self._loop_job is not None and self._loop_job.is_alive():
            return

        def _worker():
            try:
                from playsound import playsound
            except Exception:
                return
            while self._playing:
                if self._muted or self._volume <= 0.0:
                    threading.Event().wait(0.2)
                    continue
                try:
                    playsound(self.path, block=True)
                except Exception:
                    return

        self._loop_job = threading.Thread(target=_worker, daemon=True,
                                          name="tic-music")
        self._loop_job.start()

    def stop(self):
        self._playing = False
        if self._backend == "pygame":
            try:
                import pygame
                pygame.mixer.music.stop()
            except Exception:
                pass


    def play_sfx(self, path: str):
        try:
            if self._muted:
                return
            full = path if os.path.isfile(path) else self._resolve(path)
            if not os.path.isfile(full):
                return
            if self._backend == "pygame":
                try:
                    import pygame
                    key = os.path.abspath(full)
                    snd = self._sfx.get(key)
                    if snd is None:
                        snd = pygame.mixer.Sound(full)
                        if len(self._sfx) >= 12:
                            self._sfx.pop(next(iter(self._sfx)))
                        self._sfx[key] = snd
                    try:
                        snd.set_volume(self._applied_volume())
                    except Exception:
                        pass
                    snd.play()
                    return
                except Exception:
                    pass
            if self._backend == "playsound":
                try:
                    from playsound import playsound as _play

                    def _worker(p=full):
                        try:
                            _play(p, block=True)
                        except Exception:
                            pass

                    threading.Thread(target=_worker, daemon=True,
                                     name="tic-sfx").start()
                except Exception:
                    pass
        except Exception:
            pass
