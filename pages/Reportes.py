import streamlit as st
import pandas as pd
import os
from datetime import datetime


def mostrar_reporte_utilidades():
    st.title("📈 Reporte de Utilidades y Liquidación")
    # Cambio de etiqueta informativa
    st.info(
        "Este reporte calcula la utilidad exacta restando el Costo de Inversión (compra) y fletes de cada factura."
    )

    # 1. SEGURIDAD DE CONEXIÓN
    if "db" not in st.session_state:
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
        df_detallado["Inversion_Item"] = (
            df_detallado["cantidad"] * df_detallado["costo_proveedor"]
        )

        # Agrupamos por factura
        df_facturas = (
            df_detallado.groupby("Factura")
            .agg(
                {
                    "fecha": "first",
                    "Cliente": "first",
                    "Total_Factura": "first",
                    "Flete": "first",
                    "Inversion_Item": "sum",
                }
            )
            .reset_index()
        )

        # Utilidad Neta = Total - Inversión (Costo) - Flete
        df_facturas["Utilidad_Neta"] = (
            df_facturas["Total_Factura"]
            - df_facturas["Inversion_Item"]
            - df_facturas["Flete"]
        )

        # 3. MÉTRICAS DE ALTO NIVEL (Actualizadas con el nuevo nombre)
        total_v = df_facturas["Total_Factura"].sum()
        total_c = df_facturas["Inversion_Item"].sum()
        total_f = df_facturas["Flete"].sum()
        total_u = df_facturas["Utilidad_Neta"].sum()

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
        df_display = df_display.rename(columns={"Inversion_Item": "Costo Inversión"})

        for col in ["Total_Factura", "Flete", "Costo Inversión", "Utilidad_Neta"]:
            df_display[col] = df_display[col].map("${:,.0f}".format)

        # Mostramos la tabla con el nuevo nombre de columna
        st.dataframe(
            df_display[
                [
                    "fecha",
                    "Factura",
                    "Cliente",
                    "Total_Factura",
                    "Flete",
                    "Costo Inversión",
                    "Utilidad_Neta",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        # 5. EXPORTACIÓN A EXCEL REAL (Celdas y Filas separadas)
        import io

        # Creamos el buffer para el archivo Excel
        output = io.BytesIO()

        # Preparamos el DataFrame de exportación con la fila de totales
        df_export = df_facturas.copy()
        df_export = df_export.rename(columns={"Inversion_Item": "Costo Inversión"})

        # Generar el archivo usando el motor openpyxl
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_export.to_excel(writer, index=False, sheet_name="Utilidades")

            workbook = writer.book
            worksheet = writer.sheets["Utilidades"]

            # Definimos el formato de moneda
            formato_moneda = '"$"#,##0'

            # 🚀 APLICAR FORMATO A LAS COLUMNAS DE DINERO (D, E, F, G)
            # Recorremos desde la fila 2 hasta la última con datos
            for row in range(2, len(df_export) + 2):
                worksheet.cell(row=row, column=4).number_format = (
                    formato_moneda  # Total_Factura
                )
                worksheet.cell(row=row, column=5).number_format = (
                    formato_moneda  # Flete
                )
                worksheet.cell(row=row, column=6).number_format = (
                    formato_moneda  # Costo Inversión
                )
                worksheet.cell(row=row, column=7).number_format = (
                    formato_moneda  # Utilidad_Neta
                )

            # Añadir fila de TOTALES al final del archivo
            # --- FILA DE TOTALES AL FINAL ---
            last_row = len(df_export) + 2
            worksheet.cell(row=last_row, column=1, value="TOTALES GENERALES:")

            # Asignamos valores y aplicamos formato a la fila final
            columnas_totales = {4: total_v, 5: total_f, 6: total_c, 7: total_u}
            for col, valor in columnas_totales.items():
                celda = worksheet.cell(row=last_row, column=col, value=valor)
                celda.number_format = formato_moneda

        st.download_button(
            label="📥 Descargar Reporte de Utilidades (Excel Real)",
            data=output.getvalue(),
            file_name=f"Utilidades_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


def show():
    mostrar_reporte_utilidades()


if __name__ == "__main__":
    show()
