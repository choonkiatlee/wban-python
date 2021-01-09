import time

import utils
from bluepy.btle import UUID, Peripheral, DefaultDelegate

import GenericBTLEDevice


CHAR_ACCEL_X         = ["f65399a1-d953-472d-8ca9-1ac71c4ffcb8","68485d94-df75-441c-a457-0af3db0bd987"]
CHAR_ACCEL_Y         = ["f65399a1-d953-472d-8ca9-1ac71c4ffcb8","13220723-6d7d-4056-8d92-85de2109b5f5"]
CHAR_ACCEL_Z         = ["f65399a1-d953-472d-8ca9-1ac71c4ffcb8","603fc2c1-fa8e-4ead-b4a2-e4ea82a78990"]

CHAR_DATA_POINT      = ["45855422-6565-4cd7-a2a9-fe8af41b85e8", "016e11b1-6c8a-4074-9e5a-076053f93784"]
CHAR_SET_POINT       = ["45855422-6565-4cd7-a2a9-fe8af41b85e8", "b44b03f0-b850-4090-86eb-72863fb3618d"]

CHAR_DEBUG           = ["593f756e-fafc-49ba-8695-b39ca851b00b", "e3578b0d-caa7-46d6-b7c2-7331c08de044"]

CHAR_LED_CONTROL     = ["4f817071-4180-434a-982b-422b4c9e6611","a1d9a5bf-f5d8-49f3-a440-e6bf27440cb0"]

BOTTLE_SIZE = 591     # For the current bottle from calculations

