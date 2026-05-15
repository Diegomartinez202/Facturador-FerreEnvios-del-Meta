import streamlit as st
import pandas as pd
import sqlite3
import os

def sincronizar_base_de_datos(df_editado):
    import sqlite3
    # USAMOS LA RUTA QUE YA TIENE EL OBJETO DB INICIALIZADO
    db_path = st.session_state.db.db_path 
    
    try:
        with sqlite3.connect(db_path, timeout=10) as conn:
            # Forzamos nombres de columnas en minúsculas para la base de datos
            df_listo = df_editado.copy()
            df_listo.columns = [c.lower() for c in df_listo.columns]
            
            # El orden debe ser exacto al de tu tabla SQL
            columnas_db = [
                'codigo', 'descripcion', 'cantidad', 'precio', 
                'categoria', 'costo_proveedor', 'tarifa_iva', 
                'codigo_unspsc', 'unidad_medida'
            ]
            # Aseguramos que existan todas las columnas antes de guardar
            for col in columnas_db:
                if col not in df_listo.columns:
                    df_listo[col] = 0 if 'precio' in col or 'costo' in col else 'N/A'
            
            df_listo = df_listo[columnas_db]
            
            # GUARDADO REAL
            df_listo.to_sql('productos', conn, if_exists='replace', index=False)
            conn.commit()
        return True
    except Exception as e:
        st.error(f"❌ Error al escribir en DB: {e}")
        return False

