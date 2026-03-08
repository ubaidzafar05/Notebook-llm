from __future__ import annotations

from components import chat_panel
from services.api_client import ApiClient


def render(client: ApiClient) -> None:
    chat_panel.render(client)
