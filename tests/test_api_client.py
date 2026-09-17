"""Unit tests for the two pieces of real logic in api_client.py."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from frontend import api_client


def _mock_response(json_data=None, text="", ok=True, status_code=200, json_raises=False):
    response = MagicMock()
    response.ok = ok
    response.status_code = status_code
    response.text = text
    if json_raises:
        response.json.side_effect = ValueError("not JSON")
    else:
        response.json.return_value = json_data
    return response


class TestRequestErrorClassification:
    def test_connection_failure_raises_backend_unreachable(self):
        with patch("frontend.api_client.requests.request", side_effect=requests.ConnectionError("refused")):
            with pytest.raises(api_client.BackendUnreachableError):
                api_client.list_datasets("s1")

    def test_timeout_raises_backend_unreachable(self):
        with patch("frontend.api_client.requests.request", side_effect=requests.Timeout("too slow")):
            with pytest.raises(api_client.BackendUnreachableError):
                api_client.list_datasets("s1")

    def test_non_ok_response_raises_api_error_with_detail(self):
        response = _mock_response(json_data={"detail": "Dataset not found"}, ok=False, status_code=404)
        with patch("frontend.api_client.requests.request", return_value=response):
            with pytest.raises(api_client.ApiError, match="404.*Dataset not found"):
                api_client.list_datasets("s1")

    def test_non_ok_response_with_non_json_body_falls_back_to_text(self):
        response = _mock_response(text="Internal Server Error", ok=False, status_code=500, json_raises=True)
        with patch("frontend.api_client.requests.request", return_value=response):
            with pytest.raises(api_client.ApiError, match="500.*Internal Server Error"):
                api_client.list_datasets("s1")

    def test_ok_response_returns_parsed_json(self):
        response = _mock_response(json_data=[{"id": 1}], ok=True)
        with patch("frontend.api_client.requests.request", return_value=response):
            result = api_client.list_datasets("s1")
        assert result == [{"id": 1}]

    def test_backend_unreachable_error_is_also_an_api_error(self):
        assert issubclass(api_client.BackendUnreachableError, api_client.ApiError)


class TestGetFullDataset:
    def _page_response(self, all_rows, columns, offset, limit):
        page_rows = all_rows[offset:offset + limit]
        return _mock_response(
            json_data={"columns": columns, "rows": page_rows, "n_rows": len(all_rows)},
            ok=True,
        )

    def test_single_page_when_under_page_size(self, monkeypatch):
        monkeypatch.setattr(api_client, "PAGE_SIZE", 500)
        columns = ["Id", "Val"]
        all_rows = [{"Id": i, "Val": f"v{i}"} for i in range(3)]

        def side_effect(method, url, **kwargs):
            return self._page_response(all_rows, columns, kwargs["params"]["offset"], kwargs["params"]["limit"])

        with patch("frontend.api_client.requests.request", side_effect=side_effect) as mock_request:
            df = api_client.get_full_dataset("s1", 1)

        assert mock_request.call_count == 1
        assert list(df.columns) == columns
        assert df["Id"].tolist() == [0, 1, 2]

    def test_pages_through_multiple_requests_and_reassembles_in_order(self, monkeypatch):
        monkeypatch.setattr(api_client, "PAGE_SIZE", 2)
        columns = ["Id", "Val"]
        all_rows = [{"Id": i, "Val": f"v{i}"} for i in range(5)]  # page size 2 -> 3 requests

        def side_effect(method, url, **kwargs):
            return self._page_response(all_rows, columns, kwargs["params"]["offset"], kwargs["params"]["limit"])

        with patch("frontend.api_client.requests.request", side_effect=side_effect) as mock_request:
            df = api_client.get_full_dataset("s1", 1)

        assert mock_request.call_count == 3
        assert df["Id"].tolist() == [0, 1, 2, 3, 4]

    def test_stops_safely_if_a_page_returns_no_rows_before_n_rows_reached(self, monkeypatch):
        """Defensive stopping condition — must never infinite-loop on a backend inconsistency."""
        monkeypatch.setattr(api_client, "PAGE_SIZE", 2)
        first_page = {"columns": ["Id"], "rows": [{"Id": 0}, {"Id": 1}], "n_rows": 10}
        empty_page = {"columns": ["Id"], "rows": [], "n_rows": 10}
        responses = [_mock_response(json_data=first_page), _mock_response(json_data=empty_page)]

        with patch("frontend.api_client.requests.request", side_effect=responses) as mock_request:
            df = api_client.get_full_dataset("s1", 1)

        assert mock_request.call_count == 2
        assert len(df) == 2
