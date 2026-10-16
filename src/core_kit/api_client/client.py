from typing import Any, Dict, Optional
import httpx


class BaseApiClient:
    """
    Client HTTP chuẩn dùng trong PySide6 Desktop App để giao tiếp với FastAPI Backend.
    Tự động quản lý Access Token, gắn header xác thực và bắt lỗi kết nối.
    """

    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.token: Optional[str] = None
        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def set_token(self, token: str):
        """Lưu Access Token sau khi đăng nhập thành công."""
        self.token = token

    def clear_token(self):
        """Xóa token khi người dùng đăng xuất."""
        self.token = None

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Gửi request GET và trả về dữ liệu JSON."""
        response = self._client.get(endpoint, params=params, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Gửi request POST và trả về dữ liệu JSON."""
        response = self._client.post(endpoint, json=json_data, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    def put(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Gửi request PUT và trả về dữ liệu JSON."""
        response = self._client.put(endpoint, json=json_data, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    def delete(self, endpoint: str) -> Dict[str, Any]:
        """Gửi request DELETE và trả về dữ liệu JSON."""
        response = self._client.delete(endpoint, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    def close(self):
        """Đóng kết nối client HTTP."""
        self._client.close()
