import base64
import httpx
from app.config import settings


class WhatsAppService:
    """Evolution API wrapper — swap to Meta Cloud API by changing this file only."""

    def __init__(self):
        self.base_url = settings.EVOLUTION_API_URL.rstrip("/")
        self.api_key = settings.EVOLUTION_API_KEY
        self.instance = settings.EVOLUTION_INSTANCE

    def _headers(self) -> dict:
        return {"apikey": self.api_key, "Content-Type": "application/json"}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        timeout: float = 15,
    ) -> dict:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.request(
                    method, url, headers=self._headers(), json=json
                )
                if response.status_code in (200, 201):
                    try:
                        data = response.json()
                    except Exception:
                        data = {"raw": response.text}
                    return {"success": True, "data": data, "status_code": response.status_code}
                return {
                    "success": False,
                    "error": response.text or f"HTTP {response.status_code}",
                    "status_code": response.status_code,
                }
            except Exception as e:
                return {"success": False, "error": str(e), "status_code": 0}

    async def send_message(self, to: str, body: str) -> dict:
        """Send a text message via Evolution API."""
        result = await self._request(
            "POST",
            f"/message/sendText/{self.instance}",
            json={"number": to, "text": body},
        )
        if result.get("success"):
            data = result.get("data") or {}
            message_id = ""
            if isinstance(data, dict):
                message_id = (data.get("key") or {}).get("id", "") or data.get("messageId", "")
            return {"success": True, "message_id": message_id, "data": data}
        return {"success": False, "error": result.get("error", "send failed")}

    async def connection_state(self) -> dict:
        """Return Evolution instance connection state."""
        # Prefer GET; some builds only accept POST
        result = await self._request("GET", f"/instance/connectionState/{self.instance}")
        if not result.get("success"):
            result = await self._request("POST", f"/instance/connectionState/{self.instance}")
        if not result.get("success"):
            return {
                "success": False,
                "state": "unknown",
                "instance": self.instance,
                "error": result.get("error"),
            }
        data = result.get("data") or {}
        state = "unknown"
        if isinstance(data, dict):
            instance = data.get("instance") or data
            if isinstance(instance, dict):
                state = instance.get("state") or instance.get("status") or state
            else:
                state = data.get("state") or data.get("status") or state
        return {
            "success": True,
            "state": str(state).lower(),
            "instance": self.instance,
            "raw": data,
        }

    async def connect_qr(self) -> dict:
        """Fetch QR / pairing payload to connect the WhatsApp instance."""
        result = await self._request("GET", f"/instance/connect/{self.instance}", timeout=30)
        if not result.get("success"):
            return {"success": False, "error": result.get("error"), "instance": self.instance}
        data = result.get("data") or {}
        qr = None
        pairing_code = None
        if isinstance(data, dict):
            qr = data.get("base64") or data.get("qrcode") or data.get("code")
            if isinstance(qr, dict):
                qr = qr.get("base64") or qr.get("code")
            pairing_code = data.get("pairingCode") or data.get("pairing_code")
        return {
            "success": True,
            "instance": self.instance,
            "qr": qr,
            "pairing_code": pairing_code,
            "raw": data,
        }

    async def find_chats(self) -> dict:
        """List chats from Evolution."""
        result = await self._request("POST", f"/chat/findChats/{self.instance}", json={})
        if not result.get("success"):
            return {"success": False, "error": result.get("error"), "chats": []}
        data = result.get("data")
        chats = data if isinstance(data, list) else (data.get("chats") if isinstance(data, dict) else [])
        if not isinstance(chats, list):
            chats = []
        return {"success": True, "chats": chats}

    async def find_messages(self, remote_jid: str, limit: int = 50) -> dict:
        """List messages for a remote JID."""
        body = {
            "where": {"key": {"remoteJid": remote_jid}},
            "limit": limit,
        }
        result = await self._request(
            "POST", f"/chat/findMessages/{self.instance}", json=body, timeout=30
        )
        if not result.get("success"):
            return {"success": False, "error": result.get("error"), "messages": []}
        data = result.get("data")
        messages = []
        if isinstance(data, list):
            messages = data
        elif isinstance(data, dict):
            messages = data.get("messages") or data.get("records") or []
            if isinstance(messages, dict):
                messages = messages.get("records") or messages.get("messages") or []
        if not isinstance(messages, list):
            messages = []
        return {"success": True, "messages": messages}

    async def download_media(self, message_id: str) -> tuple[bytes, str]:
        """Download media for a given message. Returns (bytes, mime_type)."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/chat/getMedia/{self.instance}",
                headers=self._headers(),
                json={"message": {"key": {"id": message_id}}},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            media_b64 = data.get("media", "")
            mime_type = data.get("mimetype", "application/octet-stream")
            return base64.b64decode(media_b64), mime_type


whatsapp_service = WhatsAppService()
