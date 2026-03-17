import logging
import time
import paho.mqtt.client as mqtt
from app.config import settings

logger = logging.getLogger(__name__)


class TrafficMQTTClient:
    def __init__(self):
        self.connected = False
        self._attempts = 0
        self._max_attempts = 3
        client_id = f"traffic_{int(time.time())}"
        self.client = mqtt.Client(client_id=client_id)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.reconnect_delay_set(min_delay=10, max_delay=60)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            self._attempts = 0
            logger.info("MQTT connected")
        else:
            logger.warning(f"MQTT connect failed rc={rc}")

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        self._attempts += 1
        if self._attempts >= self._max_attempts:
            logger.warning("MQTT unavailable after 3 attempts. Disabled.")
            try:
                self.client.loop_stop()
            except Exception:
                pass
            return
        logger.warning(f"MQTT disconnect rc={rc}, attempt {self._attempts}")

    def connect(self):
        try:
            self.client.connect(
                settings.MQTT_BROKER_HOST,
                settings.MQTT_BROKER_PORT,
                keepalive=60
            )
            self.client.loop_start()
        except Exception as e:
            logger.warning(f"MQTT unavailable: {e}. Running without broker.")

    def publish(self, topic: str, payload: str):
        if not self.connected:
            return
        try:
            self.client.publish(topic, payload)
        except Exception:
            pass

    def disconnect(self):
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass

    def is_available(self) -> bool:
        return self.connected


# Alias for backward compatibility
MQTTClient = TrafficMQTTClient
mqtt_client = TrafficMQTTClient()
