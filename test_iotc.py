import iotc
from iotc import IOTConnectType, IOTLogLevel, IOTQosLevel

import random

deviceId = "0b352d3f-1f91-4c4a-94e8-4e3b6b7dcdf2"
scopeId = "0ne000BC625"
deviceKey = "oU+XsFICYix8pWV3bFHWS5QN7UN2sMXc0HhJL0FtkRw="

# see iotc.Device documentation above for x509 argument sample
iotc = iotc.Device(scopeId, deviceKey, deviceId, IOTConnectType.IOTC_CONNECT_SYMM_KEY)
iotc.setLogLevel(IOTLogLevel.IOTC_LOGGING_API_ONLY)
iotc.setQosLevel(IOTQosLevel.IOTC_QOS_AT_MOST_ONCE)

gCanSend = False
gCounter = 0

def onconnect(info):
  global gCanSend
  print("- [onconnect] => status:" + str(info.getStatusCode()))
  if info.getStatusCode() == 0:
     if iotc.isConnected():
       gCanSend = True

def onmessagesent(info):
  print("\t- [onmessagesent] => " + str(info.getPayload()))

def oncommand(info):
  print("command name:", info.getTag())
  print("command value: ", info.getPayload())

def onsettingsupdated(info):
  print("setting name:", info.getTag())
  print("setting value: ", info.getPayload())

iotc.on("ConnectionStatus", onconnect)
iotc.on("MessageSent", onmessagesent)
iotc.on("Command", oncommand)
iotc.on("SettingsUpdated", onsettingsupdated)

iotc.connect()

while iotc.isConnected():
  iotc.doNext() # do the async work needed to be done for MQTT
  if gCanSend == True:
    if gCounter % 20 == 0:
      gCounter = 0
      print("Sending telemetry..")
      iotc.sendTelemetry("{\"water_drunk\": " + str(random.randint(20, 45)) + "}")
    gCounter += 1