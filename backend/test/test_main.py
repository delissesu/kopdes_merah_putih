import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from main import app

from typing import Any

client = TestClient(app)

# constant invalid user id
VALID_USER_ID_EMPTY_CART: int = 1
INVALID_USER_ID: int = 9999
VALID_USER_ID_EXCEED_STOCK: int = 2

VALID_PRODUCT_ID_INSUFFICIENT: int = 6
VALID_USER_ID_INSUFFICIENT_BALANCE: int = 4

# TC-05
VALID_PRODUCT_ID_NO_VOUCHER: int = 5
VALID_USER_ID_SUCCESS: int = 5

# TC-06
VALID_USER_ID_VOUCHER: int = 6
PRODUK_ID_CEK_VOUCHER: int = 4

# TC-07 (Persentase)
VALID_USER_ID_TC07: int = 7
PRODUK_ID_TC07: int = 7  # Harga Rp100.000

# TC-08 (Kombinasi Voucher)
VALID_USER_ID_TC08: int = 8
PRODUK_ID_TC08: int = 8  # Harga Rp100.000

# TC-09 (Member Discount)
VALID_USER_ID_TC09: int = 9  # is_member = true
PRODUK_ID_TC09: int = 9  # Harga Rp100.000

# TC-11 (Fixed Voucher > Total)
VALID_USER_ID_TC11: int = 11
PRODUK_ID_TC11: int = 11  # Harga Rp5.000

# TC-12 (Cashback > Total)
VALID_USER_ID_TC12: int = 12
PRODUK_ID_TC12: int = 12  # Harga Rp5.000


def test_payment_user_not_found() -> None:
    payload_pembayaran: dict[str, Any] = {"userId": INVALID_USER_ID, "voucherNames": []}

    expected_status: str = "Failed"
    expected_message: str = "User Tidak Ditemukan"

    response = client.post("/cart/pay", json=payload_pembayaran)

    data = response.json()

    assert response.status_code == 200
    assert data["Status"] == expected_status
    assert data["Message"] == expected_message


def test_payment_empty_cart() -> None:
    payload_pembayaran: dict[str, Any] = {
        "userId": VALID_USER_ID_EMPTY_CART,
        "voucherNames": [],
    }

    expected_status: str = "Failed"
    expected_message: str = "Belum Ada Produk di Keranjang"

    response = client.post("/cart/pay", json=payload_pembayaran)

    data = response.json()

    assert response.status_code == 200
    assert data["Status"] == expected_status
    assert data["Message"] == expected_message


def test_payment_quantity_exceeds_stock() -> None:
    response_products = client.get("/products")
    products = response_products.json()

    # ambil produk pertama yang stoknya lebih dari 0
    target_product = next(p for p in products if p["available_amount"] > 0)
    stok_tersedia: int = target_product["available_amount"]
    produk_id: int = target_product["id"]

    USER_A: int = 2
    USER_B: int = 3

    # a dan b sama-sama deliver semua sisa stok ke keranjang
    payload_keranjang_a: dict[str, Any] = {
        "userId": USER_A,
        "productId": produk_id,
        "quantity": stok_tersedia,
    }

    payload_keranjang_b: dict[str, Any] = {
        "userId": USER_B,
        "productId": produk_id,
        "quantity": stok_tersedia,
    }

    client.post("/cart/add/product", json=payload_keranjang_a)
    client.post("/cart/add/product", json=payload_keranjang_b)

    # asumsikan user b bayar lebih dahulu
    client.post(
        "/cart/pay",
        json={
            "userId": USER_B,
            "voucherNames": [],
        },
    )

    expected_status: str = "Failed"
    expected_message: str = "Jumlah Produk yang Akan Dibeli Melebihi Stok yang Ada"

    payload_pembayaran: dict[str, Any] = {
        "userId": USER_A,
        "voucherNames": [],
    }

    response = client.post("/cart/pay", json=payload_pembayaran)
    data = response.json()

    assert response.status_code == 200
    assert data["Status"] == expected_status
    assert data["Message"] == expected_message


