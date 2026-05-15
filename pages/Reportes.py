import streamlit as st
import pandas as pd
import os
from datetime import datetime

def mostrar_reporte_utilidades():
    st.title("📈 Reporte de Utilidades y Liquidación")
    # Cambio de etiqueta informativa
    st.info("Este reporte calcula la utilidad exacta restando el Costo de Inversión (compra) y fletes de cada factura.")

    # 1. SEGURIDAD DE CONEXIÓN
    if 'db' not in st.session_state:
        from modules.database_manager import DatabaseManager
        st.session_state.db = DatabaseManager()

    db = st.session_state.db
    
    try:
        conn = db.conectar()
        # Mantenemos el JOIN original (d.costo_proveedor es el nombre técnico en la DB)
        query = """
        SELECT 
            v.fecha, 
            v.numero_doc as Factura, 
            v.cliente_nombre as Cliente,
            d.cantidad, 
            d.precio_venta, 
            d.costo_proveedor, 
            d.subtotal as Subtotal_Producto,
            v.costo_flete as Flete,
            v.total as Total_Factura
        FROM historial_ventas v
        JOIN detalle_ventas d ON v.numero_doc = d.numero_doc
        WHERE v.tipo_doc = 'FACTURA DE VENTA'
        """
        df_detallado = pd.read_sql(query, conn)
        conn.close()
    except Exception as e:
        st.error(f"Error al consultar datos: {e}")
        return

    if not df_detallado.empty:
        # 2. CÁLCULOS (Usando el nombre técnico para generar la columna de Inversión)
        df_detallado['Inversion_Item'] = df_detallado['cantidad'] * df_detallado['costo_proveedor']
        
        # Agrupamos por factura
        df_facturas = df_detallado.groupby('Factura').agg({
            'fecha': 'first',
            'Cliente': 'first',
            'Total_Factura': 'first',
            'Flete': 'first',
            'Inversion_Item': 'sum'
        }).reset_index()

        # Utilidad Neta = Total - Inversión (Costo) - Flete
        df_facturas['Utilidad_Neta'] = df_facturas['Total_Factura'] - df_facturas['Inversion_Item'] - df_facturas['Flete']

        # 3. MÉTRICAS DE ALTO NIVEL (Actualizadas con el nuevo nombre)
        total_v = df_facturas['Total_Factura'].sum()
        total_c = df_facturas['Inversion_Item'].sum()
        total_f = df_facturas['Flete'].sum()
        total_u = df_facturas['Utilidad_Neta'].sum()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ventas Totales", f"${total_v:,.0f}")
        # Cambio de nombre en el KPI
        c2.metric("Costo Inversión", f"${total_c:,.0f}", delta_color="inverse")
        c3.metric("Gasto Fletes", f"${total_f:,.0f}", delta_color="inverse")
        c4.metric("Utilidad Neta", f"${total_u:,.0f}")

        st.markdown("---")

        # 4. TABLA DE LIQUIDACIÓN DETALLADA
        st.subheader("📋 Detalle para Conciliación con el Socio")
        
        df_display = df_facturas.copy()
        
        # Renombramos la columna para que el usuario vea "Costo Inversión" en la tabla
        df_display = df_display.rename(columns={'Inversion_Item': 'Costo Inversión'})

        for col in ['Total_Factura', 'Flete', 'Costo Inversión', 'Utilidad_Neta']:
            df_display[col] = df_display[col].map('${:,.0f}'.format)

        # Mostramos la tabla con el nuevo nombre de columna
        st.dataframe(
            df_display[['fecha', 'Factura', 'Cliente', 'Total_Factura', 'Flete', 'Costo Inversión', 'Utilidad_Neta']], 
            use_container_width=True,
            hide_index=True
        )
        
        # 5. EXPORTACIÓN
        st.download_button(
            "📥 Descargar Reporte para Liquidación (Excel/CSV)",
            df_facturas.to_csv(index=False).encode('utf-8'),
            f"reporte_utilidades_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            use_container_width=True
        )
    else:
        st.warning("Aún no hay Facturas de Venta procesadas con el sistema de Costo Inversión.")

def show():
    mostrar_reporte_utilidades()

if __name__ == "__main__":
    show()