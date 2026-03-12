# Constitutional Court Decision MCP Server — Design Spec

**Date:** 2026-03-12
**Status:** Approved

---

## Overview

Python MCP server that wraps the Korean Constitutional Court Decision (헌재결정례) Open API from law.go.kr. Exposes two MCP tools so that Claude can search decisions and retrieve full decision text.

## API Source

- **Provider:** 법제처 (Ministry of Government Legislation)
- **List endpoint:** `http://www.law.go.kr/DRF/lawSearch.do?OC=woongaro&target=detc&type=JSON`
- **Content endpoint:** `http://www.law.go.kr/DRF/lawService.do?OC=woongaro&target=detcSc&type=JSON`
  - Note: `detcSc` follows the law.go.kr naming convention (list=`detc`, content=`detcSc`). Verify against live API on first run.
- **Auth:** `OC` parameter — user email ID (`woongaro`)

## Project Structure

```
Constitutional-Court-decision-mcp/
├── server.py            # MCP server + HTTP client + JSON/XML parser
├── pyproject.toml       # Dependencies: mcp, httpx, xmltodict, python-dotenv
├── .env.example         # OC=woongaro
└── Docs/
    └── OPEN API 활용가이드_헌법재판소결정.txt
```

## MCP Tools

### `search_decisions`
Search the Constitutional Court decision list.

**Implementation note:** `type=JSON` is always injected by the implementation and is not exposed to the MCP caller. On JSON parse failure, the call is retried with `type=XML`.

**MCP Parameters → API parameter mapping:**
| MCP Parameter | API Parameter | Type | Required | Description |
|---------------|--------------|------|----------|-------------|
| query | query | string | No | Search keyword (case name or body) |
| page | page | int | No | Page number (default: 1) |
| display | display | int | No | Results per page (default: 20, max: 100) |
| sort | sort | string | No | `lasc`(default), `ldes`, `dasc`, `ddes`, `nasc`, `ndes`, `efasc`, `efdes` |
| date | date | int | No | 종국일자 YYYYMMDD format as integer |
| date_range | edYd | string | No | 종국일자 기간 검색 |
| search | search | int | No | 1=사건명(default), 2=본문검색 |
| case_number | nb | int | No | 사건번호로 직접 검색 |

**Returns fields:** `totalCnt`, `page`, `decisions[]` — each with: `일련번호`, `사건번호`, `사건명`, `종국일자`, `상세링크`

### `get_decision`
Retrieve the full text of a single decision.

**Request URL:** `http://www.law.go.kr/DRF/lawService.do?OC={OC}&target=detcSc&ID={decision_id}&type=JSON`

**Implementation note:** `type=JSON` is always used first; retried with `type=XML` on failure.

**MCP Parameters → API parameter mapping:**
| MCP Parameter | API Parameter | Type | Required | Description |
|---------------|--------------|------|----------|-------------|
| decision_id | ID | string | Yes | 헌재결정례일련번호 (from search results `일련번호` field) |

**Returns fields:** `사건번호`, `사건명`, `종국일자`, `결정요지`, `결정문` (raw text of full decision body)

## Data Flow

```
Claude calls MCP tool
  → Build request URL with params (type=JSON)
  → httpx GET to law.go.kr (connect_timeout=5s, read_timeout=30s)
  → Parse JSON response
  → If JSON parse fails → retry same URL with type=XML → parse via xmltodict
  → Normalize response to dict
  → Return structured text to Claude
  → On HTTP/network error → return descriptive error message in Korean
```

## Timeouts

- Connect timeout: 5 seconds
- Read timeout: 30 seconds (longer for `get_decision` which may return large full-text responses)

## Error Handling

- HTTP errors (4xx/5xx): `"API 오류: HTTP {status_code}"`
- Network timeout: `"요청 시간 초과"`
- Empty results: `"검색 결과가 없습니다"`
- Both JSON and XML parse fail: `"응답 파싱 실패"`

## Running the Server

```bash
# Install dependencies
pip install -e .

# Run MCP server
mcp run server.py

# Or add to Claude Desktop config:
# command: python, args: ["/path/to/server.py"]
```

## Dependencies

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

[project.scripts]
constitutional-court-mcp = "server:main"
```

## Environment Variables

```env
OC=woongaro
```

Loaded via `python-dotenv` at startup. Falls back to `woongaro` if not set.

## Out of Scope

- Caching / rate limiting
- `gana` parameter (사전식 검색) — low value for AI assistant use case
- `popYn` parameter — browser popup flag, irrelevant for MCP
- Other law.go.kr API targets (판례, 법령 등)
- Authentication beyond OC parameter
