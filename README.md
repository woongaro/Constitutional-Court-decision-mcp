# 헌재결정례 MCP Server

법제처 헌재결정례 Open API를 Claude에서 사용할 수 있게 해주는 MCP 서버입니다.

<img width="1024" height="559" alt="image" src="https://github.com/user-attachments/assets/fab40b9e-6525-4e32-bddc-e8eb6ec295e6" />



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
