import streamlit as st
import pymongo
from datetime import datetime
import os
import io
import base64
from bson import Binary
from bson.binary import Binary
import tempfile
import pandas as pd
from pathlib import Path
import glob

# ... (código anterior igual hasta las funciones de procesamiento)

# NUEVA FUNCIÓN: Procesamiento masivo de archivos
def procesar_lote_archivos(db, directorio_base, archivo_metadatos=None):
    """
    Procesa múltiples archivos de forma masiva
    """
    try:
        contador = 0
        errores = []
        
        # Si hay archivo de metadatos
        if archivo_metadatos:
            df_metadatos = pd.read_csv(archivo_metadatos)
            st.info(f"📊 Cargados {len(df_metadatos)} registros de metadatos")
        
        # Buscar archivos recursivamente
        patrones_archivos = ['*.pdf', '*.docx', '*.doc']
        archivos_encontrados = []
        
        for patron in patrones_archivos:
            archivos_encontrados.extend(glob.glob(f"{directorio_base}/**/{patron}", recursive=True))
        
        st.info(f"🔍 Encontrados {len(archivos_encontrados)} archivos para procesar")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, ruta_archivo in enumerate(archivos_encontrados):
            # Actualizar progreso
            porcentaje = (i + 1) / len(archivos_encontrados)
            progress_bar.progress(porcentaje)
            status_text.text(f"Procesando {i+1}/{len(archivos_encontrados)}: {os.path.basename(ruta_archivo)}")
            
            try:
                # Extraer CI del nombre del archivo o carpeta
                ci = extraer_ci_desde_ruta(ruta_archivo)
                
                # Buscar metadatos si existen
                metadatos = buscar_metadatos(ci, df_metadatos if archivo_metadatos else None)
                
                # Procesar archivo
                with open(ruta_archivo, 'rb') as archivo:
                    contenido_binario = Binary(archivo.read())
                
                # Determinar tipo
                extension = Path(ruta_archivo).suffix.lower()
                tipo = 'pdf' if extension == '.pdf' else 'word'
                
                documento = {
                    "titulo": metadatos.get('titulo', Path(ruta_archivo).stem),
                    "descripcion": metadatos.get('descripcion', 'Documento del empleado'),
                    "categoria": metadatos.get('categoria', 'Recursos Humanos'),
                    "autor": metadatos.get('autor', 'Sistema'),
                    "ci": ci,
                    "version": "1.0",
                    "tags": metadatos.get('tags', ['empleado', 'documentación']),
                    "prioridad": "Media",
                    "tipo": tipo,
                    "nombre_archivo": os.path.basename(ruta_archivo),
                    "contenido_binario": contenido_binario,
                    "tamaño_bytes": len(contenido_binario),
                    "fecha_creacion": datetime.utcnow(),
                    "fecha_actualizacion": datetime.utcnow(),
                    "ruta_origen": ruta_archivo
                }
                
                # Insertar en la base de datos
                db.documentos.insert_one(documento)
                contador += 1
                
            except Exception as e:
                errores.append(f"Error en {ruta_archivo}: {str(e)}")
        
        progress_bar.empty()
        status_text.empty()
        
        return contador, errores
        
    except Exception as e:
        return 0, [f"Error general: {str(e)}"]

def extraer_ci_desde_ruta(ruta_archivo):
    """
    Intenta extraer el CI del nombre del archivo o estructura de carpetas
    """
    # Ejemplo: /ruta/1234567/documento.pdf -> extraer 1234567
    partes_ruta = ruta_archivo.split(os.sep)
    
    # Buscar números que parezcan CI (entre 6-10 dígitos)
    for parte in partes_ruta:
        # Remover extensiones y buscar números
        parte_limpia = ''.join(filter(str.isdigit, parte))
        if 6 <= len(parte_limpia) <= 10:
            return parte_limpia
    
    # Si no encuentra, usar el nombre del archivo sin extensión
    return Path(ruta_archivo).stem

