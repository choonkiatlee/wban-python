import struct

import Hidrate

PERIPHERAL_ID = "45:DE:A1:04:15:2D"

HidrateBottle = Hidrate.Hidrate(PERIPHERAL_ID)

HidrateBottle.connect()

HidrateBottle.initialise_device()

while True:
    if HidrateBottle.p.waitForNotifications(1.0):
        # handleNotification() was called
        continue

    print ("Waiting... Waited more than one sec for notification")



# def send_ready_for_reading_sips(DATA_ch):
#     DATA_ch.write(bytes.fromhex('57'))

# class OnDataRead(DefaultDelegate):
#     def __init__(self, DATA_ch, parseSip):
#         DefaultDelegate.__init__(self)
#         self.DATA_ch = DATA_ch
#         self.send_ready_for_reading_sips()
#         # ... initialise here

#     def handleNotification(self, cHandle, data):
#         if cHandle == 23: #0x17 in decimal
#             print ("Notification from Handle: 0x" + format(cHandle,'02X') + " Value: {0}".format(data))
#             self.handleDataReadNotification(data)
#         # ... perhaps check cHandle
#         # ... process 'data'

#     def handleDataReadNotification(self,data):

#         no_sips_left_on_device = data[0]

#         if no_sips_left_on_device > 0:

#             # Check the rest of the data fields. If the data is otherwise empty, issue a read notification
#             if int.from_bytes(data[1:], "big") > 0:
#                 self.parseSip(data)
#             else:
#                 self.send_ready_for_reading_sips()

#     def send_ready_for_reading_sips(self):
#         self.DATA_ch.write(bytes.fromhex('57'))


# if __name__ == "__main__":

#     p = Peripheral(PERIPHERAL_ID)

#     DATA_ch = getCharacteristicByID(p, Hidrate.DATA_POINT)[0]
#     DEBUG_ch = getCharacteristicByID(p, Hidrate.DEBUG)[0]
#     SET_POINT_ch = getCharacteristicByID(p, Hidrate.SET_POINT)[0]
#     LED_ch = getCharacteristicByID(p, Hidrate.LED_CONTROL)[0]

#     p.setDelegate(OnDataRead(DATA_ch))

#     # Let's start by writing a bunch of the connection values to the bottle
#     DEBUG_ch.write(             bytes.fromhex('2100d1'))
#     SET_POINT_ch.write(         bytes.fromhex('92'))                    # SetGoalGlow(z=None)
#     DEBUG_ch.write(             bytes.fromhex('2200f7'))
#     SET_POINT_ch.write(         bytes.fromhex('7700000032d70000'))      # SetTimeInSec
#     SET_POINT_ch.write(         bytes.fromhex('00341b00e0790000'))      # ScheduleLight?
#     SET_POINT_ch.write(         bytes.fromhex('02345200c0a80000'))
#     SET_POINT_ch.write(         bytes.fromhex('03346e0030c00000'))
#     SET_POINT_ch.write(         bytes.fromhex('04348900a0d70000'))
#     SET_POINT_ch.write(         bytes.fromhex('0534a50010ef0000'))
#     SET_POINT_ch.write(         bytes.fromhex('0634c00080060100'))
#     SET_POINT_ch.write(         bytes.fromhex('0734dc00f01d0100'))
#     SET_POINT_ch.write(         bytes.fromhex('0834000000000000'))
#     SET_POINT_ch.write(         bytes.fromhex('0934000000000000'))

#     print(DEBUG_ch.read())


#     LED_ch.write(bytes.fromhex('34'))

#     while True:
#         if p.waitForNotifications(1.0):
#             # handleNotification() was called
#             continue

#         print ("Waiting... Waited more than one sec for notification")






