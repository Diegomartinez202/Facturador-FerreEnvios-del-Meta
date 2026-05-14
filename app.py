import streamlit as st
from modules.database_manager import DatabaseManager
import pandas as pd
from datetime import datetime
import os

# 1. CONFIGURACIÓN GLOBAL DEL SISTEMA
st.set_page_config(
    page_title="Ferreenvios Pro",
    page_icon="🛠️",
    layout="wide"
)

# 2. --- ESTILO PROFESIONAL PERSONALIZADO (Colores Corporativos) ---
st.markdown("""
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
    """, unsafe_allow_html=True)

# 3. INICIALIZAR BASE DE DATOS
if 'db' not in st.session_state:
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
    
    # --- LÓGICA DE DATOS PARA EL DASHBOARD ---
    recaudo_hoy = 0
    conteo_hoy = 0
    try:
        conn = st.session_state.db.conectar()
        # Consulta SQL para facturación del día
        query = "SELECT total FROM historial_ventas WHERE fecha = date('now')"
        df_ventas = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df_ventas.empty:
            recaudo_hoy = df_ventas['total'].sum()
            conteo_hoy = len(df_ventas)
    except:
        pass

    # --- DASHBOARD VISUAL ---
    c1, c2, c3 = st.columns(3)
    c1.metric("FACTURACIÓN HOY", f"${recaudo_hoy:,.0f} COP", f"{conteo_hoy} Documentos")
    c2.metric("OPERADOR ACTIVO", "Daniel Martinez") 
    c3.metric("ESTADO DEL SISTEMA", "Sincronizado ✅")

    st.markdown("<br>", unsafe_allow_html=True)
    
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
        st.write("""
        - **Facturador:** Permite realizar ventas descontando stock o crear cotizaciones simples.
        - **Inventario:** Pestaña para actualizar precios y cantidades mediante archivos Excel.
        - **Historial:** Registro completo de todas las ventas finalizadas para cierre de caja.
        """)

    st.caption("Ferreenvios & Suministros del Meta | Villavicencio, Colombia")

if __name__ == "__main__":
    main()