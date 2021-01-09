import time
import simpleaudio as sa

def getCharacteristicByID(peripheral, characteristic_constant, retries = 3):
    service = peripheral.getServiceByUUID(characteristic_constant[0])

    while retries >= 0:
        try:
            characteristic = service.getCharacteristics(characteristic_constant[1])[0]
            break
        except IndexError:
            retries = retries - 1
            time.sleep(0.5)

    if retries < 0:
        raise ValueError("No such characteristic found!")

    return characteristic

def toggle_notifications_for_characteristic(peripheral, characteristic, enable=True):
    peripheral.writeCharacteristic(characteristic.getHandle() + 1, bytes([enable]) + b'\x00') 

def read_till_characteristic_changes(ch, sampling_interval = 0.1, timeout = 5):
        
    startTime = time.time()
    orig_characteristic_value = ch.read()
    while (time.time() - startTime) < timeout:
        current_characteristic_value = ch.read()

        if current_characteristic_value != orig_characteristic_value:
            return current_characteristic_value
        
        else:
            time.sleep(sampling_interval)

    return None

def load_alarm():
    return sa.WaveObject.from_wave_file("alarm.wav")

def play_alarm(wav_obj = None, block = False):
    if wav_obj is None:
        wav_obj = sa.WaveObject.from_wave_file("alarm.wav")

    play_obj = wav_obj.play()

    if block:
        play_obj.wait_done()