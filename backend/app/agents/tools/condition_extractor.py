"""出張条件抽出ツール"""
from typing import Any, Dict, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class ConditionExtractorInput(BaseModel):
    """条件抽出入力"""
    user_message: str = Field(..., description="ユーザーのメッセージ")


class ConditionExtractorTool(BaseTool):
    """ユーザーのメッセージから出張条件を抽出するツール"""
    
    name: str = "condition_extractor"
    description: str = """ユーザーのメッセージから出張の条件（日程、目的地、予算など）を抽出します。
    抽出できた項目と、まだ確認が必要な項目を返します。"""
    args_schema: type[BaseModel] = ConditionExtractorInput
    
    def _run(self, user_message: str) -> Dict[str, Any]:
        """条件を抽出（このツールは主にLLMのプロンプトで処理される）"""
        # このツールは実際にはLLMが条件を抽出するための
        # インターフェースとして機能する
        # 実際の抽出ロジックはエージェントのプロンプトで行う
        return {
            "message": user_message,
            "instruction": "このメッセージから出張条件を抽出してください"
        }
    
    async def _arun(self, user_message: str) -> Dict[str, Any]:
        """非同期実行"""
        return self._run(user_message)



