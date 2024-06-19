from pydantic import BaseModel
from typing import Optional, Union


class AzureASRData(BaseModel):
    text: Union[str, dict]
    language: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": [
                {
                    "text": "Hello World",
                    "language": "en-US",
                },
                {
                    "text": "你好世界",
                    "language": "zh-CN",
                }
            ]
        }
