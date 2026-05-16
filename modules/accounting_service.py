import sqlite3
import os
from datetime import datetime


class AccountingService:
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, "data", "ferreteria_final.db")
        self._crear_tabla_contable()

    def _crear_tabla_contable(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS auditoria_contable (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                num_factura TEXT,
                fecha_registro TIMESTAMP,
                base_imponible REAL,
                valor_iva REAL,
                valor_flete REAL,
                total_fiscal REAL
            )
        """
        )
        conn.commit()
        conn.close()

    def registrar_impuestos(self, num_factura, fin_data):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO auditoria_contable 
                (num_factura, fecha_registro, base_imponible, valor_iva, valor_flete, total_fiscal)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    num_factura,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    fin_data["subtotal"],
                    fin_data["v_iva"],
                    fin_data["flete"],
                    fin_data["total"],
                ),
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error en Contabilidad: {e}")
            return False
