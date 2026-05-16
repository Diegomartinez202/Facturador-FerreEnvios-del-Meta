import streamlit as st
import config  # Importamos el archivo que creaste en la raíz


def show():
    st.title("⚙️ Configuración del Sistema")

    with st.expander("🏢 Datos de la Empresa (Emisor)", expanded=True):
        col1, col2 = st.columns(2)
        nombre = col1.text_input("Razón Social", value=config.EMISOR["nombre"])
        nit = col2.text_input("NIT (Sin DV)", value=config.EMISOR["nit"])

    with st.expander("📄 Resolución de Facturación DIAN", expanded=True):
        st.info("Estos datos son entregados por la DIAN en el formulario 1876")
        res = st.text_input("Número de Resolución", value=config.EMISOR["resolucion"])
        prefijo = st.text_input("Prefijo Autorizado", value=config.EMISOR["prefijo"])

        c1, c2 = st.columns(2)
        desde = c1.number_input("Rango Desde", value=config.EMISOR["rango_desde"])
        hasta = c2.number_input("Rango Hasta", value=config.EMISOR["rango_hasta"])

        clave = st.text_input(
            "Clave Técnica", value=config.EMISOR["clave_tecnica"], type="password"
        )

    if st.button("💾 Guardar Configuración"):
        # Aquí podrías guardar estos datos en una tabla 'config' de tu base de datos
        # para que los cambios sean permanentes.
        st.success("Configuración actualizada correctamente.")
        st.warning("Nota: Para persistir estos cambios, debemos vincularlos a la DB.")


if __name__ == "__main__":
    show()
