from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel
from typing import List, Generator, Optional

app = FastAPI(title="Product CRUD API dengan FastAPI & Psycopg 3")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Konfigurasi Koneksi Database
DB_PARAMS = "dbname=kopdes user=postgres password=Delion21. host=localhost port=5432"
MEMBER_DISCOUNT = 0.05


# 2. Dependency untuk Yield Koneksi Database
def get_db() -> Generator[psycopg.Connection, None, None]:
    """
    Membuka koneksi database per request, dan otomatis menutupnya
    setelah request selesai diproses.
    """
    with psycopg.connect(DB_PARAMS, row_factory=dict_row) as conn:  # type: ignore
        yield conn
        # Context manager 'with' otomatis melakukan conn.close() di sini


# 3. Pydantic Schemas (Untuk Validasi Request & Response Body)
class UserLogin(BaseModel):
    username: str
    password: str


class ProductCreate(BaseModel):
    name: str
    available_amount: int
    price: float


class ProductUpdateStock(BaseModel):
    available_amount: int


class ProductResponse(BaseModel):
    id: int
    name: str
    available_amount: int
    price: float
    description: str


class CartAddProduct(BaseModel):
    userId: int
    productId: int
    quantity: int


class UseVoucher(BaseModel):
    userId: int
    voucherName: str


class Payment(BaseModel):
    userId: int
    voucherNames: list[str]


# ==========================================
# ENDPOINTS / URL CRUD
# ==========================================


@app.get("/")
def read_root():
    return {"message": "Welcome to E-Commerce API, Bang!"}


@app.post("/login")
def login(datas: UserLogin, conn: psycopg.Connection = Depends(get_db)):
    query = "SELECT id, name, username, is_member, balance FROM users WHERE username=%s AND password=%s;"
    try:
        with conn.cursor() as cur:
            cur.execute(query, (datas.username, datas.password))
            user = cur.fetchone()
            if user is None:
                raise HTTPException(
                    status_code=401, detail="Username atau password salah"
                )
            return {"Status": "Success", "Message": "Login berhasil", "User": user}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Terjadi kesalahan: {e}")


@app.get("/users/{id}")
def get_user(id, conn: psycopg.Connection = Depends(get_db)):
    query = f'SELECT * FROM users where "id"={id};'
    try:
        with conn.cursor() as cur:
            cur.execute(query)  # type: ignore
            return cur.fetchall()[0]
    except Exception as e:
        return HTTPException(status_code=500, detail=f"User Not Found: {e}")


# --- R - READ: Ambil Semua Produk ---
@app.get("/products", response_model=List[ProductResponse])
def get_all_products(conn: psycopg.Connection = Depends(get_db)):
    query = "SELECT * FROM Products ORDER BY name ASC;"
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengambil data: {str(e)}")


@app.get("/products/{id}", response_model=ProductResponse)
def get_product(id: int, conn: psycopg.Connection = Depends(get_db)):
    query = "SELECT * FROM Products WHERE id=%s;"
    try:
        with conn.cursor() as cur:
            cur.execute(query, (id,))
            product = cur.fetchone()
            if product is None:
                raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
            return product
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengambil data: {str(e)}")


