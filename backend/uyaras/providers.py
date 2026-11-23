"""Provider boundary: mock payments and manual shipping until providers are selected."""

import os
from dataclasses import dataclass
from typing import Protocol
from .security import require


class PaymentProvider(Protocol):
    def create(self, order_id: str, amount: int) -> dict: ...


@dataclass
class MockPayments:
    def create(self, order_id: str, amount: int) -> dict:
        require(
            os.getenv("APP_ENV", "development") != "production",
            "Mock payments are disabled.",
            503,
        )
        return {
            "provider": "mock",
            "order_id": order_id,
            "amount": amount,
            "currency": "INR",
            "status": "pending",
        }


def payment_provider() -> PaymentProvider:
    name = os.getenv("PAYMENT_PROVIDER", "mock")
    require(name == "mock", f"Payment adapter {name} is not activated.", 503)
    return MockPayments()


def shipping_provider():
    name = os.getenv("SHIPPING_PROVIDER", "manual")
    require(name == "manual", f"Shipping adapter {name} is not activated.", 503)
    return name
