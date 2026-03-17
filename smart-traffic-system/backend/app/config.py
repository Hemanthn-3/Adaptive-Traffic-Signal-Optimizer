"""
Environment configuration via Pydantic Settings
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_ENV: str = "development"
    SECRET_KEY: str = "changeme"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://traffic_user:traffic_pass@localhost:5432/traffic_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # MQTT
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_USERNAME: str = ""
    MQTT_PASSWORD: str = ""
    MQTT_CLIENT_ID: str = "traffic_backend"

    # ML
    YOLO_MODEL_PATH: str = "yolov8n.pt"
    VEHICLE_CLASSES: str = "2,3,5,7"
    MAX_LANE_CAPACITY: int = 20
    FRAME_SKIP: int = 5

    # Signal Timing (seconds)
    MIN_GREEN_DURATION: int = 10
    MAX_GREEN_DURATION: int = 50     # min + max = 60s base cycle
    DEFAULT_YELLOW_DURATION: int = 3
    EMERGENCY_GREEN_DURATION: int = 90

    # Emergency Vehicle Detection
    EMERGENCY_DETECTION_CONFIDENCE: float = 0.7   # Confidence threshold (0.0-1.0)
    EMERGENCY_AUTO_CLEAR_SECONDS: int = 60        # Auto-clear duration for auto-detected emergencies
    EMERGENCY_RED_THRESHOLD: int = 15              # Min % of red pixels in vehicle bbox
    EMERGENCY_YELLOW_THRESHOLD: int = 15           # Min % of yellow pixels in vehicle bbox
    EMERGENCY_MIN_WIDTH_RATIO: float = 0.15        # Min vehicle width relative to frame width

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    @property
    def vehicle_class_ids(self) -> List[int]:
        return [int(c) for c in self.VEHICLE_CLASSES.split(",")]


settings = Settings()