@app.post("/cart/add/product")
def add_product_to_cart(
    datas: CartAddProduct, conn: psycopg.Connection = Depends(get_db)
):
    query = """
        INSERT INTO carts (user_id, product_id, quantity)
        VALUES (%s, %s, %s);
    """
    select_query = """
        SELECT id, quantity FROM carts
        where user_id=%s
            AND product_id=%s
            AND is_paid=false;
    """
    select_product_query = """
        SELECT available_amount FROM products
        WHERE id = %s;
    """

    update_query = """
        UPDATE carts
        SET quantity = quantity+%s
        WHERE id = %s; 
    """

    try:
        with conn.cursor() as cur:
            cur.execute(select_query, (datas.userId, datas.productId))
            res = cur.fetchone()
            cur.execute(select_product_query, (datas.productId,))
            product = cur.fetchone()
            if res == None:
                if product["available_amount"] < datas.quantity:  # type: ignore
                    return {
                        "Status": "Failed",
                        "Message": "Gagal Menambahkan Produk, Jumlah Produk yang Tersedia Tidak Mencukupi",
                    }
                cur.execute(query, (datas.userId, datas.productId, datas.quantity))
                # Wajib commit untuk menyimpan data baru
            else:
                if product["available_amount"] < res["quantity"] + datas.quantity:  # type: ignore
                    return {
                        "Status": "Failed",
                        "Message": "Gagal Menambahkan Produk, Jumlah Produk yang Tersedia Tidak Mencukupi",
                    }
                cur.execute(update_query, (datas.quantity, res["id"]))  # type: ignore
            conn.commit()
            return {
                "Status": "Success",
                "Message": "Berhasil Menambahkan Produk di Keranjang",
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menambah produk: {str(e)}")


@app.get("/cart/{userId}")
def get_cart(userId: int, conn: psycopg.Connection = Depends(get_db)):
    query = """
        SELECT p.id, p.name, p.description, p.price, c.quantity FROM carts as c
        INNER JOIN products as p ON c.product_id = p.id
        WHERE user_id=%s
        AND is_paid=false;
    """
    try:
        with conn.cursor() as cur:
            cur.execute(query, (userId,))
            cart_products = cur.fetchall()
            return cart_products
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Gagal mengambil keranjang: {str(e)}"
        )


# ---- GET /vouchers - List semua voucher yang tersedia ----
@app.get("/vouchers")
def get_all_vouchers(conn: psycopg.Connection = Depends(get_db)):
    query = "SELECT id, name, effect, amount FROM vouchers ORDER BY name ASC;"
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Gagal mengambil daftar voucher: {str(e)}"
        )


# ---- GET /vouchers/check - Validasi voucher untuk user tertentu ----
@app.get("/vouchers/check")
def check_voucher(
    userId: int = Query(..., description="ID pengguna"),
    voucherName: str = Query(..., description="Nama/kode voucher"),
    conn: psycopg.Connection = Depends(get_db),
):
    select_voucher_query = (
        "SELECT id, name, effect, amount FROM vouchers WHERE name = %s;"
    )
    check_used_query = """
        SELECT 1 FROM usedVouchers
        WHERE user_id = %s AND voucher_id = %s;
    """
    try:
        with conn.cursor() as cur:
            cur.execute(select_voucher_query, (voucherName,))
            voucher = cur.fetchone()
            if voucher is None:
                return {
                    "Status": "Failed",
                    "Message": "Voucher tidak ditemukan",
                    "Valid": False,
                }
            cur.execute(check_used_query, (userId, voucher["id"]))  # type: ignore
            already_used = cur.fetchone()
            if already_used:
                return {
                    "Status": "Failed",
                    "Message": "Voucher sudah pernah digunakan",
                    "Valid": False,
                }
            return {
                "Status": "Success",
                "Message": "Voucher valid",
                "Valid": True,
                "Voucher": {
                    "id": voucher["id"],  # type: ignore
                    "name": voucher["name"],  # type: ignore
                    "effect": voucher["effect"],  # type: ignore
                    "amount": voucher["amount"],  # type: ignore
                },
            }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Gagal memeriksa voucher: {str(e)}"
        )


@app.post("/use/voucher")
def use_voucher(datas: UseVoucher, conn: psycopg.Connection = Depends(get_db)):
    query = """
        SELECT v.id FROM usedVouchers as uv
        INNER JOIN vouchers as v 
        ON uv.voucher_id = v.id
        WHERE user_id=%s
        AND v.id=%s;
    """
    select_voucher_query = """
        SELECT * FROM vouchers
        WHERE name = %s;
    """

    try:
        with conn.cursor() as cur:
            cur.execute(select_voucher_query, (datas.voucherName,))
            vouchers = res = cur.fetchall()
            if len(vouchers) == 0:
                return {"Status": "Failed", "Message": "Voucher Tidak Ada"}
            voucher = vouchers[0]
            cur.execute(query, (datas.userId, voucher["id"]))  # type: ignore
            res = cur.fetchall()
            if len(res) != 0:
                return {"Status": "Failed", "Message": "Voucher Telah Digunakan"}
            return {"Status": "Success", "Message": "Voucher Berhasil Digunakan"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Gagal saat menggunakan voucher: {str(e)}"
        )