def show():
    st.header("📦 Gestión de Inventario y Disponibilidad")
    
    
    orden_maestro = [
        'codigo', 'descripcion', 'cantidad', 'precio', 
        'categoria', 'costo_proveedor', 'tarifa_iva', 
        'codigo_unspsc', 'unidad_medida'
    ]
    
    config_visual_maestra = {
        "codigo": st.column_config.TextColumn("Cód", width="small"),
        "descripcion": st.column_config.TextColumn("Descripción del Producto", width="large"),
        "cantidad": st.column_config.NumberColumn("Stock Disponible", format="%d", width="medium"), # <-- Nombre claro
        "precio": st.column_config.NumberColumn("Precio Venta", format="$%d", width="medium"),
        "categoria": st.column_config.TextColumn("Categoría", width="medium"),
        "costo_proveedor": st.column_config.NumberColumn("Costo Inversión", format="$%d", width="medium"),
        "tarifa_iva": st.column_config.NumberColumn("IVA %", format="%d%%", width="small"),
        "codigo_unspsc": st.column_config.TextColumn("Cód. UNSPSC", width="medium"),
        "unidad_medida": st.column_config.TextColumn("Unidad de Medida", width="medium"), # <-- Nombre restaurado
        "Subtotal": st.column_config.NumberColumn("Subtotal", format="$%d"),
        "Valor IVA": st.column_config.NumberColumn("IVA Valor", format="$%d")
    }
    
    # 1. Pestañas organizadas (Unificadas para evitar confusiones)
    tab_lista, tab_carga, tab_editor = st.tabs([
        "📋 Lista de Precios", 
        "📥 Cargar Excel/Word", 
        "🛠 Editor Maestro"
    ])
    
    # Obtenemos los datos una sola vez para ambas pestañas
    df_base = st.session_state.db.obtener_productos()
    
    # --- PESTAÑA 1: LISTA DE PRECIOS ---
    with tab_lista:
        st.subheader("Consulta de Productos")
        # Obtenemos productos de la DB
        df_prods = st.session_state.db.obtener_productos()
        
        if not df_prods.empty:
            df_view = df_prods.copy()
            
            # --- LÓGICA DE IVA SEGÚN SELECCIÓN ---
            aplicar_iva = st.session_state.get('liquidar_iva', False) 
            
            if aplicar_iva:
                # Si está activado: Desglosamos IVA basándonos en la tarifa de la DB
                df_view['Tarifa'] = df_view.get('tarifa_iva', 19.0).fillna(19.0)
                df_view['Subtotal'] = df_view['precio'] / (1 + (df_view['Tarifa']/100))
                df_view['Valor IVA'] = df_view['precio'] - df_view['Subtotal']
                
                cols_a_mostrar = [
                    'codigo', 'descripcion', 'cantidad', 'precio', 
                    'Subtotal', 'Valor IVA', 'categoria', 
                    'costo_proveedor', 'tarifa_iva', 'codigo_unspsc', 'unidad_medida'
                ]
                
            else:
                cols_mostrar = orden_maestro

            # --- INTERFAZ DE BÚSQUEDA ---
            busqueda = st.text_input("🔍 Buscar por descripción, código o categoría", key="bus_inv_final")
            
            mask = (
                df_view['descripcion'].str.contains(busqueda, case=False) | 
                df_view['codigo'].astype(str).str.contains(busqueda) |
                df_view['categoria'].str.contains(busqueda, case=False)
            )
            
            cols_finales = [c for c in cols_mostrar if c in df_view.columns]
            # Aplicamos filtro y orden de columnas
            df_display = df_view[mask][cols_mostrar].copy()
            
            label_precio = "Precio Final (COP)" if not aplicar_iva else "Precio Total (Incluye IVA)"
            
            # --- RENDERIZADO PROFESIONAL CON FORMATO COP Y ESTILOS ---
            config_visual_maestra["precio"] = st.column_config.NumberColumn(label_precio, format="$%d", width="medium")
            
            # Formateo de encabezado de precio
            label_precio = "Total Neto (Sin IVA)" if not aplicar_iva else "Precio Total (Incluye IVA)"
            df_display.rename(columns={'precio': label_precio}, inplace=True)

            # --- RENDERIZADO CON FORMATO COP ---
            formato_moneda = {
                "Subtotal": "${:,.0f}",
                "Valor IVA": "${:,.0f}",
                label_precio: "${:,.0f}"
            }
            
            st.dataframe(
                df_display.style.applymap(
                    lambda x: 'background-color: #ffcccc' if x <= 5 else '', 
                    subset=['cantidad']
                ).format({k: v for k, v in formato_moneda.items() if k in df_display.columns}),
                column_config=config_visual_maestra,
                use_container_width=True, 
                hide_index=True
            )
            
            estado_iva = "ACTIVA ✅" if aplicar_iva else "DESACTIVADA ❌"
            st.info("💡 Nota: El desglose de IVA y Subtotal detallado en el PDF solo se activa al procesar la factura con liquidación de impuestos.")
            st.caption(f"💡 Liquidación de IVA: {estado_iva}. Los productos en rojo tienen stock crítico (5 o menos).")
        else:
            st.warning("El inventario está vacío.")

    with tab_carga:
        # 1. Mensaje informativo actualizado
        st.info("Requisito: El archivo debe tener las columnas: **Código, Descripción, Categoría, Cantidad, Precio**")
        archivo = st.file_uploader("Subir lista de precios (Excel o CSV)", type=["xlsx", "csv"])
        
        if archivo:
            try:
                # Lectura del archivo
                df_nuevo = pd.read_excel(archivo) if archivo.name.endswith('xlsx') else pd.read_csv(archivo)
                
                # Limpiamos nombres de columnas
                df_nuevo.columns = [c.strip().capitalize() for c in df_nuevo.columns]
                
                # Definimos las 5 columnas exigidas
                columnas_esperadas = ['Código', 'Descripción', 'Categoría', 'Cantidad', 'Precio']
                
                if all(col in df_nuevo.columns for col in columnas_esperadas):
                    st.write("### Vista previa de datos detectados:")
                    st.dataframe(df_nuevo.head())

                    if st.button("🚀 Actualizar Base de Datos Ahora"):
                        with st.spinner("Sincronizando inventario..."):
                            # --- MEJORA: Limpieza y Reordenamiento ---
                            df_nuevo['Cantidad'] = pd.to_numeric(df_nuevo['Cantidad'], errors='coerce').fillna(0)
                            df_nuevo['Precio'] = pd.to_numeric(df_nuevo['Precio'], errors='coerce').fillna(0)
                            
                            # Forzamos el orden antes de enviarlo al proceso de importación
                            # Esto asegura que DatabaseManager reciba las columnas en el orden legal de la DB
                            df_final = df_nuevo[['Código', 'Descripción', 'Cantidad', 'Precio', 'Categoría']]
                            
                            st.session_state.db.importar_desde_excel(df_final)
                            
                            st.success("¡Inventario actualizado correctamente!")
                            st.balloons()
                            st.rerun() 
                else:
                    faltantes = [c for c in columnas_esperadas if c not in df_nuevo.columns]
                    st.error(f"Error: Faltan las siguientes columnas: {faltantes}")
            
            except Exception as e:
                st.error(f"Error crítico: {e}")
            
    # --- MEJORA: EL EDITOR DINÁMICO DENTRO DE SU PESTAÑA ---
    with tab_editor:
        st.subheader("Editor Maestro de Productos")
        st.info("Cambia precios, costos o nombres directamente. Usa la última fila para agregar nuevos.")
        
        df_para_editar = st.session_state.db.obtener_productos()
        
        if not df_para_editar.empty:
            
            cols_editor = [c for c in orden_maestro if c in df_para_editar.columns]
            df_para_editar = df_para_editar[cols_editor]
            
            # INTEGRACIÓN: Editor dinámico con configuración de columnas moneda
            edited_df = st.data_editor(
                df_para_editar,
                column_config=config_visual_maestra, # Si usas la variable, verifica la coma
                num_rows="dynamic", 
                use_container_width=True,
                key="editor_maestro_ferreenvios", # <-- VERIFICA ESTA COMA
                hide_index=True
            )
            
            # Tu lógica original de guardado y sincronización
            if st.button("💾 Guardar Cambios Permanentes"):
                from pages.Inventario import sincronizar_base_de_datos
                
                with st.spinner("Sincronizando con el archivo de base de datos..."):
                    # Llamada a tu función de sincronización (asegúrate que acepte la columna 'costo')
                    if st.session_state.db.actualizar_inventario_completo(edited_df):
                        st.success("✅ ¡Base de datos actualizada físicamente! Los cambios persistirán.")
                        st.balloons()
                        # Forzamos recarga para que el Panel de Control vea los nuevos precios
                        st.rerun() 
                    else:
                        st.error("❌ No se pudo escribir en el archivo. Verifica que no esté abierto en otro programa.")

