import sqlite3
import os
import streamlit as st
from datetime import datetime
from io import BytesIO

class NotaCreditoManager:
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, "data", "ferreteria_final.db")

    def obtener_productos_factura(self, numero_doc):
        """Busca los productos asociados a una factura para mostrarlos en la devolución"""
        try:
            # Usamos la conexión ya establecida en el init
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
                SELECT codigo_producto, descripcion, cantidad, precio_venta 
                FROM detalle_ventas 
                WHERE numero_doc = ?
            """
            items = cursor.execute(query, (numero_doc,)).fetchall()
            conn.close()
            
            return [dict(item) for item in items]
            
        except Exception as e:
            st.error(f"Error en obtener_productos_factura: {e}")
            return []

    def generar_json_nota_credito(self, numero_doc_original, motivo, items_devueltos):
        """Construye el payload profesional para la API de Siigo"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 1. Traer la factura original para obtener el CUFE/UUID
            cursor.execute("SELECT * FROM historial_ventas WHERE numero_doc = ?", (numero_doc_original,))
            factura_origen = cursor.fetchone()

            if not factura_origen or not factura_origen["cufe"]:
                conn.close()
                raise Exception("La factura no existe o no tiene CUFE legal.")

            items_nc = []
            subtotal_nc = 0

            # 2. Procesar cada item para el formato de la API
            for item in items_devueltos:
                cursor.execute("""
                    SELECT * FROM detalle_ventas 
                    WHERE numero_doc = ? AND codigo_producto = ?
                """, (numero_doc_original, item["codigo"]))

                det = cursor.fetchone()
                if det:
                    valor_dev = det["precio_venta"] * item["cantidad"]
                    subtotal_nc += valor_dev
                    items_nc.append({
                        "code": det["codigo_producto"],
                        "description": f"DEVOLUCION: {det['descripcion']}",
                        "quantity": item["cantidad"],
                        "price": det["precio_venta"],
                        "tax_amount": valor_dev * 0.19,
                    })

            payload = {
                "type": "CreditNote",
                "reason_code": motivo,
                "relation_invoice": {
                    "number": factura_origen["numero_doc"],
                    "cufe": factura_origen["cufe"],
                },
                "items": items_nc,
                "total": subtotal_nc * 1.19,
            }
            conn.close()
            return payload
        except Exception as e:
            return {"error": str(e)}

    def _recuperar_stock_fisico(self, items):
        """Actualiza el inventario sumando lo devuelto"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for item in items:
                cursor.execute("""
                    UPDATE productos SET cantidad = cantidad + ? 
                    WHERE codigo = ?
                """, (item["cantidad"], item["codigo"]))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error stock: {e}")
            return False

    def _registrar_en_historial(self, numero_doc_orig, cune, total_nc, cliente):
        """Inserta el registro negativo en el historial de ventas"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            fecha_hoy = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO historial_ventas (numero_doc, fecha, cliente_nombre, total, tipo_doc, cufe, estado_dian)
                VALUES (?, ?, ?, ?, 'NOTA CRÉDITO', ?, 'APROBADO')
            """, (f"NC-{numero_doc_orig}", fecha_hoy, cliente, -total_nc, cune)) 
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Error historial: {e}")

def generar_pdf_binario(datos_nc, factura_orig, items_devueltos):
    # 1. Preparación de rutas
    logo_path = os.path.abspath("assets/logo.png")
    img_tag = f"<img src='{logo_path}' style='width: 120px;'>" if os.path.exists(logo_path) else ""


    info_cliente = factura_orig.get('factura', {})
    
    # 2. Contenido HTML (El diseño de la factura)
    html_content = f"""
    <html>
    <body style="font-family: Helvetica, Arial, sans-serif;">
        <div style="text-align: center;">
            {img_tag}
            <h2 style="color: #1A365D;">FERREENVIOS DEL META</h2>
            <p><strong>NOTA CRÉDITO DE VENTA</strong></p>
        </div>
        <hr>
        <p><strong>CUNE:</strong> {datos_nc.get('cune')}</p>
        <p><strong>Factura Relacionada:</strong> {factura_orig.get('numero_doc')}</p>
        <p><strong>Cliente:</strong> {factura_orig.get('cliente_nombre')}</p>
        <br>
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="background-color: #f2f2f2;">
                    <th style="border: 1px solid #ddd; padding: 8px;">Descripción</th>
                    <th style="border: 1px solid #ddd; padding: 8px;">Cant.</th>
                    <th style="border: 1px solid #ddd; padding: 8px;">Precio</th>
                </tr>
            </thead>
            <tbody>
    """
    for item in items_devueltos:
        html_content += f"""
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">{item['descripcion']}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{item['cantidad']}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">${item['precio']:,.0f}</td>
                </tr>"""

    html_content += "</tbody></table></body></html>"

    # 3. Motor de Renderizado (El Microservicio de PDF)
    try:
        from xhtml2pdf import pisa
        output = BytesIO()
        pisa.CreatePDF(html_content, dest=output)
        return output.getvalue()
    except Exception as e:
        print(f"Error generando PDF: {e}")
        return None
    
def consultar_datos_nota_credito(self, numero_factura_afectada):
    try:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Consultamos directamente el historial que es donde guardas todo
        cursor.execute("""
            SELECT h.*, c.nit_cedula, c.direccion, c.telefono
            FROM historial_ventas h
            LEFT JOIN clientes c ON h.cliente_nombre = c.nombre
            WHERE h.numero_doc = ?
        """, (numero_factura_afectada,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "factura": {
                    "cliente_nombre": row["cliente_nombre"], # Nombre correcto
                    "nit_cedula": row["nit_cedula"] if row["nit_cedula"] else "22222222",
                    "direccion": row["direccion"] if row["direccion"] else "Villavicencio",
                    "telefono": row["telefono"] if row["telefono"] else "S/N"
                }
            }
        return {}
    except Exception as e:
        print(f"Error consultando datos NC: {e}")
        return {}
