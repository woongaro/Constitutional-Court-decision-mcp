# 헌재결정례 MCP Server

법제처 헌재결정례 Open API를 Claude에서 사용할 수 있게 해주는 MCP 서버입니다.

<img width="1024" height="559" alt="image" src="https://github.com/user-attachments/assets/fab40b9e-6525-4e32-bddc-e8eb6ec295e6" />


## 사용 전 주의사항

 ** 이 MCP 서버를 사용하려면 반드시 법제처 Open API 사용자 등록이 필요합니다 .**

### API 사용자 등록 방법

1. [국가법령정보 Open API](https://open.Law.go.kr/LSO/main.do) 접속
2. 회원가입 후 로그인
3. ** 오픈API ** → ** 오픈API 신청 ** 메뉴에서 사용 신청
4. 승인 후 발급받은 ** 이메일 계정 ID ** (OC 값)를 환경 변수에 설정

> 미등록 상태로 API를 호출하면 인증 오류 또는 데이터가 반환되지 않습니다.

### 사용자 경고사항

- ** 무단 크롤링 금지 **: 이 서버는 법제처가 공식 제공하는 Open API만 사용합니다. API 외 방식으로
데이터를 수집하는 것은 이용약관 위반입니다.
- ** API 호출 한도 **: 법제처 Open API는 일일 호출 횟수 제한이 있을 수 있습니다. 과도한 반복 호출을
삼가주세요.
- ** 데이터 재배포 주의 **: 조회된 결정문 원문은 법제처의 저작권 정책에 따르며, 상업적 재배포 시 별도
확인이 필요합니다.
- ** 정확성 책임 **: 이 도구는 정보 조회 보조 목적으로 제공됩니다. 법률 판단이나 소송 등 중요한
의사결정에는 반드시 원문을 직접 확인하고 전문가 조언을 받으시기 바랍니다.

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
