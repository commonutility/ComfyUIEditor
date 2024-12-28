import os
from typing import Optional

class Config:
    def __init__(self):
        self.api_key: Optional[str] = os.environ.get('ANTHROPIC_API_KEY')

    def validate(self) -> bool:
        """Validate that required configuration is present"""
        return bool(self.api_key)

    def get_api_key(self) -> str:
        """Get the API key or raise an exception if not configured"""
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Please set it with your Claude API key."
            )
        return self.api_key
