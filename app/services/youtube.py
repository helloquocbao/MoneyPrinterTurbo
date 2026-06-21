"""
Dịch vụ tích hợp YouTube Data API v3 để tải video lên YouTube.
"""
import os
from loguru import logger
from app.config import config

# Thư viện Google API
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False


class YoutubeUploadService:
    """
    Dịch vụ tải video lên YouTube bằng YouTube Data API v3.
    """

    def __init__(self):
        self.enabled = config.youtube.get("youtube_upload_enabled", False)
        self.client_secrets_file = config.youtube.get("youtube_client_secrets_file", "client_secrets.json")
        self.credentials_file = config.youtube.get("youtube_credentials_file", "youtube_credentials.json")
        self.auto_upload = config.youtube.get("youtube_auto_upload", False)
        self.privacy_status = config.youtube.get("youtube_privacy_status", "private")

    def is_configured(self) -> bool:
        """Kiểm tra xem tính năng YouTube và các tệp cấu hình cần thiết đã sẵn sàng chưa."""
        if not GOOGLE_API_AVAILABLE:
            logger.warning("Thư viện google-api-python-client chưa được cài đặt.")
            return False

        if not self.enabled:
            return False

        # Tệp credentials lưu mã token đăng nhập phải tồn tại để tự động tải lên
        if not os.path.exists(self.credentials_file):
            logger.warning(
                f"Không tìm thấy tệp token xác thực YouTube tại '{self.credentials_file}'. "
                f"Vui lòng chạy script xác thực `youtube_auth.py` trước."
            )
            return False

        return True

    def upload_video(self, video_path: str, title: str, description: str = "", tags: list = None) -> dict:
        """
        Tải video lên YouTube.

        Args:
            video_path (str): Đường dẫn đến file video.
            title (str): Tiêu đề của video trên YouTube.
            description (str): Mô tả của video.
            tags (list): Danh sách thẻ gắn của video.

        Returns:
            dict: Kết quả phản hồi chứa success và video_id (hoặc error).
        """
        if not self.is_configured():
            return {"success": False, "error": "Dịch vụ YouTube chưa được cấu hình hoặc chưa xác thực tài khoản."}

        if not os.path.exists(video_path):
            logger.error(f"Không tìm thấy file video tại: {video_path}")
            return {"success": False, "error": f"Không tìm thấy file video tại: {video_path}"}

        logger.info(f"Bắt đầu tải video lên YouTube: {video_path}")

        try:
            # Tải thông tin credentials
            creds = Credentials.from_authorized_user_file(self.credentials_file)
            
            # Xây dựng client dịch vụ youtube
            youtube_client = build("youtube", "v3", credentials=creds)

            if not tags:
                tags = ["shorts", "moneyprinter", "ai"]

            # Khởi tạo body metadata
            body = {
                "snippet": {
                    "title": title[:100],  # YouTube giới hạn tiêu đề 100 kí tự
                    "description": description,
                    "tags": tags,
                    "categoryId": "22"  # Category 22 tương ứng với "People & Blogs"
                },
                "status": {
                    "privacyStatus": self.privacy_status,  # "private", "public", "unlisted"
                    "selfDeclaredMadeForKids": False
                }
            }

            # Thiết lập tải file
            media = MediaFileUpload(
                video_path,
                chunksize=1024 * 1024,
                mimetype="video/*",
                resumable=True
            )

            # Gửi request tải lên
            request = youtube_client.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )

            logger.info("Đang tải dữ liệu video lên YouTube...")
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"Đã tải lên {int(status.progress() * 100)}%")

            video_id = response.get("id")
            logger.success(f"🎉 Tải video lên YouTube thành công! Video ID: {video_id}")
            return {"success": True, "video_id": video_id}

        except HttpError as e:
            logger.error(f"Lỗi HTTP API YouTube: {e}")
            return {"success": False, "error": f"Lỗi HTTP API: {e.content.decode()}"}
        except Exception as e:
            logger.error(f"Lỗi không xác định khi tải lên YouTube: {str(e)}")
            return {"success": False, "error": str(e)}


# Khởi tạo instance duy nhất để sử dụng trong ứng dụng
youtube_service = YoutubeUploadService()
