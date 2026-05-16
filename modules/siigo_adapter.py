import sqlite3
import os
import requests
import json
import time
import streamlit as st


class SiigoAdapter:
    def __init__(self):
        # 1. Definición de rutas
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, "data", "ferreteria_final.db")
        
        # 2. Configuración de Ambiente (Manual)
        self.PRODUCCION = False 
        
        # 3. Importación de la API
        from modules.siigo_api import ClienteApiSiigo
        
        try:
            # Intentamos leer la configuración de Daniel
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            config = conn.execute("SELECT * FROM configuracion WHERE id = 1").fetchone()
            conn.close()
            
            # --- AQUÍ SE DECIDE SI ES PRUEBA O REAL ---
            if config and config["email_siigo"] and config["clave_tecnica"]:
                # CASO REAL: El sistema encuentra datos y se prepara para conectar con Siigo
                self.api = ClienteApiSiigo(
                    config["email_siigo"], 
                    config["clave_tecnica"], 
                    es_produccion=self.PRODUCCION
                )
            else:
                # CASO PRUEBA: Si no hay datos, creamos la marca "TEST_MODE"
                # Esto es lo que el 'if' del enviar_nota_credito detectará
                self.api = ClienteApiSiigo("TEST_MODE", "TEST_MODE", es_produccion=False)
                
        except Exception as e:
            # Si hay un error de lectura, inicializamos en modo seguro para no romper el programa
            self.api = ClienteApiSiigo("dummy", "dummy", es_produccion=False)
            
    def construir_json_siigo(self, factura, detalles):
        """Traduce datos de SQLite al formato UBL 2.1 de Siigo"""
        payload = {
            "document": {"id": 24331},  # ID estándar de Factura en Siigo
            "number": int(factura["numero_doc"]),
            "date": factura["fecha"],
            "customer": {
                "identification": factura[
                    "cliente_nombre"
                ],  # Cambiar por NIT si lo tienes
                "check_digit": "0",
            },
            "seller": 1,
            "items": [],
        }

        for d in detalles:
            item = {
                "code": d["codigo_producto"],
                "description": d["descripcion"],
                "quantity": d["cantidad"],
                "price": d["precio_venta"],
                "taxes": [{"id": 1, "percentage": 19}],  # IVA 19%
            }
            payload["items"].append(item)

        # Incluir el flete de $3,000 que arreglamos en utils
        if factura["costo_flete"] > 0:
            payload["items"].append(
                {
                    "code": "FLETE01",
                    "description": "SERVICIO DE TRANSPORTE",
                    "quantity": 1,
                    "price": factura["costo_flete"],
                    "taxes": [],
                }
            )
        return payload

    def enviar_a_siigo(self, numero_doc_local):
        """
        Método Maestro: Decide si usa Simulación o Envío Real
        según la configuración.
        """
        # 1. Extraer datos locales
        factura, detalles = self._extraer_datos_locales(numero_doc_local)
        
        if not factura:
            # Quitamos los procesos de cursor/conn que no pertenecen a este bloque
            return False, "Factura no encontrada en DB local."

        # 2. Construir el JSON profesional (Traductor)
        payload = self.construir_json_siigo(factura, detalles)

        # --- OPCIÓN A: ENVÍO REAL (Si se activa PRODUCCION o existen Secrets) ---
        if self.PRODUCCION or "siigo" in st.secrets:
            try:
                from modules.siigo_api import ClienteApiSiigo

                # Intentamos obtener credenciales de Secrets o de la DB
                try:
                    user = st.secrets["siigo"]["username"]
                    key = st.secrets["siigo"]["access_key"]
                except:
                    # Si no hay secrets, buscamos en la DB (lo que configuramos en Administración)
                    conn = sqlite3.connect(self.db_path)
                    conn.row_factory = sqlite3.Row
                    config = (
                        conn.cursor()
                        .execute("SELECT * FROM configuracion WHERE id = 1")
                        .fetchone()
                    )
                    conn.close()
                    user = config["email_siigo"]
                    key = config["clave_tecnica"]

                api = ClienteApiSiigo(user, key, es_produccion=self.PRODUCCION)

                with st.spinner("Comunicando con la DIAN / Siigo..."):
                    respuesta, status_code = api.enviar_factura(payload)

                if status_code in [200, 201]:
                    cufe = respuesta.get("cufe", "EXITOSO-SIN-CUFE")
                    self._actualizar_estado_dian(numero_doc_local, cufe)
                    return True, f"✅ Aprobado Real: {cufe}"
                else:
                    error_msg = respuesta.get("error", "Error en servidor Siigo")
                    return False, f"❌ Rechazo Real: {error_msg}"
            except Exception as e:
                return False, f"⚠️ Error en flujo real: {str(e)}"

        # --- OPCIÓN B: SIMULACIÓN PARA PRUEBAS (Tu código original) ---
        else:
            try:
                time.sleep(2)  # Simula latencia
                status_code = 200
                respuesta_mock = {
                    "cufe": "CUFE-PRUEBA-FERREENVIOS-2026",
                    "qr_url": "https://catalogo.dian.gov.co/doc/prueba",
                }

                if status_code == 200:
                    cufe = respuesta_mock.get("cufe")
                    self._actualizar_estado_dian(numero_doc_local, cufe)
                    return True, f"🛡️ Simulación Exitosa: {cufe}"
                else:
                    return False, "Simulación fallida."
            except Exception as e:
                return False, f"Error en simulación: {str(e)}"

    def _actualizar_estado_dian(self, numero_doc, cufe):
        """Actualiza la base de datos local con el CUFE recibido"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE historial_ventas 
            SET cufe = ?, estado_dian = 'APROBADO' 
            WHERE numero_doc = ?
        """,
            (cufe, numero_doc),
        )
        conn.commit()
        conn.close()

    def _recuperar_stock_devolucion(self, items_devueltos):
        """Suma las cantidades devueltas al inventario actual"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for item in items_devueltos:
                cursor.execute(
                    """
                    UPDATE productos 
                    SET cantidad = cantidad + ? 
                    WHERE codigo_barras = ? OR id_producto = ?
                """,
                    (item["cantidad"], item["codigo"], item["codigo"]),
                )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error recuperando stock: {e}")
            return False

    def enviar_nota_credito(self, numero_doc, motivo, items_devueltos):
        """Coordina la validación de prueba y la seguridad real DIAN"""
        try:
            # --- BLOQUE 1: VALIDACIÓN DE PRUEBA (Sin eliminar nada) ---
            # Si el sistema detecta que estamos en modo manual/test, procesa y recupera stock
            if self.api and self.api.es_api_de_prueba():
                self._recuperar_stock_devolucion(items_devueltos)
                return self._simular_envio(f"NC-{numero_doc}")

            # --- BLOQUE 2: VALIDACIÓN DE SEGURIDAD REAL ---
            # Si no es prueba, el sistema EXIGE que la API esté inicializada
            if not self.api:
                return False, "Error de Seguridad: API no inicializada. Registre credenciales en Configuración."

            # Si llegamos aquí, es una operación REAL. No se elimina ninguna validación.
            from modules.nota_credito_manager import NotaCreditoManager
            manager = NotaCreditoManager()
            payload = manager.generar_json_nota_credito(numero_doc, motivo, items_devueltos)

            # Intento de envío real a Siigo
            respuesta, status_code = self.api.enviar_documento("credit-notes", payload)

            if status_code in [200, 201]:
                cune = respuesta.get("cune")
                # Éxito real: Recuperamos stock y actualizamos historial
                self._recuperar_stock_devolucion(items_devueltos)
                self._actualizar_estado_dian(f"NC-{numero_doc}", cune)
                return True, cune
            else:
                # Si la DIAN rechaza, devolvemos el error de seguridad de la API
                return False, f"Rechazo de Seguridad DIAN: {respuesta}"

        except Exception as e:
            # Blindaje total contra fallos inesperados
            return False, f"Fallo Crítico de Seguridad: {str(e)}"
        
    def _extraer_datos_locales(self, id_factura):
        """Consulta la BD local asegurando que siempre devuelva dos valores"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Buscamos por numero_doc (que es el num_base que enviamos)
            cursor.execute(
                "SELECT * FROM historial_ventas WHERE numero_doc = ?",
                (str(id_factura),),
            )
            factura = cursor.fetchone()

            if not factura:
                conn.close()
                return None, None  # <-- IMPORTANTE: Devuelve dos valores

            cursor.execute(
                "SELECT * FROM detalle_ventas WHERE numero_doc = ?", (str(id_factura),)
            )
            return dict(factura), [dict(d) for d in detalles]

            conn.close()
            return factura, detalles

        except Exception as e:
            print(f"Error crítico en la extracción: {e}")

            return None, None
        
    def _simular_envio(self, numero_doc_local):
        """
        Esta es la función que faltaba. 
        Simula una respuesta exitosa de la DIAN para pruebas internas.
        """
        import time
        # 1. Simulamos una pequeña espera de red (2 segundos)
        time.sleep(2)
        
        # 2. Creamos un CUFE de prueba
        cufe_simulado = "CUFE-SIMULADO-FERREENVIOS-2026-TEST"
        
        # 3. Actualizamos la base de datos local para que Daniel vea el cambio
        self._actualizar_estado_dian(numero_doc_local, cufe_simulado)
        
        # 4. Retornamos el éxito con el escudo de protección
        return True, f"🛡️ Simulación Exitosa: {cufe_simulado}"