def test_payment_insufficient_balance() -> None:
    response_cart = client.get(f"/cart/{VALID_USER_ID_INSUFFICIENT_BALANCE}")
    cart_items = response_cart.json()
    print(cart_items)

    if len(cart_items) == 0:
        payload_keranjang: dict[str, Any] = {
            "userId": VALID_USER_ID_INSUFFICIENT_BALANCE,
            "productId": VALID_PRODUCT_ID_INSUFFICIENT,
            "quantity": 1,
        }
        client.post("/cart/add/product", json=payload_keranjang)

    payload_pembayaran: dict[str, Any] = {
        "userId": VALID_USER_ID_INSUFFICIENT_BALANCE,
        "voucherNames": [],
    }

    expected_status: str = "Failed"
    expected_message: str = "Saldo Anda Tidak Mencukupi"

    response = client.post("/cart/pay", json=payload_pembayaran)

    data = response.json()

    assert response.status_code == 200
    assert data["Status"] == expected_status
    assert data["Message"] == expected_message


def test_payment_success_no_voucher() -> None:
    payload_keranjang: dict[str, Any] = {
        "userId": VALID_USER_ID_SUCCESS,
        "productId": VALID_PRODUCT_ID_NO_VOUCHER,
        "quantity": 1,
    }
    print(payload_keranjang)

    response_add = client.post("/cart/add/product", json=payload_keranjang)

    assert (
        response_add.json()["Status"] == "Success"
    ), f"Produk gagal masuk keranjang: {response_add.json()}"

    payload_pembayaran: dict[str, Any] = {
        "userId": VALID_USER_ID_SUCCESS,
        "voucherNames": [],
    }

    expected_status: str = "Success"
    expected_message: str = "Keranjang Anda Berhasil Dibayar"

    response = client.post("/cart/pay", json=payload_pembayaran)
    print(response)

    data = response.json()

    assert response.status_code == 200
    assert (
        data["Status"] == expected_status
    ), f"Gagal bayar! Pesan dari server: {data.get('Message')}"
    assert data["Message"] == expected_message

    assert "Detail" in data
    assert "total_paid" in data["Detail"]


def test_payment_fixed_voucher() -> None:
    response_cart = client.get(f"/cart/{VALID_USER_ID_VOUCHER}")
    cart_items = response_cart.json()

    if len(cart_items) == 0:
        payload_keranjang: dict[str, Any] = {
            "userId": VALID_USER_ID_VOUCHER,
            "productId": PRODUK_ID_CEK_VOUCHER,
            "quantity": 1,
        }
        response_add = client.post("/cart/add/product", json=payload_keranjang)
        assert (
            response_add.json()["Status"] == "Success"
        ), f"Gagal masuk keranjang : {response_add.json()}"

    payload_pembayaran: dict[str, Any] = {
        "userId": VALID_USER_ID_VOUCHER,
        "voucherNames": ["DISKON_FLAT"],
    }

    expected_status: str = "Success"
    expected_message: str = "Keranjang Anda Berhasil Dibayar"

    response = client.post("/cart/pay", json=payload_pembayaran)
    data = response.json()

    assert response.status_code == 200
    assert data["Status"] == expected_status, f"Gagal bayar: {data.get('Message')}"
    assert data["Message"] == expected_message

    assert data["Detail"]["subtotal"] == 100000
    assert data["Detail"]["voucher_discount"] == 10000
    assert data["Detail"]["total_paid"] == 90000


from unittest.mock import patch


def test_payment_percentage_voucher() -> None:
    response_cart = client.get(f"/cart/{VALID_USER_ID_TC07}")

    if len(response_cart.json()) == 0:
        client.post(
            "/cart/add/product",
            json={
                "userId": VALID_USER_ID_TC07,
                "productId": PRODUK_ID_TC07,
                "quantity": 1,
            },
        )

    payload_pembayaran: dict[str, Any] = {
        "userId": VALID_USER_ID_TC07,
        "voucherNames": ["DISKON_10_PERSEN"],
    }

    response = client.post("/cart/pay", json=payload_pembayaran)
    data = response.json()

    assert response.status_code == 200
    assert data["Status"] == "Success", data
    assert data["Detail"]["subtotal"] == 100000
    assert data["Detail"]["total_paid"] == 90000


