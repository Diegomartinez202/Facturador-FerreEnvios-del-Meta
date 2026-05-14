import streamlit as st
import pandas as pd

def show():
    st.header("📦 Gestión de Inventario y Disponibilidad")
    
    # Pestañas para organizar (Tu estructura original intacta)
    tab_lista, tab_carga = st.tabs(["📋 Lista de Precios", "📥 Cargar Excel/Word"])
    
    with tab_lista:
        st.subheader("Consulta de Productos")
        # Acceso al microservicio de base de datos
        df_prods = st.session_state.db.obtener_productos()
        
        if not df_prods.empty:
            # Buscador en tiempo real
            busqueda = st.text_input("🔍 Buscar por descripción o código")
            # Filtro dinámico
            mask = df_prods['descripcion'].str.contains(busqueda, case=False) | df_prods['codigo'].astype(str).str.contains(busqueda)
            
            # Formatear visualmente el precio para la tabla
            df_display = df_prods[mask].copy()
            
            # Mostrar tabla con alerta de disponibilidad (Tu lógica original intacta)
            st.dataframe(
                df_display.style.applymap(
                    lambda x: 'background-color: #ffcccc' if x <= 5 else '', 
                    subset=['cantidad']
                ).format({"precio": "${:,.0f}"}), # Agregamos formato de moneda visual
                use_container_width=True,
                hide_index=True
            )
            st.caption("💡 Los productos en rojo tienen disponibilidad crítica (5 o menos unidades).")
        else:
            st.warning("El inventario está vacío. Por favor, cargue un archivo en la siguiente pestaña.")

    with tab_carga:
        st.info("El archivo debe tener las columnas: Código, Descripción, Cantidad, Precio")
        archivo = st.file_uploader("Subir lista de precios", type=["xlsx", "csv"])
        
        if archivo:
            try:
                # Lectura flexible
                if archivo.name.endswith('xlsx'):
                    df_nuevo = pd.read_excel(archivo)
                else:
                    df_nuevo = pd.read_csv(archivo)
                
                st.write("### Vista previa del archivo detectado:")
                st.dataframe(df_nuevo.head())
                
                # --- MEJORA DE COMPATIBILIDAD SIN ELIMINAR TU LÓGICA ---
                # Esto asegura que si las columnas vienen con espacios o mayúsculas diferentes, el sistema las entienda
                df_nuevo.columns = [c.strip().capitalize() for c in df_nuevo.columns]
                columnas_esperadas = ['Código', 'Descripción', 'Cantidad', 'Precio']
                
                # Verificar si las columnas coinciden con tu lista de precios
                if all(col in df_nuevo.columns for col in columnas_esperadas):
                    if st.button("🚀 Actualizar Base de Datos"):
                        with st.spinner("Procesando lista de precios..."):
                            # Llamada al microservicio de base de datos
                            st.session_state.db.importar_desde_excel(df_nuevo)
                            st.success("¡Inventario actualizado con éxito!")
                            st.balloons()
                            st.rerun()
                else:
                    st.error(f"Error: El archivo debe contener exactamente las columnas: {columnas_esperadas}")
                    st.write("Columnas detectadas en tu archivo:", list(df_nuevo.columns))
            
            except Exception as e:
                st.error(f"No se pudo leer el archivo: {e}")

# Ejecución de la página
if __name__ == "__main__":
    show()