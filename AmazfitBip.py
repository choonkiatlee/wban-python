import time
from Crypto.Cipher import AES

import queue    

from bluepy.btle import UUID, Peripheral, DefaultDelegate

import utils
import StandardBLEGATTCharacteristics
import GenericBTLEDevice


# Authentication Keys
AUTH_SEND_KEY                   = b'\x01'
AUTH_REQUEST_RANDOM_AUTH_NUMBER = b'\x02'
AUTH_SEND_ENCRYPTED_AUTH_NUMBER = b'\x03'
AUTH_BYTE                       = b'\x00'

AUTH_RESPONSE                   = b'\x10'
AUTH_SUCCESS                    = b'\x01'
AUTH_FAIL                       = b'\x04'

# Characteristics

UUID_SERVICE_MIBAND_SERVICE = UUID("FEE0")
UUID_SERVICE_MIBAND2_SERVICE = UUID("FEE1")

UUID_CHARACTERISTIC_CHUNKEDTRANSFER = [UUID_SERVICE_MIBAND_SERVICE, "00000020-0000-3512-2118-0009af100700"]
UUID_CHARACTERISTIC_AUTH            = [UUID_SERVICE_MIBAND2_SERVICE,"00000009-0000-3512-2118-0009af100700"]
UUID_UNKNOWN_CHARACTERISTIC1        = [UUID_SERVICE_MIBAND_SERVICE, "00000001-0000-3512-2118-0009af100700"] # Also known as SENS in https://medium.com/machine-learning-world/how-i-hacked-xiaomi-miband-2-to-control-it-from-linux-a5bd2f36d3ad

# Commands
COMMAND_SET_PERIODIC_HR_MEASUREMENT_INTERVAL = b'\x14'
COMMAND_SET_HR_SLEEP                         = b'\x00'
COMMAND_SET_HR_CONTINUOUS                    = b'\x01'
COMMAND_SET_HR_MANUAL                        = b'\x02'

class AmazfitBip(GenericBTLEDevice.GenericBTLEDevice):

    def __init__(self, PERIPHERAL_ID, SECRET_KEY=None, telemetry_connection_params = None):

        super(AmazfitBip, self).__init__(PERIPHERAL_ID, telemetry_connection_params)
        self.SECRET_KEY = SECRET_KEY

        # self.PERIPHERAL_ID = PERIPHERAL_ID
        # self.MonitorNotificationsFlag = False

    def connect(self):
        
        super().connect(connection_type = "random")

        self.collect_relevant_characteristics()

        # Setup Required Classes
        self.Authentication = Authentication(self)
        self.HeartRateMonitoring = HeartRateMonitoring(self)
        self.GenericNotifications = GenericNotifications(self)

        # Authenticate
        self.Authentication.authenticate()

    def collect_relevant_characteristics(self, retries = 3):
        
        while retries >= 0:
            try:
                self.CHUNKED_TRANSFER_ch = utils.getCharacteristicByID( self.p, UUID_CHARACTERISTIC_CHUNKEDTRANSFER )
                break
            except ValueError:
                self.disconnect()
                time.sleep(2)
                self.connect()
                retries = retries - 1

    def initialise_device(self):
        self.GenericNotifications.start_notify(notify_for_x_seconds=3)
        self.GenericNotifications.stop_notify()

        self.HeartRateMonitoring.set_heart_rate_measurement_interval(1)
        self.HeartRateMonitoring.enable_continuous_heart_rate_monitoring()

    def handle_disconnection(self):
        super().handle_disconnection()
        utils.play_alarm()
        return


