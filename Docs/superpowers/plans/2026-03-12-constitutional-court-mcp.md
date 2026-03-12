# Constitutional Court Decision MCP Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python MCP server with two tools (`search_decisions`, `get_decision`) that wrap the law.go.kr 헌재결정례 Open API.

**Architecture:** Single `server.py` file using the `mcp` Python SDK (FastMCP). Async HTTP requests via `httpx.AsyncClient` with JSON-first parsing and `xmltodict` XML fallback. `OC` credential loaded from `.env`.

**Tech Stack:** Python 3.10+, `mcp[cli]`, `httpx`, `xmltodict`, `python-dotenv`, `pytest`, `pytest-httpx`, `pytest-asyncio`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `pyproject.toml` | Create | Project metadata, dependencies (including dev extras), entry point, pytest config |
| `.env.example` | Create | Document required environment variables |
| `conftest.py` | Create | Empty — ensures project root is on sys.path for all pytest versions |
| `server.py` | Create | MCP server, async API client, JSON/XML parser, both tools |
| `tests/__init__.py` | Create | Empty — marks tests as a package |
| `tests/test_server.py` | Create | Unit tests for parser and tool logic |

---

## Chunk 1: Project Scaffold

### Task 1: Create `pyproject.toml`, `conftest.py`, `.env.example`

**Files:**
- Create: `pyproject.toml`
- Create: `conftest.py`
- Create: `.env.example`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "constitutional-court-decision-mcp"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "mcp[cli]>=1.0.0",
    "httpx>=0.27.0",
    "xmltodict>=0.13.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-httpx>=0.30.0",
    "pytest-asyncio>=0.23.0",
]