def test_payment_combination_voucher() -> None:
    response_cart = client.get(f"/cart/{VALID_USER_ID_TC08}")

    if len(response_cart.json()) == 0:
        client.post(
            "/cart/add/product",
            json={
                "userId": VALID_USER_ID_TC08,
                "productId": PRODUK_ID_TC08,
                "quantity": 1,
            },
        )

    payload_pembayaran: dict[str, Any] = {
        "userId": VALID_USER_ID_TC08,
        "voucherNames": ["DISKON_10K_FLAT", "DISKON_10_PERSEN"],
    }

    response = client.post("/cart/pay", json=payload_pembayaran)
    data = response.json()

    assert response.status_code == 200
    assert data["Status"] == "Success"
    assert data["Detail"]["total_paid"] == 81000


def test_payment_member_discount() -> None:
    response_cart = client.get(f"/cart/{VALID_USER_ID_TC09}")

    if len(response_cart.json()) == 0:
        client.post(
            "/cart/add/product",
            json={
                "userId": VALID_USER_ID_TC09,
                "productId": PRODUK_ID_TC09,
                "quantity": 1,
            },
        )

    payload_pembayaran: dict[str, Any] = {
        "userId": VALID_USER_ID_TC09,
        "voucherNames": [],
    }

    response = client.post("/cart/pay", json=payload_pembayaran)
    data = response.json()

    assert response.status_code == 200
    assert data["Status"] == "Success"
    assert data["Detail"]["subtotal"] == 100000
    assert data["Detail"]["member_discount"] == 5000
    assert data["Detail"]["total_paid"] == 95000


from main import get_db


def test_payment_system_error() -> None:
    class FailingCursor:
        def __enter__(self):
            raise Exception("Mocked payment failure")

        def __exit__(self, exc_type, exc, tb):
            return False

    class FailingConn:
        def cursor(self):
            return FailingCursor()

    def override_get_db_error():
        yield FailingConn()

    app.dependency_overrides[get_db] = override_get_db_error

    payload_pembayaran: dict[str, Any] = {
        "userId": 99999,
        "voucherNames": [],
    }

    try:
        response = client.post("/cart/pay", json=payload_pembayaran)
        assert response.status_code == 500
        assert response.json().get("detail") == "Gagal membayar: Mocked payment failure"

    finally:
        app.dependency_overrides.clear()


def test_payment_fixed_voucher_exceeds_total() -> None:
    response_cart = client.get(f"/cart/{VALID_USER_ID_TC11}")

    if len(response_cart.json()) == 0:
        client.post(
            "/cart/add/product",
            json={
                "userId": VALID_USER_ID_TC11,
                "productId": PRODUK_ID_TC11,
                "quantity": 1,
            },
        )

    payload_pembayaran: dict[str, Any] = {
        "userId": VALID_USER_ID_TC11,
        "voucherNames": ["DISKON_10K_FLAT"],
    }

    response = client.post("/cart/pay", json=payload_pembayaran)
    data = response.json()

    assert response.status_code == 200, data
    assert data["Status"] == "Failed", data


def test_payment_cashback_exceeds_total() -> None:
    response_cart = client.get(f"/cart/{VALID_USER_ID_TC12}")

    if len(response_cart.json()) == 0:
        client.post(
            "/cart/add/product",
            json={
                "userId": VALID_USER_ID_TC12,
                "productId": PRODUK_ID_TC12,
                "quantity": 1,
            },
        )

    payload_pembayaran: dict[str, Any] = {
        "userId": VALID_USER_ID_TC12,
        "voucherNames": ["CASHBACK_10K"],
    }

    response = client.post("/cart/pay", json=payload_pembayaran)
    data = response.json()

    assert response.status_code == 200, data
    assert data["Status"] == "Failed", data