class Authentication:
    def __init__(self, AmazfitBip):
        self.AmazfitBip = AmazfitBip
        self.collect_relevant_characteristics()

    def collect_relevant_characteristics(self):

        try:
            self.AUTH_ch = utils.getCharacteristicByID(self.AmazfitBip.p, UUID_CHARACTERISTIC_AUTH)
            return True
        except ValueError:
            self.AmazfitBip.handle_disconnection()
            return False

    def authenticate(self):

        # Send authentication key to create a new pairing only if it is not set
        if self.AmazfitBip.SECRET_KEY is None:
            self.AmazfitBip.SECRET_KEY = str.encode("0123456789abcdef")    # Default SECRET_KEY
            
            # Start Authentication Step 1
            print("Secret Key: {0}".format(self.AmazfitBip.SECRET_KEY))
            self.AUTH_ch.write(AUTH_SEND_KEY + AUTH_BYTE + self.AmazfitBip.SECRET_KEY)

            response = utils.read_till_characteristic_changes(self.AUTH_ch, sampling_interval = 0.1, timeout = 10)

            if not self.validate_auth_response(response, AUTH_SEND_KEY):
                return False
        
        # Start Authentication Step 2
        print("Starting Auth Step 2")
        self.AUTH_ch.write(AUTH_REQUEST_RANDOM_AUTH_NUMBER + AUTH_BYTE)
        
        response = utils.read_till_characteristic_changes(self.AUTH_ch, sampling_interval = 0.1, timeout = 5)

        if not self.validate_auth_response(response, AUTH_REQUEST_RANDOM_AUTH_NUMBER):
            return False
            
        # Start Authentication Step 3 (AUTH_SEND_ENCRYPTED_AUTH_NUMBER)
        # 1) Extract 16 bytes random key from returned notification
        # 2) Encrypt said key with the secret key
        # 3) Send to AUTH_ch

        print("Auth Step 2 (AUTH_REQUEST_RANDOM_AUTH_KEY) successful! Starting Auth Step 3")
        random_key = response[3:]
        if len(random_key) != 16:
            print("Random key looks like it is the wrong number of bytes!")
            return

        encrypted_key = self._encrypt(random_key)
        self.AUTH_ch.write(AUTH_SEND_ENCRYPTED_AUTH_NUMBER + AUTH_BYTE + encrypted_key)

        response = utils.read_till_characteristic_changes(self.AUTH_ch, sampling_interval = 0.1, timeout = 5)
        
        if not self.validate_auth_response(response, AUTH_SEND_ENCRYPTED_AUTH_NUMBER):
            return False

        print("Auth Step 3 successful! Finished Auth")
        return True

    def _encrypt(self, message):
        # This takes a 16 byte message and returns a 16 byte message.
        aes = AES.new(self.AmazfitBip.SECRET_KEY, AES.MODE_ECB)
        return aes.encrypt(message)

    @staticmethod
    def validate_auth_response(data, desired_message_type):

        if bytes([data[0]]) != AUTH_RESPONSE:
            print("Unrecognised response code! Byte dump: {0}, {1} {2} {3}".format(data, bytes([data[0]]), AUTH_RESPONSE,bytes([data[0]]) == AUTH_RESPONSE))
            return False
        
        if ( bytes([data[2]]) == AUTH_FAIL) or (bytes([data[2]]) != AUTH_SUCCESS): 
            print("Authentication failed! Byte dump: {0}".format(data))
            return False

        if (bytes([data[1]]) != desired_message_type):
            print("Wrong message! Byte dump: {0}".format(data))
            return False
        
        else:
            return True

    
