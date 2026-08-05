
import pytest
from fastapi import HTTPException

from app.utils.plans import (
    _validate_positive
)


class TestPlans:
    def test_validate_positive_accepts_positive_number(self):
        assert _validate_positive(10, "Amount") is None

    def test_validate_positive_rejects_negative_number(self):
        with pytest.raises(HTTPException):
            _validate_positive(-5, "Amount")
