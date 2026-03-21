"""
VoiceDataCollectionAgent
------------------------
LiveKit Agent subclass that collects customer data via voice call.
Uses PromptFactory for dynamic instructions based on required fields.
Provides @function_tool for saving collected data and ending the call.
"""
import json
import logging
from typing import Any

from livekit.agents import Agent, function_tool, RunContext

from src.core.prompts.factory import PromptFactory

logger = logging.getLogger(__name__)

# Default fields to collect if none specified
DEFAULT_FIELDS = [
    "Họ và tên (full_name)",
    "Số điện thoại (phone_number)",
    "Số bảo hiểm y tế (health_insurance_number)",
    "Tiền sử bệnh lý (medical_history)",
    "Triệu chứng hiện tại (symptoms)",
]


class VoiceDataCollectionAgent(Agent):
    """LiveKit voice agent that collects customer information via conversation."""

    def __init__(self, fields: list[str] | None = None) -> None:
        fields_list = fields or DEFAULT_FIELDS
        fields_description = "\n".join(f"   - {f}" for f in fields_list)

        instructions = PromptFactory.render(
            "voice_data_collection",
            fields_description=fields_description,
        )

        super().__init__(instructions=instructions)
        self._fields = fields_list
        self._collected_data: dict = {}

    @function_tool()
    async def save_collected_data(
        self,
        context: RunContext,
        data_json: str,
    ) -> str:
        """Lưu thông tin đã thu thập được từ khách hàng.

        Args:
            data_json: JSON string chứa các trường thông tin đã thu thập.
                       Ví dụ: {"full_name": "Nguyễn Văn A", "phone_number": "0912345678"}
        """
        try:
            self._collected_data = json.loads(data_json)
            logger.info(f"Collected data saved: {self._collected_data}")

            # Publish data to room metadata so FastAPI can retrieve it
            room = context.session.room
            if room and room.local_participant:
                await room.local_participant.set_attributes(
                    {"collected_data": data_json, "status": "completed"}
                )

            return "Đã lưu thông tin thành công."
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from LLM: {e}")
            return "Lỗi: Dữ liệu không hợp lệ. Hãy thử lại với JSON đúng định dạng."

    @function_tool()
    async def end_call(self, context: RunContext) -> str:
        """Kết thúc cuộc gọi sau khi đã thu thập đủ thông tin và cảm ơn khách hàng."""
        logger.info("Voice call ended by agent.")
        await context.session.aclose()
        return "Cuộc gọi đã kết thúc."

    @property
    def collected_data(self) -> dict:
        """Return the collected data dictionary."""
        return self._collected_data