from enum import Enum


class VoucherType(Enum):
    FIXED_MINUS = "FIXED_MINUS"
    PERCENTAGE_DISCOUNT = "PERCENTAGE_DISCOUNT"
    FIXED_CASHBACK = "FIXED_CASHBACK"


def handle_voucher(
    total_price: float, voucher_type: str, amount: float
) -> tuple[float, float]:
    cashback = 0
    match voucher_type:
        case VoucherType.FIXED_MINUS.value:
            total_price -= amount
        case VoucherType.PERCENTAGE_DISCOUNT.value:
            total_price *= 1 - (amount / 100)
        case VoucherType.FIXED_CASHBACK.value:
            cashback = amount
        case _:
            raise ValueError("Unknown Value in Voucher Type")
    return (total_price, cashback)


# Preview kalkulasi harga sebelum bayar
@app.get("/cart/summary/{userId}")
def get_cart_summary(
    userId: int,
    voucherNames: Optional[List[str]] = Query(default=[]),
    conn: psycopg.Connection = Depends(get_db),
):
    user_query = "SELECT id, is_member FROM users WHERE id=%s;"
    cart_query = """
        SELECT p.price, c.quantity
        FROM carts AS c
        INNER JOIN products AS p ON c.product_id = p.id
        WHERE c.user_id = %s AND c.is_paid = false;
    """
    vouchers_query = """
        SELECT v.id, v.name, v.effect, v.amount 
        FROM vouchers AS v
        WHERE v.name = ANY(%s)
          AND NOT EXISTS (
              SELECT 1 FROM usedVouchers AS uv 
              WHERE uv.voucher_id = v.id AND uv.user_id = %s
          )
        ORDER BY v.effect ASC;
    """
    try:
        with conn.cursor() as cur:
            cur.execute(user_query, (userId,))
            user = cur.fetchone()
            if user is None:
                raise HTTPException(status_code=404, detail="User tidak ditemukan")

            cur.execute(cart_query, (userId,))
            cart_items = cur.fetchall()
            if len(cart_items) == 0:
                raise HTTPException(status_code=400, detail="Keranjang kosong")

            subtotal = sum(item["price"] * item["quantity"] for item in cart_items)  # type: ignore
            total = subtotal
            voucher_discount = 0.0
            cashback = 0.0

            names_list = list(voucherNames) if voucherNames else []
            if names_list:
                cur.execute(vouchers_query, (names_list, userId))
                vouchers = cur.fetchall()
                for v in vouchers:
                    before = total
                    total, cb = handle_voucher(total_price=total, voucher_type=v["effect"], amount=v["amount"])  # type: ignore
                    if v["effect"] != VoucherType.FIXED_CASHBACK.value:  # type: ignore
                        voucher_discount += before - total
                    cashback += cb

            member_discount = 0.0
            if user["is_member"]:  # type: ignore
                member_discount = total * MEMBER_DISCOUNT
                total -= member_discount

            total = max(0, total)

            return {
                "subtotal": round(subtotal, 2),
                "voucher_discount": round(voucher_discount, 2),
                "member_discount": round(member_discount, 2),
                "cashback": round(cashback, 2),
                "total_to_pay": round(total, 2),
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Gagal menghitung ringkasan: {str(e)}"
        )


