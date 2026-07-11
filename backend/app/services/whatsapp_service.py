import httpx
from app.config import settings


class WhatsAppService:
    """Evolution API wrapper — swap to Meta Cloud API by changing this file only."""

    def __init__(self):
        self.base_url = settings.EVOLUTION_API_URL
        self.api_key = settings.EVOLUTION_API_KEY
        self.instance = settings.EVOLUTION_INSTANCE

    async def send_message(self, to: str, body: str) -> dict:
        """Send a text message via Evolution API."""
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/message/sendText/{self.instance}",
                    headers={"apikey": self.api_key, "Content-Type": "application/json"},
                    json={"number": to, "text": body},
                )
                if response.status_code in (200, 201):
                    data = response.json()
                    return {"success": True, "message_id": data.get("key", {}).get("id", "")}
                return {"success": False, "error": response.text}
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def download_media(self, message_id: str) -> tuple[bytes, str]:
        """Download media for a given message. Returns (bytes, mime_type)."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/chat/getMedia/{self.instance}",
                headers={"apikey": self.api_key},
                json={"message": {"key": {"id": message_id}}},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            import base64
            media_b64 = data.get("media", "")
            mime_type = data.get("mimetype", "application/octet-stream")
            return base64.b64decode(media_b64), mime_type


whatsapp_service = WhatsAppService()
