import pytest
import httpx
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

    async def test_fetch_returns_timeout_error(self, httpx_mock: HTTPXMock):
        httpx_mock.add_exception(
            httpx.ReadTimeout("read timeout"),
            url="http://www.law.go.kr/DRF/lawSearch.do?OC=woongaro&target=detc&type=JSON",
        )
        result = await fetch(
            "http://www.law.go.kr/DRF/lawSearch.do",
            {"OC": "woongaro", "target": "detc"},
        )
        assert result == "요청 시간 초과"

    async def test_fetch_returns_timeout_error_on_connect_timeout(self, httpx_mock: HTTPXMock):
        httpx_mock.add_exception(
            httpx.ConnectTimeout("connect timeout"),
            url="http://www.law.go.kr/DRF/lawSearch.do?OC=woongaro&target=detc&type=JSON",
        )
        result = await fetch(
            "http://www.law.go.kr/DRF/lawSearch.do",
            {"OC": "woongaro", "target": "detc"},
        )
        assert result == "요청 시간 초과"

    async def test_fetch_returns_parse_fail_on_malformed_xml(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://www.law.go.kr/DRF/lawSearch.do?OC=woongaro&target=detc&type=JSON",
            text="not json",
        )
        httpx_mock.add_response(
            url="http://www.law.go.kr/DRF/lawSearch.do?OC=woongaro&target=detc&type=XML",
            content=b"<<invalid xml>>",
        )
        result = await fetch(
            "http://www.law.go.kr/DRF/lawSearch.do",
            {"OC": "woongaro", "target": "detc"},
        )
        assert result == "응답 파싱 실패"


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

    def test_returns_empty_message_when_detc_key_missing(self):
        raw = {"DetcSearch": {"totalCnt": "5", "page": "1"}}  # no "detc" key
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