@app.post("/cart/pay")
def payment_handle(datas: Payment, conn: psycopg.Connection = Depends(get_db)):
    user_query = """
        SELECT id, is_member, balance FROM users
        WHERE id=%s;
    """
    cart_query = """
        SELECT c.id, c.product_id, p.price, c.quantity, 
        CASE 
            WHEN c.quantity > p.available_amount THEN 1 
            ELSE 0 
        END AS is_exceed
        FROM carts as c
        INNER JOIN products as p ON c.product_id = p.id
        WHERE user_id=%s
        AND is_paid=false;
    """
    vouchers_query = """
        SELECT v.id, v.effect, v.amount 
        FROM vouchers AS v
        WHERE v.name = ANY(%s)
          AND NOT EXISTS (
              SELECT 1 
              FROM usedVouchers AS uv 
              WHERE uv.voucher_id = v.id 
                AND uv.user_id = %s
          )
        ORDER BY v.effect ASC;
    """

    user_change_balance_query = """
        UPDATE users
        SET balance = %s
        WHERE id = %s
    """
    cart_paid = """
        UPDATE carts
        SET is_paid = true
        WHERE id = ANY(%s)
    """

    used_vouchers_insert = """
        INSERT INTO usedVouchers (user_id, voucher_id) 
        VALUES (%s, %s)
    """
    update_product_stock_query = """
        UPDATE products 
        SET available_amount = available_amount - %s
        WHERE id=%s;
    """
    try:
        with conn.cursor() as cur:
            cur.execute(user_query, (datas.userId,))
            user = cur.fetchone()
            if user == None:
                return {"Status": "Failed", "Message": "User Tidak Ditemukan"}
            cur.execute(cart_query, (datas.userId,))
            cart_products = cur.fetchall()
            if len(cart_products) == 0:
                return {"Status": "Failed", "Message": "Belum Ada Produk di Keranjang"}
            # Calculate if quantity more than available product
            subtotal = 0
            for product in cart_products:
                if product["is_exceed"] == 1:  # type: ignore
                    return {
                        "Status": "Failed",
                        "Message": "Jumlah Produk yang Akan Dibeli Melebihi Stok yang Ada",
                    }
                subtotal += product["price"] * product["quantity"]  # type: ignore
            total = subtotal
            # Do Discount (Voucher)
            cur.execute(vouchers_query, (datas.voucherNames, datas.userId))
            vouchers = cur.fetchall()
            cashback = 0.0
            voucher_discount = 0.0
            for voucher in vouchers:
                before = total
                total, cashback_amount = handle_voucher(
                    total_price=total,
                    voucher_type=voucher["effect"], # type: ignore
                    amount=voucher["amount"], # type: ignore
                )  # type: ignore
                if voucher["effect"] != VoucherType.FIXED_CASHBACK.value:  # type: ignore
                    voucher_discount += before - total
                cashback += cashback_amount
            # Diskon Member
            member_discount = 0.0
            if user["is_member"]:  # type: ignore
                member_discount = total * MEMBER_DISCOUNT
                total -= member_discount
            
            # total = max(0, total)
            if total < 0: 
                return {
                    "Status": "Failed", 
                    "Message": "Total pembayaran tidak valid / Potongan melebihi harga"
                }

            if cashback > total:
                return {
                    "Status": "Failed", 
                    "Message": "Cashback melebihi total pembayaran"
                }
                
            if total > user["balance"]:  # type: ignore
                return {"Status": "Failed", "Message": "Saldo Anda Tidak Mencukupi"}
            user["balance"] -= total  # type: ignore

            user["balance"] += cashback  # type: ignore

            cur.executemany(
                used_vouchers_insert,
                [(datas.userId, vouchers[i]["id"]) for i in range(len(vouchers))],  # type: ignore
            )
            cur.execute(user_change_balance_query, (user["balance"], user["id"]))  # type: ignore
            cart_ids = [product["id"] for product in cart_products]  # type: ignore
            cur.execute(cart_paid, (cart_ids,))
            # Dont forget subtract available product
            product_id_subtract = [(product["quantity"], product["product_id"]) for product in cart_products]  # type: ignore
            cur.executemany(update_product_stock_query, product_id_subtract)
            conn.commit()
            return {
                "Status": "Success",
                "Message": "Keranjang Anda Berhasil Dibayar",
                "Detail": {
                    "subtotal": round(subtotal, 2),
                    "voucher_discount": round(voucher_discount, 2),
                    "member_discount": round(member_discount, 2),
                    "cashback": round(cashback, 2),
                    "total_paid": round(total, 2),
                    "new_balance": round(user["balance"], 2),  # type: ignore
                },
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal membayar: {str(e)}")