class Hidrate(GenericBTLEDevice.GenericBTLEDevice):

    def __init__(self, PERIPHERAL_ID, telemetry_connection_params = None):

        super(Hidrate, self).__init__(PERIPHERAL_ID, telemetry_connection_params)
        self.BOTTLE_SIZE = BOTTLE_SIZE
        self.delegate_uuid = "unattached"

    def connect(self, handleDataInputs=True):

        super().connect(connection_type = "public")
        self.collect_relevant_characteristics()

        if handleDataInputs:
            # self.p.setDelegate(self.OnDataRead(self))
            self.delegate_uuid = self.overall_delegate.add_child_delegate(self.OnDataRead(self))

    def initialise_device(self):
        # Let's start by writing a bunch of the connection values to the bottle
        # From btsnoop_hci.log, packets 1812 - 1825
        self.queue_write_transaction(self.DEBUG_ch.getHandle(),     bytes.fromhex('2100d1'))
        self.queue_write_transaction(self.SET_POINT_ch.getHandle(), bytes.fromhex('92'))
        self.queue_write_transaction(self.DEBUG_ch.getHandle(),     bytes.fromhex('2200f7'))
        self.queue_write_transaction(self.SET_POINT_ch.getHandle(), bytes.fromhex('7700000032d70000'))
        self.queue_write_transaction(self.SET_POINT_ch.getHandle(), bytes.fromhex('00341b00e0790000'))
        self.queue_write_transaction(self.SET_POINT_ch.getHandle(), bytes.fromhex('02345200c0a80000'))
        self.queue_write_transaction(self.SET_POINT_ch.getHandle(), bytes.fromhex('03346e0030c00000'))
        self.queue_write_transaction(self.SET_POINT_ch.getHandle(), bytes.fromhex('04348900a0d70000'))
        self.queue_write_transaction(self.SET_POINT_ch.getHandle(), bytes.fromhex('0534a50010ef0000'))
        self.queue_write_transaction(self.SET_POINT_ch.getHandle(), bytes.fromhex('0634c00080060100'))
        self.queue_write_transaction(self.SET_POINT_ch.getHandle(), bytes.fromhex('0734dc00f01d0100'))
        self.queue_write_transaction(self.SET_POINT_ch.getHandle(), bytes.fromhex('0834000000000000'))
        self.queue_write_transaction(self.SET_POINT_ch.getHandle(), bytes.fromhex('0934000000000000'))

        # self.DEBUG_ch.write(             bytes.fromhex('2100d1'))                # DEBUG
        # self.SET_POINT_ch.write(         bytes.fromhex('92'))                    # SetGoalGlow(z=None)
        # self.DEBUG_ch.write(             bytes.fromhex('2200f7'))                # DEBUG
        # self.SET_POINT_ch.write(         bytes.fromhex('7700000032d70000'))      # SetTimeInSec
        # self.SET_POINT_ch.write(         bytes.fromhex('00341b00e0790000'))      # ScheduleLight?
        # self.SET_POINT_ch.write(         bytes.fromhex('02345200c0a80000'))      # ScheduleLight?
        # self.SET_POINT_ch.write(         bytes.fromhex('03346e0030c00000'))      # ScheduleLight?
        # self.SET_POINT_ch.write(         bytes.fromhex('04348900a0d70000'))      # ScheduleLight?
        # self.SET_POINT_ch.write(         bytes.fromhex('0534a50010ef0000'))      # ScheduleLight?
        # self.SET_POINT_ch.write(         bytes.fromhex('0634c00080060100'))      # ScheduleLight?
        # self.SET_POINT_ch.write(         bytes.fromhex('0734dc00f01d0100'))      # ScheduleLight?
        # self.SET_POINT_ch.write(         bytes.fromhex('0834000000000000'))      # ScheduleLight?
        # self.SET_POINT_ch.write(         bytes.fromhex('0934000000000000'))      # ScheduleLight?

        for i in range(3):
            self.lightUpBottle_OneShortPulseWhite()
            time.sleep(3)

        self.send_ready_for_reading_sips()

        return self.p

    def collect_relevant_characteristics(self):
        self.DATA_ch = utils.getCharacteristicByID(self.p, CHAR_DATA_POINT)
        self.DEBUG_ch = utils.getCharacteristicByID(self.p, CHAR_DEBUG)
        self.SET_POINT_ch = utils.getCharacteristicByID(self.p, CHAR_SET_POINT)
        self.LED_ch = utils.getCharacteristicByID(self.p, CHAR_LED_CONTROL)

    @staticmethod
    def parseSip(data, BOTTLE_SIZE):
        # Parsed from dataPointCharacteristicDidUpdate in RxBLEConnectCoordinator.java
        no_sips_left_on_device = data[0]
        i3 = BOTTLE_SIZE
        b2 = data[1] & 255          # Likely some version of sip size as percentage of bottle fullness

        SipSize = (i3 * b2) / 100

        # i7 = ByteBuffer.wrap(new byte[]{0, 0, bArr2[3], bArr2[2]}).getInt() & 65535;
        total = int.from_bytes(data[3:1:-1], "little") & 65535      # This bit of list comprehension magic gets us [data[3], data[2]]

        # int i8 = ByteBuffer.wrap(new byte[]{bArr2[7], bArr2[6], bArr2[5], bArr2[4]}).getInt() & -1;
        secondsAgo = int.from_bytes(data[8:4:-1], "little") & -1

        print("Sip Size: {0}, Total: {1}, Seconds Ago: {2}, Sips Left: {3}".format(SipSize, total, secondsAgo, no_sips_left_on_device - 1))

        return SipSize, total, secondsAgo, no_sips_left_on_device

    def send_ready_for_reading_sips(self):
        self.queue_write_transaction(self.DATA_ch.getHandle(), bytes.fromhex('57'))
        # self.DATA_ch.write(bytes.fromhex('57'))

    # Light commands from Lights.java
    def lightUpBottle_OneShortPulseWhite(self):
        self.queue_write_transaction(self.LED_ch.getHandle(), bytes.fromhex('02'))
        # self.LED_ch.write(bytes.fromhex('02'))

    def lightUpBottle_OneShortStrobeRed(self):
        self.queue_write_transaction(self.LED_ch.getHandle(), bytes.fromhex('16'))
        # self.LED_ch.write(bytes.fromhex('16'))


    class OnDataRead(DefaultDelegate):
        def __init__(self, HidrateObject):
            DefaultDelegate.__init__(self)
            self.HidrateObject = HidrateObject

        def add_parent_delegate(self, parent_delegate):
            self.parent_delegate = parent_delegate

        def handleNotification(self, cHandle, data):
            if cHandle == 23: #0x17 in decimal, These are the notifications from the DATA_POINT characteristic
                print ("Notification from Handle: 0x" + format(cHandle,'02X') + " Value: {0}".format(data))
                self.handleDataReadNotification(data)

        def handleDataReadNotification(self,data):

            no_sips_left_on_device = data[0]

            if no_sips_left_on_device > 0:

                # Check the rest of the data fields. If the data is otherwise empty, issue a read notification
                if int.from_bytes(data[1:], "big") > 0:
                    SipSize, total, secondsAgo, no_sips_left_on_device = self.HidrateObject.parseSip(data, self.HidrateObject.BOTTLE_SIZE)

                    if self.HidrateObject.enable_telemetry:
                        self.HidrateObject.send_telemetry_message(
                            self.generate_telemetry_message(SipSize)
                        )

                    self.HidrateObject.lightUpBottle_OneShortPulseWhite()
                else:
                    self.HidrateObject.send_ready_for_reading_sips()

        def generate_telemetry_message(self, sip_size):
            return "{\"water_drunk\": " + str(sip_size) + " }"

