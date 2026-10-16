from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
    """
    Lớp cấu hình cơ sở đọc từ file .env và biến môi trường.
    """
    app_name: str = Field(default="MyApplication", description="Tên ứng dụng")
    env: str = Field(default="development", description="Môi trường: development, production, test")
    debug: bool = Field(default=True, description="Chế độ debug")

    # Cấu hình Database
    database_url: str = Field(
        default="sqlite:///./app.db",
        description="Đường dẫn kết nối Database (sqlite, postgresql, mysql,...)"
    )

    # Cấu hình API Server
    api_host: str = Field(default="0.0.0.0", description="Host lắng nghe của FastAPI")
    api_port: int = Field(default=8000, description="Port lắng nghe của FastAPI")
    api_base_url: str = Field(default="http://localhost:8000", description="Base URL cho client kết nối")

    # Cấu hình Bảo mật & Token
    secret_key: str = Field(default="change-this-in-production-secret-key-32bytes", description="Secret key ký JWT")
    jwt_algorithm: str = Field(default="HS256", description="Thuật toán mã hóa JWT")
    access_token_expire_minutes: int = Field(default=60 * 24, description="Thời gian sống của token (phút)")

    # Cấu hình Logging
    log_level: str = Field(default="INFO", description="Mức độ log: DEBUG, INFO, WARNING, ERROR")
    log_dir: str = Field(default="logs", description="Thư mục lưu trữ file log")

    # Cấu hình Thiết bị ngoại vi
    serial_port: str = Field(default="COM1", description="Cổng COM mặc định cho thiết bị/máy in")
    serial_baudrate: int = Field(default=9600, description="Tốc độ Baudrate của cổng Serial")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
