from bluepy.btle import UUID, Peripheral, DefaultDelegate, BTLEDisconnectError, BTLEInternalError
import uuid

from threading import Thread
import threading
import queue
import time

import AzureIOTCConnection



class OverallDelegate(DefaultDelegate):
    def __init__(self, device_delegates = {}, telemetry_connection = None):
        DefaultDelegate.__init__(self)
        self.device_delegates = device_delegates
        self.telemetry_connection = telemetry_connection

    def add_child_delegate(self, device_delegate_to_add):
        device_delegate_to_add.add_parent_delegate(self)

        # generate a uuid to attach to the device_delegate
        device_delegate_uuid = uuid.uuid1()
        
        # attach the device delegate 
        self.device_delegates[device_delegate_uuid] = device_delegate_to_add
        
        return device_delegate_uuid 

    def remove_child_delegate(self, device_delegate_uuid):
        self.device_delegates.pop(device_delegate_uuid)

    def get_child_delegates(self):
        return self.device_delegates

    def handleNotification(self, cHandle, data):
        print ("Notification from Handle: 0x" + format(cHandle,'02X') + " Value: {0}".format(data))

        for device_delegate_uuid, device_delegate in self.device_delegates.items():
            device_delegate.handleNotification(cHandle, data)

class GenericBTLEDevice:
    def __init__(self, PERIPHERAL_ID, telemetry_connection_params = None):
        self.PERIPHERAL_ID = PERIPHERAL_ID
        self.MonitorNotificationsFlag = False
        self.telemetry_connection_params = telemetry_connection_params

        self.enable_telemetry = (self.telemetry_connection_params is not None)

        # Setup Transaction Queue Class
        self.btle_transaction_queue = queue.Queue(100) # Max of 100 items in the queue. I don't think this will be reached but just in case...

        self.connected = False

    def connect(self, connection_type = "public", retries = 5):

        while retries >= 0:
            try:
                self.p = Peripheral(self.PERIPHERAL_ID, connection_type)
                self.connected = True
                break
            except BTLEDisconnectError as e:
                print("{0}. Retries left: {1}".format(e, retries))
                retries = retries - 1

        if retries < 0:
            print("Failed to connect to device {0}".format(self.PERIPHERAL_ID))
            self.connected = False
            return

        self.setup_notification_delegates()

    def queue_write_transaction(self, characteristic_handle, message, withResponse=False, time_to_sleep_for_after_transaction_seconds=0):
        # time_to_sleep_for_after_transaction_seconds is a VERY powerful thing that will block the current 
        # notifications thread so don't abuse it please
        self.btle_transaction_queue.put_nowait((characteristic_handle, message, withResponse, time_to_sleep_for_after_transaction_seconds))

    def toggle_notifications_for_characteristic(self, characteristic, enable=True):
        self.queue_write_transaction(characteristic.getHandle() + 1, bytes([enable]) + b'\x00', withResponse=True)

    # Note! Only call this in connect when self.p has been set
    def setup_notification_delegates(self):

        # Setup Delegates
        if self.enable_telemetry:
            self.connect_to_telemetry_server(self.telemetry_connection_params)
            self.overall_delegate = OverallDelegate(telemetry_connection = self.conn)
            self.send_state_message(self.generate_ble_connection_message(connected=True))
        else:
            self.overall_delegate = OverallDelegate()

        self.p.setDelegate(self.overall_delegate)

    def monitor_notifications_loop(self, notification_timeout = 1):
        counter = 0
        while True:

            if not self.MonitorNotificationsFlag:
                break

            try:
                while not self.btle_transaction_queue.empty():

                    transaction_command = self.btle_transaction_queue.get_nowait()   # get() without blocking. If no item is available, raises an Empty Exception (which hopefully shouldn't occur)

                    print(transaction_command)
                    handle, message, withResponse, time_to_sleep_for_after_transaction_seconds = transaction_command
                    self.p.writeCharacteristic(handle, message, withResponse)
                    if time_to_sleep_for_after_transaction_seconds > 0:
                        time.sleep(time_to_sleep_for_after_transaction_seconds)
                    # time.sleep(0.05)   # Add this to try to combat problems when we spam the BLE receiver with commands
                
                try:
                    wait_for_notifications_res = self.p.waitForNotifications(notification_timeout)
                except BTLEInternalError:
                    print("Internal error, set wait_for_notifications_res to False")
                    wait_for_notifications_res = False

            except BTLEDisconnectError:
                self.handle_disconnection()
                self.MonitorNotificationsFlag = False
                break

            if wait_for_notifications_res:   #10 * (1/60)):
                counter = 1
                continue
            print(counter, "Waiting for Notifications from: {0}...".format(self.PERIPHERAL_ID))
            counter = counter + 1

        print("Monitoring Notifications Thread for {0} has been stopped!".format(self.PERIPHERAL_ID))
        print("There are currently {0} threads left".format(threading.enumerate()))
        return

    def startMonitoringNotifications(self, notification_timeout = 3):
        self.MonitorNotificationsFlag = True

        # self.monitor_notifications_loop()
        t = Thread(target=self.monitor_notifications_loop, args=(notification_timeout, ))
        
        print("Started on Thread {0}, ident {1}".format(t.name, t.ident))
        print("There are {0} threads alive".format(len(threading.enumerate())))

        t.start()
       
    def stopMonitoringNotifications(self):
        self.MonitorNotificationsFlag = False

    def handle_disconnection(self):
        print("Device {0} disconnected!".format(self.PERIPHERAL_ID))
        # self.p.disconnect()
        self.connected = False    # This is used to signal to the main loop to delete the current object
        self.send_state_message(self.generate_ble_connection_message(connected=self.connected))
        self.disconnect_from_telemetry_server()
        self.stopMonitoringNotifications()


    ##################################### Setup IOTC connection ########################################
    def connect_to_telemetry_server(self, connection_params):
        deviceId, scopeId, deviceKey = connection_params
        self.conn = AzureIOTCConnection.AzureIOTCConnection(deviceId, scopeId, deviceKey, self.PERIPHERAL_ID)
        self.conn.connect()

    def send_telemetry_message(self, message):
        self.conn.sendTelemetry(message)
        self.conn.doNext()

    def send_state_message(self, message):
        self.conn.sendState(message)
        self.conn.doNext()

    @staticmethod
    def generate_ble_connection_message(connected=True):
        return "{\"connected\": \"" + str(connected) + "\" }"

    def disconnect_from_telemetry_server(self):
        self.conn.disconnect()