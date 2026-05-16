import sqlite3
import pandas as pd
import os


class DatabaseManager:
    def __init__(self, db_path="data/ferreteria_final.db"):
        self.db_path = db_path
        if not os.path.exists("data"):
            os.makedirs("data")
        self.inicializar_tablas()

    def conectar(self):
        return sqlite3.connect(self.db_path)

    def inicializar_tablas(self):
        conn = self.conectar()
        cursor = conn.cursor()

        # 1. Tabla de productos
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS productos (
                codigo TEXT PRIMARY KEY,
                descripcion TEXT,
                cantidad INTEGER,
                precio REAL
            )
        """
        )

        # 2. Tabla de clientes
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS clientes (
                nit_cedula TEXT PRIMARY KEY,
                nombre TEXT,
                telefono TEXT,
                direccion TEXT,
                email TEXT
            )
        """
        )

        # 3. Tabla de historial de ventas
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS historial_ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT,
                tipo_doc TEXT,
                numero_doc TEXT,
                cliente_nombre TEXT,
                total REAL
            )
        """
        )

        # 4. Tabla Detalle de Ventas (La "joya" de la contabilidad)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS detalle_ventas (
                id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_doc TEXT,
                codigo_producto TEXT,
                descripcion TEXT,
                cantidad INTEGER,
                precio_venta REAL,
                costo_proveedor REAL,
                subtotal REAL,
                FOREIGN KEY (codigo_producto) REFERENCES productos(codigo)
            )
        """
        )

        # 5. Tabla de Configuración (REPARADA)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS configuracion (
                id INTEGER PRIMARY KEY CHECK (id = 1), -- Solo permitimos una fila
                nombre_empresa TEXT,
                nit TEXT,
                resolucion TEXT,
                prefijo TEXT,
                rango_desde INTEGER,
                rango_hasta INTEGER,
                fecha_vencimiento_res TEXT,
                clave_tecnica TEXT,
                ambiente TEXT DEFAULT '1'
            )
        """
        )

        # INSERT O REPLACE: Esto asegura que si los datos no están, se pongan.
        cursor.execute(
            """
            INSERT OR IGNORE INTO configuracion (id, nombre_empresa, nit, resolucion, prefijo, rango_desde, rango_hasta)
            VALUES (1, 'FERREENVIOS DEL META', '800.123.456-7', '18760000001', 'NC', 1, 5000)
        """
        )

        # Insertamos datos iniciales solo si la tabla está vacía
        cursor.execute("SELECT COUNT(*) FROM configuracion")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                """
                INSERT INTO configuracion (nombre_empresa, nit, resolucion, prefijo, rango_desde, rango_hasta)
                VALUES ('FERREENVIOS DEL META', '1.121.937.188', '18760000001', 'FEV', 1, 5000)
            """
            )

        # --- MIGRACIONES SILENCIOSAS (MANTENIMIENTO DE COLUMNAS) ---
        try:
            cursor.execute(
                "ALTER TABLE productos ADD COLUMN categoria TEXT DEFAULT 'General'"
            )
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE clientes ADD COLUMN email TEXT")
        except sqlite3.OperationalError:
            pass

        # --- MEJORA ARQUITECTURA DIAN Y COSTOS ---
        try:
            # Costos y Tarifa IVA
            cursor.execute(
                "ALTER TABLE productos ADD COLUMN costo_proveedor REAL DEFAULT 0.0"
            )
            cursor.execute(
                "ALTER TABLE productos ADD COLUMN tarifa_iva REAL DEFAULT 19.0"
            )

            # Trazabilidad Legal DIAN en historial
            cursor.execute("ALTER TABLE historial_ventas ADD COLUMN cufe TEXT")
            cursor.execute("ALTER TABLE historial_ventas ADD COLUMN url_xml TEXT")
            cursor.execute(
                "ALTER TABLE historial_ventas ADD COLUMN costo_flete REAL DEFAULT 0.0"
            )
            cursor.execute(
                "ALTER TABLE historial_ventas ADD COLUMN estado_dian TEXT DEFAULT 'PENDIENTE'"
            )

            # Códigos internacionales UNSPSC y Unidad de Medida
            cursor.execute(
                "ALTER TABLE productos ADD COLUMN codigo_unspsc TEXT DEFAULT '27110000'"
            )
            cursor.execute(
                "ALTER TABLE productos ADD COLUMN unidad_medida TEXT DEFAULT '94'"
            )
        except sqlite3.OperationalError:
            pass

        conn.commit()
        conn.close()

    def registrar_venta(
        self,
        fecha,
        tipo,
        num,
        cliente,
        total,
        carrito=None,
        cufe=None,
        xml=None,
        flete=0.0,
    ):
        """Método Maestro: Registra legalidad DIAN y detalle de productos para utilidades"""
        conn = self.conectar()
        cursor = conn.cursor()
        try:
            # 1. Guardar ENCABEZADO
            cursor.execute(
                """
                INSERT INTO historial_ventas 
                (fecha, tipo_doc, numero_doc, cliente_nombre, total, cufe, url_xml, costo_flete, estado_dian)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    fecha,
                    tipo,
                    num,
                    cliente,
                    total,
                    cufe,
                    xml,
                    flete,
                    "EXITOSO" if cufe else "LOCAL",
                ),
            )

            # 2. Guardar DETALLE
            if carrito:
                for item in carrito:
                    subtotal_item = item["cant"] * item["precio"]
                    cursor.execute(
                        """
                        INSERT INTO detalle_ventas 
                        (numero_doc, codigo_producto, descripcion, cantidad, precio_venta, costo_proveedor, subtotal)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            num,
                            item["cod"],
                            item["desc"],
                            item["cant"],
                            item["precio"],
                            item.get("costo_proveedor", 0),
                            subtotal_item,
                        ),
                    )

            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    # MEJORA: Obtener siguiente número incremental
    def obtener_siguiente_numero(self, tipo):
        conn = self.conectar()
        cursor = conn.cursor()
        # Filtramos por tipo_doc para que el conteo de Facturas no afecte al de Notas Crédito
        cursor.execute(
            "SELECT COUNT(*) FROM historial_ventas WHERE tipo_doc = ?",
        (tipo,),
        )
        res = cursor.fetchone()[0]
        conn.close()
        return (res + 1)

    # MEJORA: Gestión de Clientes
    def guardar_cliente(self, nit, nombre, tel, dir, email=""):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO clientes (nit_cedula, nombre, telefono, direccion, email) 
            VALUES (?, ?, ?, ?, ?)
        """,
            (nit, nombre, tel, dir, email),
        )
        conn.commit()
        conn.close()

    def obtener_clientes(self):
        conn = self.conectar()
        df = pd.read_sql_query("SELECT * FROM clientes", conn)
        conn.close()
        return df

    def importar_desde_excel(self, df):
        """Lógica robusta de limpieza original intacta"""
        conn = self.conectar()
        cursor = conn.cursor()
        df = df.dropna(how="all", axis=0)

        nombres_clave = ["Código", "Descripción", "Categoría", "Cantidad", "Precio"]

        if not all(col in df.columns for col in nombres_clave):
            for i in range(len(df)):
                fila = [str(val).strip().capitalize() for val in df.iloc[i].values]
                if "Descripción" in fila or "Descripcion" in fila:
                    df.columns = [str(c).strip().capitalize() for c in df.iloc[i]]
                    df = df.iloc[i + 1 :].reset_index(drop=True)
                    break
        for _, fila in df.iterrows():
            try:
                cod = (
                    str(fila.get("Código", fila.get("Codigo", "")))
                    .strip()
                    .replace(".0", "")
                )
                desc = str(fila.get("Descripción", fila.get("Descripcion", ""))).strip()

                cat = str(
                    fila.get("Categoría", fila.get("Categoria", "General"))
                ).strip()
                if cat == "nan" or cat == "":
                    cat = "General"

                if desc == "nan" or cod == "" or desc == "":
                    continue

                cant_raw = str(fila.get("Cantidad", "0")).replace(",", "").split(".")[0]
                cant = int(cant_raw) if cant_raw.isdigit() else 0

                precio_raw = (
                    str(fila.get("Precio", "0"))
                    .replace("$", "")
                    .replace(".", "")
                    .replace(",", ".")
                    .strip()
                )
                precio = float(precio_raw)
                cursor.execute(
                    "INSERT OR REPLACE INTO productos (codigo, descripcion, cantidad, precio, categoria) VALUES (?, ?, ?, ?, ?)",
                    (cod, desc, cant, precio, cat),
                )
            except:
                continue
        conn.commit()
        conn.close()

    def obtener_productos(self):
        conn = self.conectar()
        df = pd.read_sql_query("SELECT * FROM productos", conn)
        conn.close()
        return df

    def descontar_stock(self, codigo, cantidad_vendida):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE productos SET cantidad = cantidad - ? WHERE codigo = ?",
            (cantidad_vendida, str(codigo)),
        )
        conn.commit()
        conn.close()

    def update_producto(id_producto, nueva_desc, nuevo_precio):
        conn = sqlite3.connect("data/database.db")  # Ajusta a tu ruta
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE productos 
            SET descripcion = ?, precio = ? 
            WHERE id = ?
        """,
            (nueva_desc, nuevo_precio, id_producto),
        )
        conn.commit()
        conn.close()

    def insert_producto(codigo, descripcion, precio):
        conn = sqlite3.connect("data/database.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO productos (codigo, descripcion, precio) VALUES (?, ?, ?)",
            (codigo, descripcion, precio),
        )
        conn.commit()
        conn.close()

    def delete_producto(id_producto):
        conn = sqlite3.connect("data/database.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM productos WHERE id = ?", (id_producto,))
        conn.commit()
        conn.close()

    def obtener_producto_por_codigo(self, codigo):
        conn = self.conectar()
        # Usamos dict_factory o similar para devolver un diccionario
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM productos WHERE codigo = ?", (codigo,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def actualizar_inventario_completo(self, df_nuevo):
        """Sobrescribe la tabla de productos con los datos editados en el Editor Maestro"""
        try:
            conn = self.conectar()
            # 'if_exists=replace' asegura que la estructura se mantenga y los datos se actualicen
            df_nuevo.to_sql("productos", conn, if_exists="replace", index=False)
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Error Crítico al guardar en DB: {e}")
            return False
        
    def obtener_configuracion(self):
        """Devuelve los datos de la empresa para el encabezado del PDF"""
        conn = self.conectar()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM configuracion WHERE id = 1")
        res = cursor.fetchone()
        conn.close()
        return dict(res) if res else {
            "nombre_empresa": "FERREENVIOS (TEMP)", 
            "nit": "000.000.000-0"
        }
