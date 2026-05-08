import unittest

from app.api.responses import ApiResponse
from app.core.errors import AppError
from app.core.errors import ValidationAppError


class ApiResponseTests(unittest.TestCase):
    def test_success_response_has_stable_shape(self) -> None:
        response = ApiResponse.ok({"id": "project-1"}, request_id="request-1")

        self.assertEqual(
            response.to_dict()["data"],
            {"id": "project-1"},
        )
        self.assertIsNone(response.to_dict()["error"])
        self.assertEqual(response.to_dict()["meta"]["request_id"], "request-1")

    def test_failed_response_uses_app_error_code(self) -> None:
        response = ApiResponse.failed(
            ValidationAppError("invalid payload", {"field": "name"}),
            request_id="request-1",
        )

        body = response.to_dict()

        self.assertIsNone(body["data"])
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(body["error"]["details"], {"field": "name"})
        self.assertEqual(body["meta"]["request_id"], "request-1")

    def test_failed_response_accepts_error_without_details(self) -> None:
        response = ApiResponse.failed(
            AppError(
                code="INTERNAL_ERROR",
                message="unexpected error",
                http_status=500,
            ),
            request_id="request-1",
        )

        body = response.to_dict()

        self.assertEqual(body["error"]["details"], {})


if __name__ == "__main__":
    unittest.main()
