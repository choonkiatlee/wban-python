import iotc
from iotc import IOTConnectType, IOTLogLevel, IOTQosLevel

import random


class AzureIOTCConnection:

    def __init__(self, deviceId, scopeId, deviceKey, deviceIdentifier):
        self.deviceId = deviceId
        self.scopeId = scopeId
        self.deviceKey = deviceKey

        # This is a device Identifier for us: MAC Address?
        self.deviceIdentifier = deviceIdentifier

        self.connected = False

    def connect(self):
        self.conn = iotc.Device(self.scopeId, self.deviceKey, self.deviceId, IOTConnectType.IOTC_CONNECT_SYMM_KEY)
        self.conn.setLogLevel(IOTLogLevel.IOTC_LOGGING_API_ONLY)
        self.conn.setQosLevel(IOTQosLevel.IOTC_QOS_AT_MOST_ONCE)

        self.conn.on("ConnectionStatus", self.onconnect)
        self.conn.on("MessageSent", self.onmessagesent)

        self.conn.on("Command", self.oncommand)

        self.conn.connect()

    def disconnect(self):
        self.conn.disconnect()

    def onconnect(self, info):
        if info.getStatusCode() == 0:
            if self.conn.isConnected():
                self.connected = True
                print("Connected device {0}".format(self.deviceIdentifier))


    def onmessagesent(self, info):
        print("\t- [onmessagesent] => " + str(info.getPayload()))

    def oncommand(self,info):
        print("command name:", info.getTag())
        print("command value: ", info.getPayload())

    def sendTelemetry(self, message):
        self.conn.sendTelemetry(message)

    def sendState(self, message):
        self.conn.sendState(message)

    # do the async work needed to be done for MQTT # Do we need this?
    def doNext(self):
        self.conn.doNext()

if __name__ == "__main__":

    deviceId = "0b352d3f-1f91-4c4a-94e8-4e3b6b7dcdf2"
    scopeId = "0ne000BC625"
    deviceKey = "oU+XsFICYix8pWV3bFHWS5QN7UN2sMXc0HhJL0FtkRw="

    conn = AzureIOTCConnection(deviceId, scopeId, deviceKey)