# Some notes on how this all works:
# At the start just after pairing, we need to send some values over to the bottle before it'll let us read
# data (PLEASE VERIFY!). However, I can't find out what kind of values are sent, so I just replayed values I 
# got over WireShark. Thus, we need to check if this works for different bottles / different times, but shouldn't
# matter for the demo.

# Next after pairing, we want to read all the data that the bottle has got after subscribing to notifications
# on the DATA_POINT characteristic.

# This is done by writing 0x57 to the DATA_POINT characteristic. The DATA_POINT characteristic will then
# notify the connected object a data packet. Format of this data packet can be found in 
# dataPointCharacteristicDidUpdate in RxBLEConnectCoordinator.java in the decompiled APK

# In normal operation, after the user drinks a sip of water, the bottle will notify 0x0n,0x00,0x00......
# Here, n is the number of sips that is currently stored on the device without being collected (yet)
# After we receive one of these, we then trigger the procedure above to keep reading sips until no more sips are left
# i.e.:
# receive 0x02,0x00,0x00......
# send 0x57
# receive packet 1
# send 0x57
# receive packet 2
# send 0x57 
# receive 0x00,0x00,0x00...... (I think)

# We need to do a tiny bit more work to be 100% sure about what the TOTAL and Seconds Ago fields mean, and
# settle the endianness of it, but I think it's roughly done. 

# Lights are triggered throught the LED characteristic, though the light numbers given in model/Lights.java seem
# a bit suspect.

# Notes on APK decompiling:
# sources/hidratenow/com/hidrate/hidrateandroid/BLE seems to be the main folder to look at
# RxBLEBottleConnectionManager.java gives the high level stuff which you should look at first
# It then calls stuff from RxBLEBottleCoordinator.java
# Remember to look at the Cxxxxxxxxx.java files, which contain lambda functions used to do the BLE calls

# sources/hidratenow/com/hidrate/hidrateandroid/models gives the data models
# Of main interest is BLEMessage (Select the notification speed / type when you subscribe to the DATA_POINT notifications)
# HidrateBleCharacteristicConstants.java (Give the UUIDs of all characteristics and usable names)
# Lights.java ( supposed to be the light codes but I swear they do not work. Only ones that do so far are 0x34 => 3times of 3 short pulses and 0x02 => one time of one short pulse)



if __name__ == "__main__":

    PERIPHERAL_ID = "45:DE:A1:04:15:2D"

    HidrateBottle = Hidrate(PERIPHERAL_ID)

    test_bytes_1 = "0122f300010000007322dd26dc265d2556010000" #201ml   # packet 1390 btsnoop_hci.log
    test_bytes_2 = "01130601010000007722d8265d258824be000000" #112ml   # packet 2219 btsnoop_hci.log
    test_bytes_3 = "01323801010000007922d52688249b22f8010000" #296ml   # packet 2828 btsnoop_hci.log

    HidrateBottle.parseSip(bytes.fromhex(test_bytes_1), BOTTLE_SIZE)
    HidrateBottle.parseSip(bytes.fromhex(test_bytes_2), BOTTLE_SIZE)
    HidrateBottle.parseSip(bytes.fromhex(test_bytes_3), BOTTLE_SIZE)

    # HidrateBottle.connect(handleDataInputs=False)

    HidrateBottle.connect()

    HidrateBottle.initialise_device()

    HidrateBottle.startMonitoringNotifications()


