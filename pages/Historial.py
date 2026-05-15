import streamlit as st
import pandas as pd
from datetime import datetime

def show():
    st.header("📊 Historial de Ventas y Recaudo")

    # Obtener historial de la base de datos
    conn = st.session_state.db.conectar()
    df_ventas = pd.read_sql_query("SELECT * FROM historial_ventas ORDER BY id DESC", conn)
    conn.close()

    if not df_ventas.empty:
        # Filtros rápidos
        mes_actual = datetime.now().strftime('%Y-%m')
        # Filtramos primero por mes
        ventas_mes = df_ventas[df_ventas['fecha'].str.contains(mes_actual)]

        # MEJORA: Solo sumamos dinero de FACTURAS para el recuadro de arriba
        facturas_reales = df_ventas[df_ventas['tipo_doc'] == "FACTURA DE VENTA"]
        total_mes = facturas_reales['total'].sum()

        # KPIs Visuales
        c1, c2, c3 = st.columns(3)
        c1.metric("💵 Recaudo Mes Actual", f"${total_mes:,.0f} COP")
        c2.metric("🧾 Facturas Emitidas", len(ventas_mes))
        c3.metric("📈 Promedio por Venta", f"${(total_mes/len(ventas_mes)) if len(ventas_mes)>0 else 0:,.0f} COP")

        st.markdown("---")
        st.subheader("📋 Listado Detallado")
        
        # Buscador de facturas
        busqueda = st.text_input("🔍 Buscar por nombre de cliente o número de factura")
        if busqueda:
            df_ventas = df_ventas[
                df_ventas['cliente_nombre'].str.contains(busqueda, case=False) | 
                df_ventas['numero_doc'].str.contains(busqueda)
            ]

        # Tabla profesional
        st.dataframe(
            df_ventas,
            column_config={
                "id": "ID",
                "fecha": "Fecha de Venta",
                "tipo_doc": "Tipo",
                "numero_doc": "N° Doc",
                "cliente_nombre": "Cliente",
                "total": st.column_config.NumberColumn("Total Venta", format="$%d")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Aún no hay ventas registradas en el historial.")

# Esto asegura que la página se cargue correctamente en el sistema multipágina
if __name__ == "__main__":
    show()