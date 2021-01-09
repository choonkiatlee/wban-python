from bluepy.btle import Scanner, DefaultDelegate, BTLEManagementError
from multiprocessing import Process, Event, Manager, JoinableQueue


class ScanDelegate(DefaultDelegate):
    def __init__(self, BLEScanner):
        DefaultDelegate.__init__(self)
        self.BLEScanner = BLEScanner

    def handleDiscovery(self, dev, isNewDev, isNewData):
        
        if dev.addr in self.BLEScanner.devices_to_check_for:
            # print("Discovered device {0}, RSSI: {1}".format(dev.addr, dev.rssi))
            self.BLEScanner.devices_to_check_for[dev.addr] = dev.rssi

# Multithreaded BLEScanner. Use this to get RSSIs from devices
class BLEScanner:

    def __init__(self, devices_to_check_for, scan_delegate_class):

        self.manager = Manager()
        self.devices_to_check_for = self.manager.dict()

        for key in devices_to_check_for:
            self.devices_to_check_for[key] = devices_to_check_for[key]

        self.to_connect_queue = JoinableQueue()

        self.scanner = Scanner().withDelegate(scan_delegate_class(self))
        self.stopped = False

    def start(self):
        self.stop_event = Event()
        self.stop_event.clear()

        self.process_connection_event = Event()
        self.process_connection_event.clear()

        # Need to use multiprocessing to start this in a new process
        # This is because the Scanner code in bluepy-helper sets the state of currently connected devices to "disconnected"
        # Thus, if the connected device code is in another thread waiting for notifications, this will
        # cause it to raise a BTLEDisconnectedError even though the device is actually still connected.

        # The workaround is to start the scanning in a new _process_ instead. This will create a whole new copy
        # of bluepy-helper, which allows the scanner to do whatever it want to the device state in its copy of 
        # bluepy-helper and not have to worry about screwing up the device state in the connected BLE object
        self.process = Process(target=self.scan, args = ())   
        self.process.start()

        print("Started Scan")

        return self

    def scan(self):
        while True:

            if self.stop_event.is_set():
                return

            # Delay if still connecting (There are devices on the queue that are not done yet)
            self.to_connect_queue.join()

            # Done waiting: clear the process_connection_event bit
            self.process_connection_event.clear()

            self.devices = self.scanner.scan(5, passive=True)

            # If there are devices that we need to connect to, signal that we want to connect to them to the main process.
            # The following line will 
            if not self.to_connect_queue.empty():
                self.process_connection_event.set()     


    def stop(self):
        # self.stopped = True  
        self.stop_event.set()    


if __name__ == "__main__":

    PERIPHERAL_ID = "CA:0A:FB:47:1A:95"
    
    # Dictionary of {ID : RSSI}
    wanted_device_rssis = {
        PERIPHERAL_ID.lower():0
    }

    # Start scan in new thread
    blescanner = BLEScanner(wanted_device_rssis, ScanDelegate).start()

    print("Started Scan")

    import time

    for i in range(10):
        time.sleep(3)
        print(blescanner.devices_to_check_for)

    blescanner.stop()



# Sample code

# from multiprocessing import Process, Event

# class BLEScanner:
#     def __init__(self):
#         self.scanner = Scanner().withDelegate(ScanDelegate())

#         self.stop_event = Event()

#     def start(self):

#         self.stop_event.clear()

#         self.process = Process(target=self.scan, args = ())
#         self.process.start()
#         return self

#     def scan(self):
#         while True:

#             if self.stop_event.is_set():
#                 return

#             self.devices = self.scanner.scan(5, passive=True)

#     def stop(self):
#         self.stop_event.set()  

# Usage: 
# BLEScanner().start()