############################## Heart Rate Functions #######################################
class HeartRateMonitoring():

    # Note: Manual Heart Rate Measurements take about 12 x 3 = 36 seconds?
    # Continuous Heart Rate Measurements come in at the HEART_RATE_MEASUREMENT_INTERVAL
    # If the user is not wearing the watch, these continuous heart rate measurements don't come in
    # but if you initiate a manual heart rate read when the user is not wearing the watch, 
    # you still get non-zero values (likely the last recorded values I think)


    def __init__(self, AmazfitBip):
        self.AmazfitBip = AmazfitBip
        self.collect_relevant_characteristics()

        self.hr_delegate_uuid = "unattached"

    def collect_relevant_characteristics(self):

        try:
            self.HEART_RATE_CONTROL_POINT_ch = utils.getCharacteristicByID(
                self.AmazfitBip.p, 
                StandardBLEGATTCharacteristics.UUID_CHARACTERISTIC_HEART_RATE_CONTROL_POINT
            )

            self.HEART_RATE_MEASUREMENT_ch = utils.getCharacteristicByID(
                self.AmazfitBip.p,
                StandardBLEGATTCharacteristics.UUID_CHARACTERISTIC_HEART_RATE_MEASUREMENT
            )

            self.SENS_ch = utils.getCharacteristicByID(
                self.AmazfitBip.p,
                UUID_UNKNOWN_CHARACTERISTIC1
            )
        except ValueError:
            self.AmazfitBip.handle_disconnection()

    def send_heart_rate_measurement_command(self, command, data):
        # self.HEART_RATE_CONTROL_POINT_ch.write(b'\x15' + command + bytes([data]), withResponse=False)
        self.AmazfitBip.queue_write_transaction(
            self.HEART_RATE_CONTROL_POINT_ch.getHandle(),
            b'\x15' + command + bytes([data]),
            withResponse=False
        )

    def set_heart_rate_measurement_interval(self, interval_minutes = 15):
        # Interval in minutes
        print("Setting heart rate measurement interval to {0} minutes".format(interval_minutes))
        # self.HEART_RATE_CONTROL_POINT_ch.write(COMMAND_SET_PERIODIC_HR_MEASUREMENT_INTERVAL + bytes([interval_minutes]), withResponse=False)
        
        self.AmazfitBip.queue_write_transaction(
            self.HEART_RATE_CONTROL_POINT_ch.getHandle(),
            COMMAND_SET_PERIODIC_HR_MEASUREMENT_INTERVAL + bytes([interval_minutes]),
        )

    def toggle_heart_rate_measurement_notifications(self, enable = True):

        self.AmazfitBip.toggle_notifications_for_characteristic(self.HEART_RATE_MEASUREMENT_ch, enable)

        # If we want to enable heart rate measurement notifications but there is currently no delegate set 
        if enable and (self.hr_delegate_uuid == "unattached"):
            self.hr_delegate_uuid = self.AmazfitBip.overall_delegate.add_child_delegate(self.HeartRateMonitoringDelegate(self))
        
         # If we want to disable heart rate measurement notifications but there is currently a delegate set 
        elif (not enable) and (self.hr_delegate_uuid != "unattached"):
            self.AmazfitBip.overall_delegate.remove_child_delegate(self.hr_delegate_uuid)
            self.hr_delegate_uuid = "unattached"

        else:
            print("Something is wrong!")


    class HeartRateMonitoringDelegate(DefaultDelegate):
        def __init__(self, HeartRateMonitoringObj):
            DefaultDelegate.__init__(self)
            self.HeartRateMonitoringObj = HeartRateMonitoringObj

        def add_parent_delegate(self, parent_delegate):
            self.parent_delegate = parent_delegate

        def handleNotification(self, cHandle, data):
            print ("Notification from {0} Handle: 0x".format(self.HeartRateMonitoringObj.AmazfitBip.PERIPHERAL_ID)
                 + format(cHandle,'02X') + " Value: {0}".format(data))

            if cHandle == self.HeartRateMonitoringObj.HEART_RATE_MEASUREMENT_ch.getHandle():
                print( "Heart Rate: {0}".format( data[1] ))

                if self.HeartRateMonitoringObj.AmazfitBip.enable_telemetry:
                    self.HeartRateMonitoringObj.AmazfitBip.send_telemetry_message(
                        self.generate_telemetry_message(data[1])
                    )

                # self.HeartRateMonitoringObj.send_heart_rate_measurement_command(COMMAND_SET_HR_MANUAL, False)
                # self.HeartRateMonitoringObj.send_heart_rate_measurement_command(COMMAND_SET_HR_CONTINUOUS, True)        

        def generate_telemetry_message(self, heartRate):
            return "{\"heart_rate\": " + str(heartRate) + " }"

    def enable_continuous_heart_rate_monitoring(self):
        # Turn off current Heart Monitoring measurements
        self.send_heart_rate_measurement_command(COMMAND_SET_HR_MANUAL,False)
        self.send_heart_rate_measurement_command(COMMAND_SET_HR_CONTINUOUS, False)

        # I don't think we need these?
        # Enable Gyro and Heart Raw Data by writing to SENS
        # self.SENS_ch.write(b'\x01\x03\x19')

        # Enable Notifications for HRM
        self.toggle_heart_rate_measurement_notifications(enable=True)

        # Start continuous Heart Rate Monitoring
        self.send_heart_rate_measurement_command(COMMAND_SET_HR_CONTINUOUS, True)

        # Send command to SENS
        # self.SENS_ch.write(b'\x02')

        # self.AmazfitBip.p.setDelegate(self.OnDataRead(self))

        # counter = 0
        # while True:
        #     # Send Heartbeat Seems like we don't need this too!
        #     # self.HEART_RATE_MEASUREMENT_ch.write(b'\x16')
        #     if self.AmazfitBip.p.waitForNotifications(3):   #10 * (1/60)):
        #         counter = 1
        #         continue
        #     print(counter, "Waiting for Notifications...")
        #     counter = counter + 1

        # data = self.HEART_RATE_MEASUREMENT_ch.read()
        # print("Got Heart Rate: {0}".format(data))

