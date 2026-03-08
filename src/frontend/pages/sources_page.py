from __future__ import annotations

from components import source_panel
from services.api_client import ApiClient


def render(client: ApiClient) -> None:
    source_panel.render(client)
