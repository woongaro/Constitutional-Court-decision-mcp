"""
Constitutional Court Decision MCP Server
법제처 헌재결정례 Open API wrapper
"""

import json
import os
from typing import Any

import httpx
import xmltodict
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

OC = os.getenv("OC", "woongaro")
SEARCH_URL = "http://www.law.go.kr/DRF/lawSearch.do"
SERVICE_URL = "http://www.law.go.kr/DRF/lawService.do"
TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=5.0, pool=5.0)

mcp = FastMCP("헌재결정례")


async def fetch(base_url: str, params: dict[str, Any]) -> dict | str:
    """
    Fetch from law.go.kr API using async httpx client.
    Tries JSON first; falls back to XML if JSON parsing fails.
    Returns parsed dict or error string.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # JSON attempt
        json_params = {**params, "type": "JSON"}
        try:
            response = await client.get(base_url, params=json_params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return f"API 오류: HTTP {e.response.status_code}"
        except httpx.TimeoutException:
            return "요청 시간 초과"
        except (json.JSONDecodeError, ValueError):
            pass  # fall through to XML retry

        # XML fallback
        xml_params = {**params, "type": "XML"}
        try:
            response = await client.get(base_url, params=xml_params)
            response.raise_for_status()
            return xmltodict.parse(response.content)
        except httpx.HTTPStatusError as e:
            return f"API 오류: HTTP {e.response.status_code}"
        except httpx.TimeoutException:
            return "요청 시간 초과"
        except Exception:
            return "응답 파싱 실패"


def parse_search_response(raw: dict) -> dict | str:
    """Normalize search response to consistent structure."""
    data = raw.get("DetcSearch", {})
    total = data.get("totalCnt", "0")
    try:
        if int(total) == 0 or "detc" not in data:
            return "검색 결과가 없습니다"
    except (ValueError, TypeError):
        return "검색 결과가 없습니다"

    items = data["detc"]
    # xmltodict returns a single item as dict, not list
    if isinstance(items, dict):
        items = [items]

    decisions = []
    for item in items:
        # NOTE: 'detcLnkUrl' is the assumed JSON key for 상세링크.
        # Verify against live API response — the actual key may differ.
        decisions.append({
            "일련번호": item.get("헌재결정례일련번호", ""),
            "사건번호": item.get("사건번호", ""),
            "사건명": item.get("사건명", ""),
            "종국일자": item.get("종국일자", ""),
            "상세링크": item.get("detcLnkUrl", ""),
        })

    return {
        "totalCnt": str(total),
        "page": data.get("page", "1"),
        "decisions": decisions,
    }


def parse_decision_response(raw: dict) -> dict | str:
    """Normalize decision content response."""
    data = raw.get("DetcService", {})
    if not data:
        return "결정문을 찾을 수 없습니다"

    return {
        "사건번호": data.get("사건번호", ""),
        "사건명": data.get("사건명", ""),
        "종국일자": data.get("종국일자", ""),
        "결정요지": data.get("결정요지", ""),
        "결정문": data.get("결정문", ""),
    }


def main():
    mcp.run()


if __name__ == "__main__":
    main()
