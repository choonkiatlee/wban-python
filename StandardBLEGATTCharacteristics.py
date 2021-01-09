from bluepy.btle import UUID


# Services from service/blte/GattService.java
UUID_SERVICE_HEART_RATE = UUID("180D")
UUID_SERVICE_IMMEDIATE_ALERT = UUID("1802")
UUID_SERVICE_ALERT_NOTIFICATION = UUID("1811")


# Characteristics from service/blte/GattCharacteristic.java
UUID_CHARACTERISTIC_HEART_RATE_CONTROL_POINT = [UUID_SERVICE_HEART_RATE,UUID("2A39")]
UUID_CHARACTERISTIC_HEART_RATE_MEASUREMENT = [UUID_SERVICE_HEART_RATE,UUID("2A37")]

UUID_CHARACTERISTIC_ALERT_LEVEL = [UUID_SERVICE_IMMEDIATE_ALERT, UUID("2A06")]
UUID_CHARACTERISTIC_NEW_ALERT = [UUID_SERVICE_ALERT_NOTIFICATION, UUID("2A46")]
UUID_CHARACTERISTIC_ALERT_NOTIFICATION_CONTROL_POINT = [UUID_SERVICE_ALERT_NOTIFICATION, UUID("2A44")]