import streamlit as st
from modules.database_manager import DatabaseManager
import pandas as pd
from datetime import datetime
import os

# 1. CONFIGURACIÓN GLOBAL DEL SISTEMA
st.set_page_config(page_title="Ferreenvios Pro", page_icon="🛠️", layout="wide")

# 2. --- ESTILO PROFESIONAL PERSONALIZADO (Colores Corporativos) ---
st.markdown(
    """
    <style>
    .main { background-color: #f5f7f9; }
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        border-left: 6px solid #1A365D;
    }
    [data-testid="stSidebar"] {
        background-color: #1A365D;
    }
    .st-emotion-cache-16idsys p {
        color: white !important;
        font-weight: bold;
    }
    h1, h2, h3 {
        color: #1A365D;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .stButton>button {
        border-radius: 8px;
        height: 3em;
        background-color: #1A365D;
        color: white;
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #2c5282;
        border-color: #2c5282;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 3. INICIALIZAR BASE DE DATOS
if "db" not in st.session_state:
    st.session_state.db = DatabaseManager()


def main():
    # --- ENCABEZADO PRINCIPAL ---
    col_t1, col_t2 = st.columns([1, 5])
    with col_t1:
        if os.path.exists("assets/logo.png"):
            st.image("assets/logo.png", width=130)
    with col_t2:
        st.title("Panel de Control Administrativo")
        st.caption("Ferreenvios & Suministros | Gestión Comercial 2026")

    st.markdown("---")

    # --- LÓGICA DE DATOS Y VALIDACIÓN TÉCNICA (Sincronizada) ---
    recaudo_hoy = 0
    utilidad_hoy = 0
    total_docs_historico = 0
    facturas_conteo_total = 0
    cotizaciones_conteo_total = 0
    df_facts_hoy = pd.DataFrame()

    ruta_db = "data/ferreteria_final.db"
    db_existe = os.path.exists(ruta_db)
    estado_sistema = "Sincronizado ✅" if db_existe else "Error DB ❌"

    if db_existe:
        try:
            conn = st.session_state.db.conectar()

            # MEJORA: Traemos TODO el historial para métricas y gráficos
            df_ventas_todo = pd.read_sql_query(
                """
                SELECT v.total, v.fecha, v.tipo_doc, v.numero_doc,
                (SELECT SUM(d.subtotal - (d.cantidad * d.costo_proveedor)) 
                 FROM detalle_ventas d WHERE d.numero_doc = v.numero_doc) as utilidad_doc
                FROM historial_ventas v
                """,
                conn,
            )
            conn.close()

            if not df_ventas_todo.empty:
                # --- 1. LÓGICA DE GRÁFICOS (Ventas vs Devoluciones) ---
                st.markdown("### 📈 Flujo de Caja (Ventas y Devoluciones)")

                # Agrupamos por fecha y tipo para el gráfico
                df_grafico = (
                    df_ventas_todo.groupby(["fecha", "tipo_doc"])["total"]
                    .sum()
                    .reset_index()
                )

                st.bar_chart(
                    df_grafico,
                    x="fecha",
                    y="total",
                    color="tipo_doc",
                )

                # --- 2. CÁLCULOS DE RECAUDO Y UTILIDAD (Solo Hoy) ---
                df_ventas_todo["fecha"] = df_ventas_todo["fecha"].astype(str)
                fecha_actual = datetime.now().strftime("%Y-%m-%d")

                # Filtramos los movimientos de hoy en memoria
                df_hoy = df_ventas_todo[
                    df_ventas_todo["fecha"].str.contains(fecha_actual)
                ]

                # Separamos por tipo para el cálculo neto
                df_facts_hoy = df_hoy[df_hoy["tipo_doc"] == "FACTURA DE VENTA"]
                df_nc_hoy = df_hoy[df_hoy["tipo_doc"] == "NOTA CRÉDITO"]

                # 💵 Recaudo Real = Ventas Brutas - Notas Crédito
                recaudo_hoy = df_facts_hoy["total"].sum() - df_nc_hoy["total"].sum()

                if "utilidad_doc" in df_hoy.columns:
                    # Utilidad Neta = Utilidad de ventas - Valor total devuelto (estimado)
                    utilidad_hoy = df_facts_hoy["utilidad_doc"].sum() - (
                        df_nc_hoy["total"].sum() * 0.20
                    )

                # --- 3. CONTEO HISTÓRICO TOTAL ---
                total_docs_historico = len(df_ventas_todo)
                facturas_conteo_total = len(
                    df_ventas_todo[df_ventas_todo["tipo_doc"] == "FACTURA DE VENTA"]
                )
                cotizaciones_conteo_total = len(
                    df_ventas_todo[df_ventas_todo["tipo_doc"] == "COTIZACIÓN"]
                )

            else:
                st.info(
                    "Aún no hay datos suficientes para generar el gráfico de flujo."
                )

        except Exception as e:
            estado_sistema = "Error Crítico ⚠️"
            st.error(f"Error al leer base de datos: {e}")

    else:
        st.error(f"🚨 No se encontró el archivo de base de datos en {ruta_db}")
    # --- PANEL VISUAL DE 4 MÉTRICAS (Actualizado en app.py) ---
    st.markdown("### 📊 Resumen de Operaciones")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("FACTURACIÓN HOY", f"${recaudo_hoy:,.0f} COP")

    with c2:
        # Aquí inyectamos la utilidad real basada en tu Costo Inversión
        st.metric(
            "UTILIDAD ESTIMADA",
            f"${utilidad_hoy:,.0f} COP",
            delta=f"{len(df_facts_hoy)} ventas",
        )

    with c3:
        st.metric(
            "🧾 DOCUMENTACIÓN",
            f"{total_docs_historico} Archivos",
            help=f"Histórico Total:\n- Facturas: {facturas_conteo_total}\n- Cotizaciones: {cotizaciones_conteo_total}",
        )

    with c4:
        st.metric("ESTADO DEL SISTEMA", estado_sistema)


def calcular_metricas_reales(conn):
    cursor = conn.cursor()
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")

    # 1. Sumamos las Ventas
    cursor.execute(
        """
        SELECT SUM(total) FROM historial_ventas 
        WHERE fecha = ? AND tipo_doc = 'FACTURA DE VENTA'
    """,
        (fecha_hoy,),
    )
    ventas = cursor.fetchone()[0] or 0

    # 2. Sumamos las Devoluciones (Notas Crédito)
    cursor.execute(
        """
        SELECT SUM(total) FROM historial_ventas 
        WHERE fecha = ? AND tipo_doc = 'NOTA CRÉDITO'
    """,
        (fecha_hoy,),
    )
    devoluciones = cursor.fetchone()[0] or 0

    # 3. RESULTADO NETO (Lo que realmente hay en la caja)
    recaudo_real = ventas - devoluciones

    return recaudo_real


def mostrar_dashboard_devoluciones(db_path):
    import datetime

    hoy = datetime.date.today()
    primer_dia_mes = hoy.replace(day=1).strftime("%Y-%m-%d")

    try:
        conn = sqlite3.connect(db_path)
        # Contamos cuántas notas crédito hay este mes
        query = """
            SELECT COUNT(*) as cantidad, SUM(total) as monto 
            FROM historial_ventas 
            WHERE tipo_doc = 'NOTA CRÉDITO' 
            AND fecha >= ?
        """
        res = pd.read_sql_query(query, conn, params=(primer_dia_mes,)).iloc[0]
        conn.close()

        st.subheader("⚠️ Alerta de Mercancía Devuelta (Mes Actual)")
        c1, c2 = st.columns(2)

        # Si hay muchas devoluciones, se pone en rojo para alertar a Daniel
        color_alerta = "normal" if res["cantidad"] < 5 else "inverse"

        c1.metric(
            "Devoluciones Realizadas",
            f"{int(res['cantidad'])} Facturas",
            delta=f"{int(res['cantidad'])} este mes",
            delta_color=color_alerta,
        )
        c2.metric(
            "Valor en Mercancía Retornada",
            f"${int(res['monto'] or 0):,}",
            help="Dinero que salió de caja o se cruzó por cambios",
        )

        if res["cantidad"] > 0:
            st.warning(
                f"💡 Daniel, has recibido {int(res['cantidad'])} devoluciones. Revisa si algún proveedor está entregando productos defectuosos."
            )

    except Exception as e:
        pass  # Si la tabla de historial no tiene el tipo 'NOTA CRÉDITO' aún, no muestra error

    st.markdown("---")

    # --- SECCIÓN DE ACCIONES RÁPIDAS (Botonera Ajustada a tus nombres) ---
    st.subheader("🚀 Acciones Rápidas")
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        if st.button("📝 Crear Nueva Factura", use_container_width=True):
            # Navegación hacia Facturador.py
            st.switch_page("pages/Facturador.py")

    with col_b:
        if st.button("📦 Revisar Inventario", use_container_width=True):
            # Navegación hacia Inventario.py
            st.switch_page("pages/Inventario.py")

    with col_c:
        if st.button("📊 Reporte de Ventas", use_container_width=True):
            # Navegación hacia Historial.py
            st.switch_page("pages/Historial.py")

    st.markdown("---")

    # --- GUÍA RÁPIDA ---
    with st.expander("ℹ️ Información de Ayuda"):
        st.write(
            """
        - **Facturador:** Permite realizar ventas descontando stock o crear cotizaciones simples.
        - **Inventario:** Pestaña para actualizar precios y cantidades mediante archivos Excel.
        - **Historial:** Registro completo de todas las ventas finalizadas para cierre de caja.
        """
        )

    st.caption("Ferreenvios & Suministros del Meta | Villavicencio, Colombia")


if __name__ == "__main__":
    main()
