from __future__ import annotations

from components import studio_panel
from services.api_client import ApiClient


def render(client: ApiClient) -> None:
    studio_panel.render(client)
