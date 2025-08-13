from typing import Dict, Any

class ToolSpec(Dict[str, Any]):
    pass

class ToolRegistry:
    _tools: Dict[str, ToolSpec] = {
        "calendar_agent.read": {
            "description": "Read calendar events and free time blocks.",
            "inputs": {"window_days": "int"},
            "outputs": ["events", "free_blocks"]
        },
        "scheduler_agent.block_plan": {
            "description": "Generate a weekly plan given events, free blocks, and preferences.",
            "inputs": {"events": "list", "free_blocks": "list", "prefs": "dict"},
            "outputs": ["weekly_plan"]
        },
        "booking_agent.search_providers": {
            "description": "Search for providers (e.g., dentists) given insurance, location, and window.",
            "inputs": {"insurance": "str", "location": "str", "window_days": "int"},
            "outputs": ["provider_options"]
        },
        "booking_agent.propose": {
            "description": "Propose ranked appointment slots.",
            "inputs": {"options": "list", "free_blocks": "list"},
            "outputs": ["ranked_slot_proposals"]
        },
        "email_agent.draft_batch": {
            "description": "Draft email replies in batch.",
            "inputs": {"inbox_filter": "dict", "tone": "str"},
            "outputs": ["drafts"]
        }
    }

    @classmethod
    def get_tool(cls, name: str) -> ToolSpec:
        return cls._tools[name]

    @classmethod
    def all_tools(cls) -> Dict[str, ToolSpec]:
        return cls._tools