# This is a generic class, and should work for any device. To H
class GenericNotifications:
    def __init__(self, AmazfitBip):
        self.AmazfitBip = AmazfitBip
        self.collect_relevant_characteristics()

        self._max_text_notification_length = 18   # From services/btle/profiles/AlertNotificationProfile.java

    def collect_relevant_characteristics(self):
        self.ALERT_LEVEL_ch = utils.getCharacteristicByID(
            self.AmazfitBip.p, 
            StandardBLEGATTCharacteristics.UUID_CHARACTERISTIC_ALERT_LEVEL
        )

        self.NEW_ALERT_ch = utils.getCharacteristicByID(
            self.AmazfitBip.p,
            StandardBLEGATTCharacteristics.UUID_CHARACTERISTIC_NEW_ALERT
        )

        self.NEW_ALERT_CONTROL_POINT_ch = utils.getCharacteristicByID(
            self.AmazfitBip.p,
            StandardBLEGATTCharacteristics.UUID_CHARACTERISTIC_ALERT_NOTIFICATION_CONTROL_POINT
        )

    def start_notify(self, alert_level = 2, notify_for_x_seconds=3):

        self.AmazfitBip.queue_write_transaction(
            self.ALERT_LEVEL_ch.getHandle(),
            bytes([alert_level]),
            withResponse = False,
            time_to_sleep_for_after_transaction_seconds = notify_for_x_seconds
        )

        # self.ALERT_LEVEL_ch.write(bytes([alert_level]))

    def stop_notify(self):

        self.AmazfitBip.queue_write_transaction(
            self.ALERT_LEVEL_ch.getHandle(),
            b'\x00'
        )

        # self.ALERT_LEVEL_ch.write(b'\x00')

    class Alert:

        def __init__(self, alert_category_id, alert_text, num_alerts=1):
            self.alert_category_id = alert_category_id
            self.alert_text = alert_text
            self.num_alerts = num_alerts

        def generate_alert_message(self):
            return self.alert_category_id + bytes([self.num_alerts]) + str.encode(self.alert_text)

    def configure_alerts(self, command_id="enable_new_incoming_alert", category_id="SMS"):

        self.AmazfitBip.queue_write_transaction(
            self.NEW_ALERT_CONTROL_POINT_ch.getHandle(),
            self.command_ids[command_id] + self.category_ids[category_id]
        )

        # self.NEW_ALERT_CONTROL_POINT_ch.write(self.command_ids[command_id] + self.category_ids[category_id])

    def send_text_alert(self, notification_text = ""):
        
        # Handle the large bit later
        numChunks = len(notification_text) / self._max_text_notification_length
        
        newAlert = self.Alert(self.category_ids["SMS"], notification_text, 1)
        
        print(newAlert.generate_alert_message())
        self.NEW_ALERT_ch.write(newAlert.generate_alert_message())


    command_ids = {
        "enable_new_incoming_alert"     : b'\x00',
        "disable_new_incoming_alert"    : b'\x02',
    }

    # These are the only ones fixed on the Amazfit Bip
    category_ids = {
        "Email"         : b'\x01',
        "Incoming Call" : b'\x03',
        "SMS"           : b'\x05',
    }

if __name__ == "__main__":

    PERIPHERAL_ID = "CA:0A:FB:47:1A:95"
    # SECRET_KEY = str.encode("PWGv20jxKGsID4Qt")
    SECRET_KEY = str.encode("0123456789abcdef")
    AmazfitBip = AmazfitBip(PERIPHERAL_ID, SECRET_KEY)
    AmazfitBip.connect()

    AmazfitBip.GenericNotifications.start_notify()
    time.sleep(2)
    AmazfitBip.GenericNotifications.stop_notify()

    # time.sleep(2)
    # AmazfitBip.GenericNotifications.configure_alerts()
    # time.sleep(1)
    # AmazfitBip.GenericNotifications.send_text_alert("Hello World")

    AmazfitBip.HeartRateMonitoring.set_heart_rate_measurement_interval(1)
    AmazfitBip.HeartRateMonitoring.enable_continuous_heart_rate_monitoring()

    AmazfitBip.startMonitoringNotifications()

    import BLEScanner
    wanted_device_rssis = {
        PERIPHERAL_ID.lower():0
    }

    # Start scan in new thread
    blescanner = BLEScanner.BLEScanner(wanted_device_rssis).start()
    print("Started Scan")
    for i in range(10):
        time.sleep(3)
        print(blescanner.devices_to_check_for)
    