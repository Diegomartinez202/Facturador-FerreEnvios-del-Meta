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
        # Tabla de productos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                codigo TEXT PRIMARY KEY,
                descripcion TEXT,
                cantidad INTEGER,
                precio REAL
            )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            nit_cedula TEXT PRIMARY KEY,
            nombre TEXT,
            telefono TEXT,
            direccion TEXT,
            email TEXT  -- Nuevo campo opcional
        )
        """)
        # --- LÓGICA DE EMERGENCIA: Agregar columna email si la DB ya existía ---
        try:
            cursor.execute("ALTER TABLE clientes ADD COLUMN email TEXT")
        except sqlite3.OperationalError:
            # Si el error es porque la columna ya existe, no hacemos nada
            pass
        
        # Tabla de historial de ventas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historial_ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT,
                tipo_doc TEXT,
                numero_doc TEXT,
                cliente_nombre TEXT,
                total REAL
            )
        """)
        conn.commit()
        conn.close()

    # MEJORA: Obtener siguiente número incremental
    def obtener_siguiente_numero(self, tipo_doc):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(CAST(numero_doc AS INTEGER)) FROM historial_ventas WHERE tipo_doc = ?", (tipo_doc,))
        resultado = cursor.fetchone()[0]
        conn.close()
        return str(resultado + 1) if resultado else "1001"

    # MEJORA: Gestión de Clientes
    def guardar_cliente(self, nit, nombre, tel, dir, email=""):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO clientes (nit_cedula, nombre, telefono, direccion, email) 
            VALUES (?, ?, ?, ?, ?)
        """, (nit, nombre, tel, dir, email))
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
        df = df.dropna(how='all', axis=0) 
        nombres_clave = ['Código', 'Descripción', 'Cantidad', 'Precio']
        if not all(col in df.columns for col in nombres_clave):
            for i in range(len(df)):
                fila = [str(val).strip().capitalize() for val in df.iloc[i].values]
                if 'Descripción' in fila or 'Descripcion' in fila:
                    df.columns = [str(c).strip().capitalize() for c in df.iloc[i]]
                    df = df.iloc[i+1:].reset_index(drop=True)
                    break
        for _, fila in df.iterrows():
            try:
                cod = str(fila.get('Código', fila.get('Codigo', ''))).strip().replace('.0', '')
                desc = str(fila.get('Descripción', fila.get('Descripcion', ''))).strip()
                if desc == 'nan' or cod == '' or desc == '': continue
                cant_raw = str(fila.get('Cantidad', '0')).replace(',', '').split('.')[0]
                cant = int(cant_raw) if cant_raw.isdigit() else 0
                precio_raw = str(fila.get('Precio', '0')).replace('$', '').replace('.', '').replace(',', '.').strip()
                precio = float(precio_raw)
                cursor.execute("INSERT OR REPLACE INTO productos VALUES (?, ?, ?, ?)", (cod, desc, cant, precio))
            except: continue 
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
        cursor.execute("UPDATE productos SET cantidad = cantidad - ? WHERE codigo = ?", (cantidad_vendida, str(codigo)))
        conn.commit()
        conn.close()

    def registrar_venta(self, fecha, tipo, numero, cliente, total):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO historial_ventas (fecha, tipo_doc, numero_doc, cliente_nombre, total) VALUES (?, ?, ?, ?, ?)", (fecha, tipo, numero, cliente, total))
        conn.commit()
        conn.close()