import sqlite3
import os


class InventoryAdapter:
    def __init__(self):
        # Buscamos la carpeta raíz y luego entramos a /data/
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, "data", "ferreteria_final.db")

    def procesar_descuento_stock(self, carrito):
        conn = None
        try:
            if not os.path.exists(self.db_path):
                return False, f"Base de datos no hallada en: {self.db_path}"

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for item in carrito:
                codigo = str(item["cod"]).strip()
                cantidad = item["cant"]

                # Actualizamos la tabla 'productos' que ya vimos que existe en tu script
                cursor.execute(
                    """
                    UPDATE productos 
                    SET cantidad = cantidad - ? 
                    WHERE codigo = ?
                """,
                    (cantidad, codigo),
                )

                if cursor.rowcount == 0:
                    conn.rollback()
                    return False, f"Producto [{codigo}] no existe."

            conn.commit()
            return True, "Inventario actualizado correctamente"
        except Exception as e:
            if conn:
                conn.rollback()
            return False, f"Error en Microservicio Inventario: {str(e)}"
        finally:
            if conn:
                conn.close()