# --- EJECUCIÓN PRINCIPAL (Versión Final FerreEnvios) ---
if __name__ == "__main__":
    # --- INICIALIZACIÓN CRÍTICA ---
    # Garantiza que 'db' exista en la memoria de la página antes de mostrar nada
    if "db" not in st.session_state:
        try:
            # 1. Intentamos importar desde tu archivo real: database_manager.py
            try:
                from modules.database_manager import DatabaseManager as DBClass
            except ImportError:
                # 2. Plan B: Si alguna vez cambias el nombre a database.py
                from modules.database import DatabaseManager as DBClass
            
            # 3. Inicializamos apuntando a la base de datos oficial
            st.session_state.db = DBClass(db_path="data/ferreteria_final.db")
            
        except ModuleNotFoundError:
            st.error("❌ **Error Crítico:** No se encontró el archivo de base de datos en `modules/`.")
            st.info("Verifica que el archivo se llame `database_manager.py` y exista `modules/__init__.py`.")
        except Exception as e:
            st.error(f"❌ **Error al inicializar el sistema:** {e}")

    # --- MEJORA INTEGRADA: AGREGAR COLUMNA COSTO ---
    # Solo intentamos la migración si la base de datos se inicializó correctamente
    if "db" in st.session_state:
        try:
            # Abrimos conexión y creamos el cursor para la migración
            conn = st.session_state.db.conectar()
            cursor = conn.cursor()
            
            # Intentamos agregar la columna Costo al inventario
            cursor.execute("ALTER TABLE productos ADD COLUMN costo REAL DEFAULT 0.0")
            
            # Guardamos cambios y cerramos
            conn.commit()
            conn.close()
        except sqlite3.OperationalError:
            # Si la columna ya existe, SQLite lanza este error y simplemente lo ignoramos
            pass 
        except Exception as e:
            # Si ocurre un error diferente, lo capturamos para no bloquear la app
            st.warning(f"Nota técnica: Verificación de estructura DB: {e}")

    # Ejecutamos la interfaz solo si la inicialización terminó (con éxito o error controlado)
    show()