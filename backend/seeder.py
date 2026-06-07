from typing import Sequence, Tuple
import psycopg
from psycopg.rows import dict_row

DB_PARAMS: str = "dbname=kopdes user=postgres password=Delion21. host=localhost port=5432"


def get_db_connection() -> psycopg.Connection:
    return psycopg.connect(DB_PARAMS, row_factory=dict_row) # type: ignore


def seed_database() -> None:
    users_data: Sequence[Tuple[str, str, str, bool, float]] = [
        ("Andi Wijaya", "andi", "password123", True, 5_000_000.0),
        ("Siti Aminah", "siti", "password123", False, 5_000_000.0),
        ("Budi Santoso", "budi", "password123", True, 2_000.0),
        ("Tester Saldo Kurang", "tester_saldo", "password123", False, 0.0),
        ("Tester Sukses", "tester_sukses", "password123", False, 498_250_000.0),
        ("Tester Voucher", "tester_voucher", "password123", False, 496_890_000.0),
        ("Tester TC07 (Persen)", "tester_tc07", "password123", False, 4_180_000.0),
        ("Tester TC08 (Kombinasi)", "tester_tc08", "password123", False, 4_333_000.0),
        ("Tester TC09 (Member)", "tester_tc09", "password123", True, 4_240_000.0),
        ("Tester TC11 (Flat > Total)", "tester_tc11", "password123", False, 5_000_000.0),
        ("Tester TC12 (Cashback > Tot)", "tester_tc12", "password123", False, 5_000_000.0),
    ]

    products_data: Sequence[Tuple[str, int, float, str]] = [
        ("Kaos Polos", 5, 45_000.0, "Kaos polos berbahan Combed 30s yang adem dan menyerap keringat."),
        ("Sepatu Gacor", 9, 150_000.0, "Sepatu lari lokal yang sangat nyaman dan trendi untuk dipakai harian."),
        ("PRODUK TC11", 50, 5_000.0, "Produk harga 5rb tes potongan > total"),
        ("PRODUK TC12", 50, 5_000.0, "Produk harga 5rb tes cashback > total"),
        ("Jaket Hoodie", 0, 250_000.0, "Hoodie tebal dengan bahan fleece premium, cocok untuk cuaca dingin."),
        ("PRODUK TC4", 10, 40_000.0, "Produk untuk pengujian TC-04 dengan harga Rp40.000."),
        ("PRODUK TC5", 65, 50_000.0, "Produk untuk pengujian TC-05 dengan harga Rp50.000."),
        ("Paket Seratus Ribu", 2, 100_000.0, "Produk khusus untuk tes TC-06"),
        ("PRODUK TC07", 41, 100_000.0, "Produk harga 100rb untuk tes persentase"),
        ("PRODUK TC08", 42, 100_000.0, "Produk harga 100rb untuk tes kombinasi voucher"),
        ("PRODUK TC09", 42, 100_000.0, "Produk harga 100rb untuk tes diskon member"),
    ]

    vouchers_data: Sequence[Tuple[str, str, float]] = [
        ("PERSEN_ANAK_EMAS", "PERCENTAGE_DISCOUNT", 15.0),
        ("CASHBACK_MANTAP", "FIXED_CASHBACK", 20_000.0),
        ("DISKON_FLAT", "FIXED_MINUS", 10_000.0),
        ("DISKON_10_PERSEN", "PERCENTAGE_DISCOUNT", 10.0),
        ("DISKON_10K_FLAT", "FIXED_MINUS", 10_000.0),
        ("CASHBACK_10K", "FIXED_CASHBACK", 10_000.0),
    ]

    try:
        with get_db_connection() as conn, conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO Users (name, username, password, is_member, balance) 
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING;
                """,
                users_data,
            )

            cur.executemany(
                """
                INSERT INTO Products (name, available_amount, price, description) 
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING;
                """,
                products_data,
            )

            cur.executemany(
                """
                INSERT INTO Vouchers (name, effect, amount) 
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING;
                """,
                vouchers_data,
            )

            conn.commit()

    except Exception as e:
        raise RuntimeError(f"Database seeding failed: {e}") from e


if __name__ == "__main__":
    seed_database()