def buscar_metadatos(ci, df_metadatos):
    """
    Busca metadatos en el DataFrame basado en el CI
    """
    if df_metadatos is not None and 'ci' in df_metadatos.columns:
        resultado = df_metadatos[df_metadatos['ci'] == ci]
        if not resultado.empty:
            return resultado.iloc[0].to_dict()
    
    return {}

# ... (código anterior igual hasta después de la conexión a MongoDB)

if mongo_uri:
    db, connected = connect_mongodb(mongo_uri)
    
    if connected:
        st.success("🚀 Conectado a MongoDB Cloud!")
        
        # NUEVA PESTAÑA PARA CARGA MASIVA
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📝 Texto Simple", "📄 Subir PDF", "📝 Subir Word", 
            "📂 Todos los Documentos", "🚀 Carga Masiva"
        ])
        
        # ... (pestañas anteriores iguales)
        
        # --- NUEVA PESTAÑA 5: CARGA MASIVA ---
        with tab5:
            st.header("🚀 Carga Masiva de Documentos")
            st.warning("⚠️ Esta función es para procesar grandes volúmenes de archivos")
            
            with st.expander("📋 Instrucciones para la carga masiva"):
                st.markdown("""
                1. **Preparar estructura de carpetas**: 
                   - Organiza los archivos por empleado (carpetas con CI como nombre)
                   - Ej: `/documentos/1234567/contrato.pdf`
                
                2. **Archivo de metadatos (opcional)**:
                   - CSV con columnas: ci, titulo, autor, categoria, tags
                   - Ej: `1234567,Contrato de trabajo,Juan Pérez,Recursos Humanos,"contrato,empleado"`
                
                3. **Tipos de archivo soportados**: PDF, DOC, DOCX
                """)
            
            col1, col2 = st.columns(2)
            
            with col1:
                directorio_base = st.text_input(
                    "Directorio base de archivos",
                    placeholder="C:/documentos/empleados o /home/usuario/documentos",
                    help="Ruta donde están todas las carpetas de empleados"
                )
            
            with col2:
                archivo_metadatos = st.file_uploader(
                    "Archivo de metadatos (CSV opcional)",
                    type=['csv'],
                    help="CSV con CI, título, autor, categoría, tags"
                )
            
            if st.button("🚀 Iniciar Procesamiento Masivo", type="primary"):
                if not directorio_base or not os.path.exists(directorio_base):
                    st.error("❌ El directorio base no existe o no es válido")
                else:
                    with st.spinner("Procesando archivos... Esto puede tomar varios minutos"):
                        total_procesados, errores = procesar_lote_archivos(
                            db, directorio_base, archivo_metadatos
                        )
                        
                        st.success(f"✅ Procesados {total_procesados} archivos exitosamente")
                        
                        if errores:
                            st.error("❌ Se encontraron algunos errores:")
                            with st.expander("Ver detalles de errores"):
                                for error in errores[:10]:  # Mostrar solo primeros 10
                                    st.write(f"- {error}")
                            
                            if len(errores) > 10:
                                st.info(f"... y {len(errores) - 10} errores más")
            
            # Estadísticas de la base de datos
            st.markdown("---")
            st.subheader("📊 Estadísticas de la Base de Datos")
            
            try:
                total_documentos = db.documentos.count_documents({})
                documentos_por_tipo = db.documentos.aggregate([
                    {"$group": {"_id": "$tipo", "count": {"$sum": 1}}}
                ])
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Documentos", total_documentos)
                
                with col2:
                    st.metric("Documentos PDF", 
                             db.documentos.count_documents({"tipo": "pdf"}))
                
                with col3:
                    st.metric("Documentos Word", 
                             db.documentos.count_documents({"tipo": "word"}))
                
            except Exception as e:
                st.error(f"Error obteniendo estadísticas: {e}")

# ... (resto del código igual)