[project.scripts]
constitutional-court-mcp = "server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
include = ["server.py"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 2: Create `conftest.py` at project root (empty file)**

This guarantees the project root is on `sys.path` so `from server import ...` works in tests.

```python
# conftest.py — intentionally empty, required for pytest path resolution
```

- [ ] **Step 3: Create `.env.example`**

```
OC=woongaro
```

- [ ] **Step 4: Install dependencies**

```bash
cd E:/mcp/Constitutional-Court-decision-mcp
pip install -e ".[dev]"
```

Expected: All packages install without error.

- [ ] **Step 5: Commit scaffold**

```bash
git add pyproject.toml conftest.py .env.example
git commit -m "chore: add project scaffold and dependencies"
```

---

## Chunk 2: Core Server — Async HTTP Client + Parsers

### Task 2: Write failing tests for async `fetch` and parsers

**Files:**
- Create: `tests/__init__.py` (empty)
- Create: `tests/test_server.py`

- [ ] **Step 1: Create `tests/__init__.py`**

Empty file.

- [ ] **Step 2: Write failing tests**

Create `tests/test_server.py`:

```python
import pytest
from pytest_httpx import HTTPXMock

# These imports will fail until server.py is created — that's expected
from server import fetch, parse_search_response, parse_decision_response


class TestFetch:
    async def test_fetch_returns_dict_on_json_success(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://www.law.go.kr/DRF/lawSearch.do?OC=woongaro&target=detc&query=%EB%B2%8C%EA%B8%88&type=JSON",
            json={"DetcSearch": {"totalCnt": "1", "detc": [{"사건번호": "2020헌바1"}]}},
        )
        result = await fetch(
            "http://www.law.go.kr/DRF/lawSearch.do",
            {"OC": "woongaro", "target": "detc", "query": "벌금"},
        )
        assert result == {"DetcSearch": {"totalCnt": "1", "detc": [{"사건번호": "2020헌바1"}]}}

    async def test_fetch_falls_back_to_xml_on_json_failure(self, httpx_mock: HTTPXMock):
        xml_body = b"""<?xml version="1.0"?>
<DetcSearch>
  <totalCnt>1</totalCnt>
  <detc><\xec\x82\xac\xea\xb1\xb4\xeb\xb2\x88\xed\x98\xb8>2020\xed\x97\x8c\xeb\xb0\x94 1</\xec\x82\xac\xea\xb1\xb4\xeb\xb2\x88\xed\x98\xb8></detc>
</DetcSearch>"""
        # JSON endpoint returns non-JSON text
        httpx_mock.add_response(
            url="http://www.law.go.kr/DRF/lawSearch.do?OC=woongaro&target=detc&query=%EB%B2%8C%EA%B8%88&type=JSON",
            text="<error>not json</error>",
        )
        httpx_mock.add_response(
            url="http://www.law.go.kr/DRF/lawSearch.do?OC=woongaro&target=detc&query=%EB%B2%8C%EA%B8%88&type=XML",
            content=b"""<?xml version="1.0"?><DetcSearch><totalCnt>1</totalCnt></DetcSearch>""",
        )
        result = await fetch(
            "http://www.law.go.kr/DRF/lawSearch.do",
            {"OC": "woongaro", "target": "detc", "query": "벌금"},
        )
        assert result["DetcSearch"]["totalCnt"] == "1"

    async def test_fetch_returns_error_string_on_http_error(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://www.law.go.kr/DRF/lawSearch.do?OC=woongaro&target=detc&type=JSON",
            status_code=500,
        )
        result = await fetch(
            "http://www.law.go.kr/DRF/lawSearch.do",
            {"OC": "woongaro", "target": "detc"},
        )
        assert "API 오류" in result
        assert "500" in result


class TestParseSearchResponse:
    def test_extracts_decisions_from_list(self):
        raw = {
            "DetcSearch": {
                "totalCnt": "1",
                "page": "1",
                "detc": [
                    {
                        "헌재결정례일련번호": "12345",
                        "종국일자": "20201010",
                        "사건번호": "2020헌바1",
                        "사건명": "벌금 위헌확인",
                        "detcLnkUrl": "http://example.com/12345",
                    }
                ],
            }
        }
        result = parse_search_response(raw)
        assert result["totalCnt"] == "1"
        assert len(result["decisions"]) == 1
        assert result["decisions"][0]["사건번호"] == "2020헌바1"
        assert result["decisions"][0]["일련번호"] == "12345"

    def test_returns_empty_message_when_no_results(self):
        raw = {"DetcSearch": {"totalCnt": "0", "page": "1"}}
        result = parse_search_response(raw)
        assert result == "검색 결과가 없습니다"

    def test_handles_single_result_as_dict_not_list(self):
        # xmltodict returns a single item as a dict, not a list
        raw = {
            "DetcSearch": {
                "totalCnt": "1",
                "page": "1",
                "detc": {
                    "헌재결정례일련번호": "99",
                    "종국일자": "20210101",
                    "사건번호": "2021헌바99",
                    "사건명": "테스트 사건",
                    "detcLnkUrl": "http://example.com/99",
                },
            }
        }
        result = parse_search_response(raw)
        assert len(result["decisions"]) == 1

    def test_handles_zero_totalcnt_as_int(self):
        raw = {"DetcSearch": {"totalCnt": 0, "page": "1"}}
        result = parse_search_response(raw)
        assert result == "검색 결과가 없습니다"


class TestParseDecisionResponse:
    def test_extracts_decision_fields(self):
        raw = {
            "DetcService": {
                "사건번호": "2020헌바1",
                "사건명": "벌금 위헌확인",
                "종국일자": "20201010",
                "결정요지": "이 사건 법률조항은 위헌이다.",
                "결정문": "주문: 위헌 선언...",
            }
        }
        result = parse_decision_response(raw)
        assert result["사건번호"] == "2020헌바1"
        assert result["결정요지"] == "이 사건 법률조항은 위헌이다."
        assert result["결정문"] == "주문: 위헌 선언..."

    def test_returns_error_when_no_data(self):
        result = parse_decision_response({})
        assert "결정문을 찾을 수 없습니다" in result
```

- [ ] **Step 3: Run tests — expect ImportError**

```bash
cd E:/mcp/Constitutional-Court-decision-mcp
pytest tests/test_server.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'server'`

---

### Task 3: Implement `server.py` — async `fetch` and parsers

**Files:**
- Create: `server.py`

- [ ] **Step 1: Write `server.py`**

```python
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
```

- [ ] **Step 2: Run parser and fetch tests**

```bash
pytest tests/test_server.py -v
```

Expected: All `TestParseSearchResponse`, `TestParseDecisionResponse`, and `TestFetch` tests PASS.

- [ ] **Step 3: Commit**

```bash
git add server.py tests/__init__.py tests/test_server.py
git commit -m "feat: add async HTTP client and JSON/XML parsers with tests"
```

---

## Chunk 3: MCP Tools

### Task 4: Implement `search_decisions` tool

**Files:**
- Modify: `server.py` — add `search_decisions` tool
- Modify: `tests/test_server.py` — add tool tests

- [ ] **Step 1: Write failing tests for `search_decisions`**

Append to `tests/test_server.py`:

```python
class TestSearchDecisionsTool:
    async def test_search_by_keyword(self, httpx_mock: HTTPXMock):
        # URL param order matches exact order built in search_decisions:
        # OC, target, page, display, sort, search, query — then type=JSON appended by fetch()
        httpx_mock.add_response(
            url=(
                "http://www.law.go.kr/DRF/lawSearch.do"
                "?OC=woongaro&target=detc&page=1&display=20&sort=lasc&search=1&query=%EB%B2%8C%EA%B8%88&type=JSON"
            ),
            json={
                "DetcSearch": {
                    "totalCnt": "1",
                    "page": "1",
                    "detc": {
                        "헌재결정례일련번호": "111",
                        "종국일자": "20200101",
                        "사건번호": "2019헌바1",
                        "사건명": "벌금 위헌확인",
                        "detcLnkUrl": "http://example.com/111",
                    },
                }
            },
        )
        from server import search_decisions
        result = await search_decisions(query="벌금")
        assert "벌금 위헌확인" in result
        assert "2019헌바1" in result

    async def test_search_returns_no_results_message(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=(
                "http://www.law.go.kr/DRF/lawSearch.do"
                "?OC=woongaro&target=detc&page=1&display=20&sort=lasc&search=1&type=JSON"
            ),
            json={"DetcSearch": {"totalCnt": "0", "page": "1"}},
        )
        from server import search_decisions
        result = await search_decisions()
        assert "검색 결과가 없습니다" in result
```

- [ ] **Step 2: Run — expect failure**

```bash
pytest tests/test_server.py::TestSearchDecisionsTool -v
```

Expected: FAIL — `search_decisions` not defined

- [ ] **Step 3: Add `search_decisions` to `server.py`**

Add after `parse_decision_response`:

```python
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
        sort: 정렬 (lasc=사건명오름차순, ldes=내림차순, dasc/ddes=선고일자, nasc/ndes=사건번호, efasc/efdes=종국일자)
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_server.py::TestSearchDecisionsTool -v
```

Expected: Both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "feat: add search_decisions MCP tool"
```

---

### Task 5: Implement `get_decision` tool

**Files:**
- Modify: `server.py` — add `get_decision` tool
- Modify: `tests/test_server.py` — add tool tests

- [ ] **Step 1: Write failing tests**

Append to `tests/test_server.py`:

```python
class TestGetDecisionTool:
    async def test_get_decision_returns_full_text(self, httpx_mock: HTTPXMock):
        # URL param order: OC, target, ID — then type=JSON appended by fetch()
        httpx_mock.add_response(
            url="http://www.law.go.kr/DRF/lawService.do?OC=woongaro&target=detcSc&ID=111&type=JSON",
            json={
                "DetcService": {
                    "사건번호": "2019헌바1",
                    "사건명": "벌금 위헌확인",
                    "종국일자": "20200101",
                    "결정요지": "이 사건 법률조항은 위헌이다.",
                    "결정문": "주문: 위헌 선언.",
                }
            },
        )
        from server import get_decision
        result = await get_decision(decision_id="111")
        assert "2019헌바1" in result
        assert "위헌이다" in result

    async def test_get_decision_not_found(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://www.law.go.kr/DRF/lawService.do?OC=woongaro&target=detcSc&ID=9999&type=JSON",
            json={"DetcService": {}},
        )
        from server import get_decision
        result = await get_decision(decision_id="9999")
        assert "찾을 수 없습니다" in result
```

- [ ] **Step 2: Run — expect failure**

```bash
pytest tests/test_server.py::TestGetDecisionTool -v
```

Expected: FAIL — `get_decision` not defined

- [ ] **Step 3: Add `get_decision` to `server.py`**

Add after `search_decisions`:

```python
@mcp.tool()
async def get_decision(decision_id: str) -> str:
    """
    헌재결정례 본문을 조회합니다.

    Args:
        decision_id: 헌재결정례일련번호 (search_decisions 결과의 일련번호 값)
    """
    params: dict[str, Any] = {
        "OC": OC,
        "target": "detcSc",
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
```

- [ ] **Step 4: Run all tests**

```bash
pytest tests/test_server.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "feat: add get_decision MCP tool"
```

---

## Chunk 4: Smoke Test + README

### Task 6: Verify server starts and tools are registered

- [ ] **Step 1: Verify import**

```bash
cd E:/mcp/Constitutional-Court-decision-mcp
python -c "import server; print('OK')"
```

Expected: `OK`

- [ ] **Step 2: Live API smoke test — search**

```bash
python -c "
import asyncio, server
result = asyncio.run(server.search_decisions(query='위헌', display=3))
print(result)
"
```

Expected: List of decisions OR `검색 결과가 없습니다`.

If you see `API 오류` or `응답 파싱 실패`:
- Check if `target=detcSc` needs a different value for the content endpoint
- Inspect the raw response: `python -c "import asyncio, server; import httpx; r = httpx.get('http://www.law.go.kr/DRF/lawSearch.do', params={'OC':'woongaro','target':'detc','type':'JSON','query':'위헌','display':'3'}); print(r.text[:500])"`

- [ ] **Step 3: Live API smoke test — get decision**

Use a `일련번호` from the search result above:

```bash
python -c "
import asyncio, server
result = asyncio.run(server.get_decision('REPLACE_WITH_REAL_ID'))
print(result[:500])
"
```

If response keys differ from `DetcService` / `결정요지` / `결정문`, update `parse_decision_response` and the corresponding tests to match actual field names, then re-run all tests.

- [ ] **Step 4: Commit any fixes from live testing**

```bash
git add server.py tests/test_server.py
git commit -m "fix: adjust field keys based on live API response"
```

---

### Task 7: Write README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create `README.md`**

```markdown
# 헌재결정례 MCP Server

법제처 헌재결정례 Open API를 Claude에서 사용할 수 있게 해주는 MCP 서버입니다.

## 설치

```bash
pip install -e .
```

## 환경 설정

```bash
cp .env.example .env
# .env 파일의 OC 값을 법제처 계정 이메일 ID로 변경
```

## 실행

```bash
mcp run server.py
```

## Claude Desktop 연동

`claude_desktop_config.json`에 추가 (경로는 실제 설치 경로로 변경):

```json
{
  "mcpServers": {
    "constitutional-court": {
      "command": "python",
      "args": ["/path/to/Constitutional-Court-decision-mcp/server.py"],
      "env": {
        "OC": "your-email-id"
      }
    }
  }
}
```

## 제공 도구

### `search_decisions` — 헌재결정례 목록 검색

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| query | string | 검색 키워드 |
| page | int | 페이지 번호 (기본값: 1) |
| display | int | 결과 수 (기본값: 20, 최대: 100) |
| sort | string | 정렬: lasc/ldes/dasc/ddes/nasc/ndes/efasc/efdes |
| date | int | 종국일자 YYYYMMDD |
| date_range | string | 기간 검색 (예: "20200101~20231231") |
| search | int | 1=사건명(기본), 2=본문 |
| case_number | int | 사건번호 |

### `get_decision` — 헌재결정례 본문 조회

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| decision_id | string | 헌재결정례일련번호 (search_decisions 결과의 일련번호) |

## 데이터 출처

[국가법령정보센터](http://www.law.go.kr) — 법제처 Open API
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup and usage instructions"
```

---

## Final Checklist

- [ ] All tests pass: `pytest tests/ -v`
- [ ] Server imports without error: `python -c "import server; print('OK')"`
- [ ] Live search returns results
- [ ] Live `get_decision` returns full text
- [ ] Field keys verified against actual API responses and tests updated if needed
- [ ] README complete
