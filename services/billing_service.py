import json
import sqlite3
import requests  # Para enviar el JSON a la API


class BillingService:
    def __init__(self, db_path="ferreteria.db"):
        self.db_path = db_path

    def _obtener_datos(self, id_factura):
        """Privado: Extrae datos crudos de la DB"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Factura
        cursor.execute("SELECT * FROM facturas WHERE id_factura = ?", (id_factura,))
        factura = cursor.fetchone()

        # Detalles
        cursor.execute(
            """
            SELECT d.*, p.nombre, p.codigo_barras 
            FROM detalle_factura d
            JOIN productos p ON d.id_producto = p.id_producto
            WHERE d.id_factura = ?
        """,
            (id_factura,),
        )
        detalles = cursor.fetchall()

        conn.close()
        return factura, detalles

    def generar_json_dian(self, id_factura):
        """Construye el JSON estructurado"""
        factura, detalles = self._obtener_datos(id_factura)
        if not factura:
            return None

        items = []
        for item in detalles:
            items.append(
                {
                    "code": item["codigo_barras"],
                    "description": item["nombre"],
                    "quantity": item["cantidad"],
                    "price": float(item["precio_unitario_vendido"]),
                    "tax_rate": "19.00",  # Aquí podrías traerlo de la DB
                    "unit_measure_id": 94,
                }
            )

        json_payload = {
            "billing_resolution": "18760000001",
            "prefix": "FEV",
            "number": str(factura["numero_factura"]).replace("FEV", ""),
            "date": factura["fecha_emision"].split()[0],
            "customer": {
                "identification_number": factura["id_cliente"],
                "name": factura["nombre_cliente"],
                "email": factura["email_cliente"],
            },
            "items": items,
        }
        return json_payload

    def enviar_a_api(self, id_factura):
        """Lógica de microservicio: Genera y Envía"""
        payload = self.generar_json_dian(id_factura)
        # Aquí vendría el requests.post a la URL del proveedor
        # response = requests.post("URL_PROVEEDOR", json=payload)
        # return response.json()
        return payload  # Por ahora retornamos el JSON para pruebas
