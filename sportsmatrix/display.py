"""Physical HUB75 consumer for the virtual worker's atomic PNG output.

The web/virtual worker never imports rgbmatrix; only this process owns GPIO.
"""
import json
import logging
import os
import signal
import time
from pathlib import Path

from PIL import Image
from .configuration import ConfigStore
from .preview import BASE
from .registry import PROFILES

LOG = logging.getLogger('sportsmatrix.display')
FRAME = BASE / 'output' / 'virtual_live.png'
STATE = BASE / 'output' / 'virtual_state.json'
HARDWARE_STATE = BASE / 'output' / 'hardware_state.json'


def frame_to_show(settings, state, now):
    """Return desired (profile, brightness) only for fresh matching frames."""
    if settings.get('power', 'on') == 'off':
        return None
    if settings.get('power', 'on') == 'auto' and settings.get('schedule', {}).get('enabled'):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(settings.get('timezone', 'America/Los_Angeles'))
        current = datetime.now(tz).strftime('%H:%M')
        schedule = settings['schedule']
        start, end = schedule.get('on', '08:00'), schedule.get('off', '22:00')
        active = start <= current < end if start <= end else current >= start or current < end
        if not active:
            return None
    profile = settings.get('profile', 'enhanced_128x64')
    if profile not in PROFILES or state.get('profile') != profile:
        return None
    if state.get('league') != settings.get('league'):
        return None
    if not isinstance(state.get('updated_at'), (int, float)) or not 0 <= now - state['updated_at'] <= 120:
        return None
    return profile, max(1, min(100, int(settings.get('brightness', 50))))


def main():
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
    logging.basicConfig(level=logging.INFO)
    store = ConfigStore(os.environ.get('SPORTSMATRIX_CONFIG', BASE / 'config/settings.json'))
    options = RGBMatrixOptions()
    options.rows, options.cols = 64, 128
    options.chain_length = options.parallel = 1
    options.hardware_mapping = 'adafruit-hat'
    options.led_rgb_sequence = 'BGR'
    options.gpio_slowdown = 4
    options.brightness = 20
    options.drop_privileges = False
    matrix = RGBMatrix(options=options)
    stopped = False

    def stop(_sig, _frame):
        nonlocal stopped
        stopped = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    last_key = None
    try:
        while not stopped:
            try:
                settings = store.read()
                state = json.loads(STATE.read_text()) if STATE.exists() else {}
                desired = frame_to_show(settings, state, time.time())
                if desired is None or not FRAME.exists():
                    if last_key is not None:
                        matrix.Clear()
                        last_key = None
                else:
                    profile, brightness = desired
                    key = (state.get('updated_at'), profile, brightness)
                    if key != last_key:
                        with Image.open(FRAME) as source:
                            image = source.convert('RGB')
                        if image.size != PROFILES[profile]:
                            raise ValueError(f'Unexpected frame size: {image.size}')
                        # The validated physical panel is 128x64; do not silently scale.
                        if profile != 'enhanced_128x64':
                            raise ValueError('This panel requires enhanced_128x64 profile')
                        matrix.brightness = brightness
                        matrix.SetImage(image)
                        last_key = key
            except (OSError, ValueError, TypeError, KeyError):
                LOG.exception('Cannot display current frame; retrying')
            try:
                # Atomic status update for the web UI. File is shared with the worker.
                import tempfile
                HARDWARE_STATE.parent.mkdir(parents=True, exist_ok=True)
                payload = {"updated_at": time.time(), "frame_active": last_key is not None}
                with tempfile.NamedTemporaryFile(mode="w", dir=HARDWARE_STATE.parent, prefix=".hardware-", delete=False) as stream:
                    json.dump(payload, stream)
                    temporary = stream.name
                os.chmod(temporary, 0o644)
                os.replace(temporary, HARDWARE_STATE)
            except OSError:
                LOG.exception("Unable to write hardware status")
            time.sleep(1)
    finally:
        matrix.Clear()
        HARDWARE_STATE.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
