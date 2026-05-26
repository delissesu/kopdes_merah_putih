# Membuat fungsi test test_payment_user_not_found().
# Membuat payload Input / Precondition berupa JSON berisikan userId yang tidak valid (misal: 99999) dan voucher kosong.
# Mengirim request POST ke /cart/pay.

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from main import app

from typing import Any

# simulasi klien untuk hit api
client = TestClient(app)

# constant invalid user id
VALID_USER_ID_EMPTY_CART: int = 1
INVALID_USER_ID: int = 9999
VALID_USER_ID_EXCEED_STOCK: int = 2


def test_payment_user_not_found() -> None:
    # arrange
    payload_pembayaran: dict[str, Any] = {"userId": INVALID_USER_ID, "voucherNames": []}

    expected_status: str = "Failed"
    expected_message: str = "User Tidak Ditemukan"

    # hit end point pembayaran
    response = client.post("/cart/pay", json=payload_pembayaran)

    # validate hasil and assert

    data = response.json()

    assert response.status_code == 200
    assert data["Status"] == expected_status
    assert data["Message"] == expected_message


# Membuat fungsi  test_payment_empty_cart()
# Membuat payload Input / Precondition berupa JSON valid userId dengan keranjang user kosong pada db
# Mengirim request POST ke /cart/pay.


def test_payment_empty_cart() -> None:
    payload_pembayaran: dict[str, Any] = {
        "userId": VALID_USER_ID_EMPTY_CART,
        "voucherNames": [],
    }

    expected_status: str = "Failed"
    expected_message: str = "Belum Ada Produk di Keranjang"

    # hit endpoint pembayaran
    response = client.post("/cart/pay", json=payload_pembayaran)

    # validate hasil dan assert
    data = response.json()

    assert response.status_code == 200
    assert data["Status"] == expected_status
    assert data["Message"] == expected_message


# Membuat fungsi uji test_payment_quantity_exceeds_stock
# Membuat payload JSON berupa { "userId": [ID_USER_DENGAN_KERANJANG_OVERLIMIT], "voucherNames": [] }.
# Mengirim request client.post('/cart/pay').


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

    # client.post(
    #     "/cart/add",
    #     json={
    #         "userId": VALID_USER_ID_EXCEED_STOCK,
    #         "productId": 3,
    #         "quantity": 999,
    #     },
    # )

    # # asumsikan user ID2 punya produk di keranjang yang jumlahnya melebihi status
    # payload_pembayaran: dict[str, Any] = {
    #     "userId": VALID_USER_ID_EXCEED_STOCK,
    #     "voucherNames": [],
    # }

    expected_status: str = "Failed"
    expected_message: str = "Jumlah Produk yang Akan Dibeli Melebihi Stok yang Ada"

    payload_pembayaran: dict[str, Any] = {
        "userId": USER_A,
        "voucherNames": [],
    }
    
    response = client.post("/cart/pay", json=payload_pembayaran)

    # hit payment endpoint
    # response = client.post("/cart/pay", json=payload_pembayaran)

    # validate data and assert
    data = response.json()

    assert response.status_code == 200
    assert data["Status"] == expected_status
    assert data["Message"] == expected_message


