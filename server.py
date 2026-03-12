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
        except httpx.RequestError as e:
            return f"네트워크 오류: {type(e).__name__}"
        except Exception:
            return "응답 파싱 실패"


def parse_search_response(raw: dict) -> dict | str:
    """Normalize search response to consistent structure."""
    data = raw.get("DetcSearch", {})
    total = data.get("totalCnt", "0")

    # API returns "Detc" (capital D); XML/mock fixtures may use "detc" (lower)
    items_raw = data.get("Detc") or data.get("detc")

    try:
        if int(total) == 0 or items_raw is None:
            return "검색 결과가 없습니다"
    except (ValueError, TypeError):
        return "검색 결과가 없습니다"

    items = items_raw
    # xmltodict returns a single item as dict, not list
    if isinstance(items, dict):
        items = [items]

    decisions = []
    for item in items:
        decisions.append({
            "일련번호": item.get("헌재결정례일련번호", ""),
            "사건번호": item.get("사건번호", ""),
            "사건명": item.get("사건명", ""),
            "종국일자": item.get("종국일자", ""),
            "상세링크": (
                item.get("헌재결정례상세링크")
                or item.get("detcLnkUrl")
                or item.get("헌재결정례 상세링크")
                or item.get("lnkUrl")
                or ""
            ),
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

    # Live API stores full text in "전문"; test fixtures and XML fallback may use "결정문"
    full_text = data.get("결정문") or data.get("전문") or ""

    return {
        "사건번호": data.get("사건번호", ""),
        "사건명": data.get("사건명", ""),
        "종국일자": data.get("종국일자", ""),
        "결정요지": data.get("결정요지", ""),
        "결정문": full_text,
    }


@mcp.tool()
async def search_decisions(
    query: str = "",
    page: int = 1,
    display: int = 20,
    sort: str = "lasc",
    date: int | None = None,
    date_range: str | None = None,
    search: int = 1,
    case_number: int | None = None,
) -> str:
    """
    헌재결정례(Constitutional Court Decision) 목록을 검색합니다.

    Args:
        query: 검색 키워드 (사건명 또는 본문)
        page: 페이지 번호 (기본값: 1)
        display: 페이지당 결과 수 (기본값: 20, 최대: 100)
        sort: 정렬 (lasc=사건명오름차순, ldes=사건명내림차순, dasc=선고일자오름차순, ddes=선고일자내림차순, nasc=사건번호오름차순, ndes=사건번호내림차순, efasc=종국일자오름차순, efdes=종국일자내림차순)
        date: 종국일자 YYYYMMDD 정수 (예: 20201010)
        date_range: 종국일자 기간 (예: "20200101~20201231")
        search: 검색범위 (1=사건명, 2=본문검색)
        case_number: 사건번호로 검색
    """
    params: dict[str, Any] = {
        "OC": OC,
        "target": "detc",
        "page": page,
        "display": display,
        "sort": sort,
        "search": search,
    }
    if query:
        params["query"] = query
    if date is not None:
        params["date"] = date
    if date_range:
        params["edYd"] = date_range
    if case_number is not None:
        params["nb"] = case_number

    raw = await fetch(SEARCH_URL, params)
    if isinstance(raw, str):
        return raw

    result = parse_search_response(raw)
    if isinstance(result, str):
        return result

    lines = [f"총 {result['totalCnt']}건 (페이지 {result['page']})\n"]
    for d in result["decisions"]:
        lines.append(
            f"[{d['일련번호']}] {d['사건번호']} — {d['사건명']}\n"
            f"  종국일자: {d['종국일자']}\n"
            f"  링크: {d['상세링크']}\n"
        )
    return "\n".join(lines)


@mcp.tool()
async def get_decision(decision_id: str) -> str:
    """
    헌재결정례 본문을 조회합니다.

    Args:
        decision_id: 헌재결정례일련번호 (search_decisions 결과의 일련번호 값)
    """
    params: dict[str, Any] = {
        "OC": OC,
        "target": "detc",
        "ID": decision_id,
    }

    raw = await fetch(SERVICE_URL, params)
    if isinstance(raw, str):
        return raw

    result = parse_decision_response(raw)
    if isinstance(result, str):
        return result

    lines = [
        f"사건번호: {result['사건번호']}",
        f"사건명: {result['사건명']}",
        f"종국일자: {result['종국일자']}",
        "",
        "【결정요지】",
        result["결정요지"] or "(없음)",
        "",
        "【결정문】",
        result["결정문"] or "(없음)",
    ]
    return "\n".join(lines)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
