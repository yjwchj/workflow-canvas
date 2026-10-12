from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = ''
    mysql_host: str = '127.0.0.1'
    mysql_port: int = 3306
    mysql_user: str = 'canvas'
    mysql_password: str = 'canvas'
    mysql_database: str = 'canvas'
    redis_url: str = 'redis://127.0.0.1:6379/0'
    media_dir: Path = Path('data/media')
    comfyui_url: str = 'http://127.0.0.1:8188'
    runninghub_url: str = 'https://www.runninghub.ai'
    runninghub_api_key: str = ''
    admin_username: str = ''
    admin_password: str = ''
    secure_cookies: bool = False
    provider_timeout: int = 1800
    max_image_bytes: int = 20 * 1024 * 1024


settings = Settings()
