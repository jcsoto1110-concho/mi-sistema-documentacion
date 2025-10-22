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
import time
from pathlib import Path
import re
from pathlib import Path
import os
import sys
import platform
import zipfile  # Añadir esta importación

# Configuración de la página
st.set_page_config(
    page_title="Sistema de Gestión Documental SCO",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar session_state para control de cache
if 'last_delete_time' not in st.session_state:
    st.session_state.last_delete_time = datetime.now().timestamp()
if 'refresh_counter' not in st.session_state:
    st.session_state.refresh_counter = 0
if 'db_connection' not in st.session_state:
    st.session_state.db_connection = None
if 'db_connected' not in st.session_state:
    st.session_state.db_connected = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = "No conectado"
if 'mongo_username' not in st.session_state:
    st.session_state.mongo_username = "Desconocido"
if 'df_metadatos_local' not in st.session_state:
    st.session_state.df_metadatos_local = None
if 'df_metadatos_masiva' not in st.session_state:
    st.session_state.df_metadatos_masiva = None
if 'archivos_zip_procesados' not in st.session_state:
    st.session_state.archivos_zip_procesados = {}

# CSS personalizado para mejorar la apariencia
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .subheader {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        border-left: 4px solid #1f77b4;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .success-message {
        background-color: #d4edda;
        color: #155724;
        padding: 12px;
        border-radius: 5px;
        border-left: 4px solid #28a745;
    }
    .warning-message {
        background-color: #fff3cd;
        color: #856404;
        padding: 12px;
        border-radius: 5px;
        border-left: 4px solid #ffc107;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 5px 5px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .document-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 5px solid #1f77b4;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    .document-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    .compact-metadata {
        font-size: 0.85rem;
        color: #666;
    }
    .tag {
        background-color: #e0e0e0;
        padding: 2px 8px;
        border-radius: 10px;
        margin: 2px;
        display: inline-block;
        font-size: 0.75rem;
    }
    .user-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.9rem;
        display: inline-block;
        margin-bottom: 10px;
    }
    .zip-info {
        background-color: #e3f2fd;
        padding: 10px;
        border-radius: 5px;
        border-left: 4px solid #2196f3;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# Título principal mejorado
st.markdown('<h1 class="main-header">📚 Sistema de Gestión Documental</h1>', unsafe_allow_html=True)
st.markdown('<p class="subheader">Gestión centralizada de documentos con búsqueda avanzada y control de versiones</p>', unsafe_allow_html=True)

# Función de conexión mejorada
def connect_mongodb(uri):
    try:
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client.documentation_db
        
        # Extraer nombre de usuario de la URI
        username = "Desconocido"
        try:
            if "mongodb+srv://" in uri:
                user_part = uri.split("mongodb+srv://")[1].split(":")[0]
                if "@" in user_part:
                    username = user_part.split("@")[0]
                else:
                    username = user_part
            elif "mongodb://" in uri:
                user_part = uri.split("mongodb://")[1].split(":")[0]
                if "@" in user_part:
                    username = user_part.split("@")[0]
                else:
                    username = user_part
        except:
            username = "Usuario BD"
        
        return db, True, "Conexión exitosa", username
    except pymongo.errors.ServerSelectionTimeoutError:
        return None, False, "Error: Timeout de conexión", "Desconocido"
    except pymongo.errors.ConnectionFailure:
        return None, False, "Error: No se pudo conectar al servidor", "Desconocido"
    except Exception as e:
        return None, False, f"Error: {str(e)}", "Desconocido"

# --- FUNCIONES PARA CARGA LOCAL CON ZIP ---

def extraer_ci_desde_nombre(nombre_archivo, patron_busqueda):
    """
    Extrae el CI del nombre del archivo según el patrón especificado
    """
    try:
        nombre_sin_extension = Path(nombre_archivo).stem
        
        if patron_busqueda == "CI al inicio":
            match = re.match(r'^(\d{8,10})', nombre_sin_extension)
            if match:
                return match.group(1)
        
        elif patron_busqueda == "CI en cualquier parte":
            matches = re.findall(r'\d{8,10}', nombre_sin_extension)
            if matches:
                return matches[0]
        
        elif patron_busqueda == "CI específico en nombre":
            patterns = [
                r'CI[_\-\s]*(\d{8,10})',
                r'(\d{8,10})[_\-\s]',
                r'cedula[_\-\s]*(\d{8,10})',
                r'identificacion[_\-\s]*(\d{8,10})'
            ]
            for pattern in patterns:
                match = re.search(pattern, nombre_sin_extension, re.IGNORECASE)
                if match:
                    return match.group(1)
        
        return None
    except Exception as e:
        return None

def extraer_archivos_desde_zip(archivo_zip):
    """
    Extrae todos los archivos de un ZIP y los devuelve en memoria
    """
    try:
        archivos_extraidos = {}
        
        with zipfile.ZipFile(archivo_zip, 'r') as zip_ref:
            # Obtener lista de archivos
            lista_archivos = zip_ref.namelist()
            
            for archivo_nombre in lista_archivos:
                # Ignorar carpetas
                if not archivo_nombre.endswith('/'):
                    # Leer archivo en memoria
                    with zip_ref.open(archivo_nombre) as archivo:
                        contenido = archivo.read()
                        
                        # Crear objeto file-like en memoria
                        archivo_memoria = io.BytesIO(contenido)
                        archivo_memoria.name = Path(archivo_nombre).name
                        
                        archivos_extraidos[archivo_nombre] = archivo_memoria
        
        return archivos_extraidos, None
        
    except Exception as e:
        return None, f"Error extrayendo ZIP: {str(e)}"

def buscar_archivos_en_zip(archivos_zip, tipos_archivo, max_documentos):
    """
    Busca archivos en el ZIP extraído según los tipos especificados
    """
    try:
        archivos_encontrados = []
        
        for nombre_archivo, archivo_memoria in archivos_zip.items():
            extension = Path(nombre_archivo).suffix.lower()
            if extension in tipos_archivo:
                archivos_encontrados.append((nombre_archivo, archivo_memoria))
            
            if len(archivos_encontrados) >= max_documentos:
                break
        
        return archivos_encontrados
    
    except Exception as e:
        st.error(f"❌ Error buscando archivos en ZIP: {str(e)}")
        return []

def procesar_archivo_local_zip(archivo_nombre, archivo_memoria, ci, metadatos_ci, config):
    """
    Procesa un archivo desde ZIP para la carga local
    """
    try:
        # Determinar tipo de archivo
        extension = Path(archivo_nombre).suffix.lower()
        if extension == '.pdf':
            tipo_archivo = 'pdf'
        elif extension in ['.docx', '.doc']:
            tipo_archivo = 'word'
        elif extension in ['.jpg', '.jpeg', '.png']:
            tipo_archivo = 'imagen'
        elif extension == '.txt':
            tipo_archivo = 'texto'
        else:
            tipo_archivo = 'documento'
        
        # Generar título automático si no está en metadatos
        titulo = metadatos_ci.get('titulo')
        if not titulo:
            nombre_archivo = Path(archivo_nombre).stem
            titulo = f"{nombre_archivo} - {metadatos_ci['nombre']}"
        
        # Procesar etiquetas
        etiquetas = []
        if 'etiquetas' in metadatos_ci and pd.notna(metadatos_ci['etiquetas']):
            etiquetas = [tag.strip() for tag in str(metadatos_ci['etiquetas']).split(',')]
        
        # Agregar etiquetas automáticas
        etiquetas.extend([str(ci), 'carga_local', 'sistema_archivos', tipo_archivo])
        
        # Obtener información del archivo
        tamaño_bytes = len(archivo_memoria.getvalue())
        fecha_modificacion = datetime.utcnow()
        
        # Crear documento (sin contenido binario, solo metadatos)
        documento = {
            "titulo": titulo,
            "categoria": metadatos_ci.get('categoria', 'Personal'),
            "autor": metadatos_ci.get('autor', metadatos_ci['nombre']),
            "ci": str(ci),
            "nombre_completo": metadatos_ci['nombre'],
            "version": metadatos_ci.get('version', '1.0'),
            "tags": etiquetas,
            "prioridad": metadatos_ci.get('prioridad', 'Media'),
            "tipo": tipo_archivo,
            "nombre_archivo": Path(archivo_nombre).name,
            "ruta_local": f"zip://{archivo_nombre}",
            "tamaño_bytes": tamaño_bytes,
            "fecha_modificacion_local": fecha_modificacion,
            "fecha_creacion": datetime.utcnow(),
            "fecha_actualizacion": datetime.utcnow(),
            "usuario_creacion": st.session_state.mongo_username,
            "usuario_actualizacion": st.session_state.mongo_username,
            "procesado_local": True,
            "lote_carga": config.get('lote_id'),
            "almacenamiento": "zip"  # Indica que el archivo viene de ZIP
        }
        
        return documento, None
        
    except Exception as e:
        return None, f"Error procesando {archivo_nombre}: {str(e)}"

def procesar_carga_local_zip(db, archivos_zip, df_metadatos, tipos_archivo, max_documentos, 
                            tamaño_lote, patron_busqueda, sobrescribir_existentes):
    """
    Función principal para procesar carga masiva local desde ZIP
    """
    try:
        # Configuración
        config = {
            'lote_id': f"local_zip_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        
        # Contadores
        total_archivos = 0
        archivos_procesados = 0
        documentos_exitosos = 0
        documentos_fallidos = 0
        documentos_duplicados = 0
        documentos_sin_ci = 0
        cis_encontrados = set()
        
        # Buscar archivos en el ZIP
        st.info("🔍 Buscando archivos en el ZIP...")
        archivos_encontrados = buscar_archivos_en_zip(archivos_zip, tipos_archivo, max_documentos)
        
        if not archivos_encontrados:
            st.warning("⚠️ No se encontraron archivos para procesar en el ZIP")
            return
        
        st.success(f"🎯 Encontrados {len(archivos_encontrados)} archivos en el ZIP")
        
        # Crear mapeo CI -> metadatos para búsqueda rápida
        mapeo_metadatos = {}
        for _, fila in df_metadatos.iterrows():
            ci_str = str(fila['ci']).strip()
            mapeo_metadatos[ci_str] = fila.to_dict()
        
        # Configurar interfaz de progreso
        progress_bar = st.progress(0)
        status_text = st.empty()
        resultados_container = st.container()
        
        # Procesar archivos por lotes
        for i in range(0, len(archivos_encontrados), tamaño_lote):
            lote_actual = archivos_encontrados[i:i + tamaño_lote]
            documentos_a_insertar = []
            
            for archivo_nombre, archivo_memoria in lote_actual:
                # Extraer CI del nombre del archivo
                ci_extraido = extraer_ci_desde_nombre(archivo_nombre, patron_busqueda)
                
                if not ci_extraido:
                    documentos_sin_ci += 1
                    continue
                
                # Buscar metadatos para este CI
                metadatos_ci = mapeo_metadatos.get(ci_extraido)
                if not metadatos_ci:
                    documentos_sin_ci += 1
                    continue
                
                cis_encontrados.add(ci_extraido)
                
                # Verificar duplicados si no se permite sobrescribir
                if not sobrescribir_existentes:
                    existe = db.documentos.count_documents({
                        "nombre_archivo": Path(archivo_nombre).name,
                        "ci": ci_extraido,
                        "almacenamiento": "zip"
                    }) > 0
                    
                    if existe:
                        documentos_duplicados += 1
                        continue
                
                # Procesar archivo
                documento, error = procesar_archivo_local_zip(archivo_nombre, archivo_memoria, ci_extraido, metadatos_ci, config)
                
                if error:
                    documentos_fallidos += 1
                    st.error(error)
                else:
                    documentos_a_insertar.append(documento)
            
            # Insertar lote en MongoDB
            if documentos_a_insertar:
                try:
                    result = db.documentos.insert_many(documentos_a_insertar, ordered=False)
                    documentos_exitosos += len(result.inserted_ids)
                except Exception as e:
                    documentos_fallidos += len(documentos_a_insertar)
                    st.error(f"Error insertando lote: {str(e)}")
            
            archivos_procesados += len(lote_actual)
            
            # Actualizar progreso
            progreso = archivos_procesados / len(archivos_encontrados)
            progress_bar.progress(progreso)
            status_text.text(
                f"📊 Progreso: {archivos_procesados}/{len(archivos_encontrados)} | "
                f"✅ Exitosos: {documentos_exitosos} | "
                f"❌ Fallidos: {documentos_fallidos} | "
                f"⚡ Duplicados: {documentos_duplicados} | "
                f"🔍 Sin CI: {documentos_sin_ci}"
            )
            
            # Pequeña pausa para no sobrecargar
            time.sleep(0.1)
        
        # Mostrar resultados finales
        progress_bar.progress(1.0)
        status_text.text("✅ Procesamiento completado!")
        
        with resultados_container:
            st.markdown("### 📈 Resultados Finales - Carga Local desde ZIP")
            
            # Métricas principales
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Archivos en ZIP", len(archivos_encontrados))
            with col2:
                st.metric("Procesados Exitosos", documentos_exitosos)
            with col3:
                st.metric("Fallidos/Sin CI", documentos_fallidos + documentos_sin_ci)
            with col4:
                st.metric("CIs Encontrados", len(cis_encontrados))
            
            if documentos_exitosos > 0:
                st.success(f"🎉 Carga local desde ZIP completada por {st.session_state.mongo_username}! {documentos_exitosos} documentos procesados exitosamente.")
                st.balloons()
                
                # Mostrar detalles adicionales
                with st.expander("📋 Detalles del procesamiento", expanded=True):
                    col_d1, col_d2, col_d3 = st.columns(3)
                    with col_d1:
                        st.metric("Documentos duplicados", documentos_duplicados)
                    with col_d2:
                        st.metric("Archivos sin CI", documentos_sin_ci)
                    with col_d3:
                        st.metric("Fallidos en procesamiento", documentos_fallidos)
                
                # Actualizar estadísticas
                st.session_state.last_delete_time = datetime.now().timestamp()
            
            if documentos_duplicados > 0:
                st.info(f"💡 {documentos_duplicados} documentos no se procesaron por duplicados. "
                       "Marca 'Sobrescribir documentos existentes' para forzar el reprocesamiento.")
            
            if documentos_sin_ci > 0:
                st.warning(f"⚠️ {documentos_sin_ci} archivos no se procesaron porque no se pudo extraer el CI o no había metadatos. "
                          "Verifica que los nombres de archivo contengan el CI y que el CSV tenga los metadatos correspondientes.")
                
    except Exception as e:
        st.error(f"❌ Error en el procesamiento local desde ZIP: {str(e)}")

# --- FUNCIONES PARA CARGA MASIVA CON ZIP ---

def buscar_archivos_por_ci_zip(archivos_zip, ci, tipos_archivo):
    """Busca archivos para un CI específico en el ZIP"""
    try:
        ci_str = str(ci).strip()
        archivos_ci = []
        
        for archivo_nombre, archivo_memoria in archivos_zip.items():
            # Buscar archivos que contengan el CI en el nombre o path
            if ci_str in archivo_nombre:
                extension = Path(archivo_nombre).suffix.lower()
                if extension in tipos_archivo:
                    archivos_ci.append((archivo_nombre, archivo_memoria))
        
        return archivos_ci
    
    except Exception as e:
        return []

def procesar_archivo_masivo_zip(archivo_nombre, archivo_memoria, ci, metadatos_ci, config):
    """Procesa un archivo individual desde ZIP para la carga masiva"""
    try:
        # Leer contenido binario desde el archivo en memoria
        contenido_binario = Binary(archivo_memoria.getvalue())
        
        # Determinar tipo de archivo
        extension = Path(archivo_nombre).suffix.lower()
        if extension == '.pdf':
            tipo_archivo = 'pdf'
        elif extension in ['.docx', '.doc']:
            tipo_archivo = 'word'
        elif extension in ['.jpg', '.jpeg', '.png']:
            tipo_archivo = 'imagen'
        elif extension == '.txt':
            tipo_archivo = 'texto'
        else:
            tipo_archivo = 'documento'
        
        # Generar título automático si no está en metadatos
        titulo = metadatos_ci.get('titulo')
        if not titulo:
            nombre_archivo = Path(archivo_nombre).stem
            titulo = f"{nombre_archivo} - {metadatos_ci['nombre']}"
        
        # Procesar etiquetas
        etiquetas = []
        if 'etiquetas' in metadatos_ci and pd.notna(metadatos_ci['etiquetas']):
            etiquetas = [tag.strip() for tag in str(metadatos_ci['etiquetas']).split(',')]
        
        # Agregar etiquetas automáticas
        etiquetas.extend([str(ci), 'carga_masiva', 'automático', tipo_archivo, 'zip'])
        
        # Crear documento
        documento = {
            "titulo": titulo,
            "categoria": metadatos_ci.get('categoria', 'Personal'),
            "autor": metadatos_ci.get('autor', metadatos_ci['nombre']),
            "ci": str(ci),
            "nombre_completo": metadatos_ci['nombre'],
            "version": metadatos_ci.get('version', '1.0'),
            "tags": etiquetas,
            "prioridad": metadatos_ci.get('prioridad', 'Media'),
            "tipo": tipo_archivo,
            "nombre_archivo": Path(archivo_nombre).name,
            "contenido_binario": contenido_binario,
            "tamaño_bytes": len(contenido_binario),
            "ruta_original": f"zip://{archivo_nombre}",
            "fecha_creacion": datetime.utcnow(),
            "fecha_actualizacion": datetime.utcnow(),
            "usuario_creacion": st.session_state.mongo_username,
            "usuario_actualizacion": st.session_state.mongo_username,
            "procesado_masivo": True,
            "lote_carga": config.get('lote_id'),
            "almacenamiento": "base_datos"
        }
        
        return documento, None
        
    except Exception as e:
        return None, f"Error procesando {archivo_nombre}: {str(e)}"

def procesar_carga_masiva_ci_zip(db, archivos_zip, df_metadatos, tipos_archivo, max_documentos, 
                               tamaño_lote, sobrescribir_existentes):
    """Función principal para procesar carga masiva por CI desde ZIP"""
    
    try:
        # Configuración
        config = {
            'lote_id': f"masivo_zip_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        
        # Contadores
        total_archivos = 0
        archivos_procesados = 0
        documentos_exitosos = 0
        documentos_fallidos = 0
        documentos_duplicados = 0
        cis_procesados = 0
        
        # Lista para almacenar todos los documentos a procesar
        todos_documentos = []
        
        st.info("🔍 Buscando archivos en ZIP por CI...")
        
        # Buscar archivos para cada CI en el CSV
        for _, fila in df_metadatos.iterrows():
            ci = fila['ci']
            archivos_ci = buscar_archivos_por_ci_zip(archivos_zip, ci, tipos_archivo)
            
            if archivos_ci:
                cis_procesados += 1
                for archivo_nombre, archivo_memoria in archivos_ci:
                    if total_archivos < max_documentos:
                        todos_documentos.append((archivo_nombre, archivo_memoria, ci, fila.to_dict()))
                        total_archivos += 1
                    else:
                        break
            
            if total_archivos >= max_documentos:
                break
        
        if not todos_documentos:
            st.warning("⚠️ No se encontraron archivos para procesar en el ZIP")
            return
        
        st.success(f"🎯 Encontrados {total_archivos} archivos para {cis_procesados} CIs diferentes en el ZIP")
        
        # Configurar interfaz de progreso
        progress_bar = st.progress(0)
        status_text = st.empty()
        resultados_container = st.container()
        
        # Procesar por lotes
        for i in range(0, len(todos_documentos), tamaño_lote):
            lote_actual = todos_documentos[i:i + tamaño_lote]
            documentos_a_insertar = []
            
            for archivo_nombre, archivo_memoria, ci, metadatos in lote_actual:
                # Verificar duplicados si no se permite sobrescribir
                if not sobrescribir_existentes:
                    existe = db.documentos.count_documents({
                        "nombre_archivo": Path(archivo_nombre).name,
                        "ci": str(ci)
                    }) > 0
                    
                    if existe:
                        documentos_duplicados += 1
                        continue
                
                # Procesar archivo
                documento, error = procesar_archivo_masivo_zip(archivo_nombre, archivo_memoria, ci, metadatos, config)
                
                if error:
                    documentos_fallidos += 1
                    st.error(error)
                else:
                    documentos_a_insertar.append(documento)
            
            # Insertar lote en MongoDB
            if documentos_a_insertar:
                try:
                    result = db.documentos.insert_many(documentos_a_insertar, ordered=False)
                    documentos_exitosos += len(result.inserted_ids)
                except Exception as e:
                    documentos_fallidos += len(documentos_a_insertar)
                    st.error(f"Error insertando lote: {str(e)}")
            
            archivos_procesados += len(lote_actual)
            
            # Actualizar progreso
            progreso = archivos_procesados / len(todos_documentos)
            progress_bar.progress(progreso)
            status_text.text(
                f"📊 Progreso: {archivos_procesados}/{len(todos_documentos)} | "
                f"✅ Exitosos: {documentos_exitosos} | "
                f"❌ Fallidos: {documentos_fallidos} | "
                f"⚡ Duplicados: {documentos_duplicados}"
            )
            
            # Pequeña pausa para no sobrecargar
            time.sleep(0.1)
        
        # Mostrar resultados finales
        progress_bar.progress(1.0)
        status_text.text("✅ Procesamiento completado!")
        
        with resultados_container:
            st.markdown("### 📈 Resultados Finales - Carga Masiva desde ZIP")
            
            # Métricas principales
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Archivos Encontrados", len(todos_documentos))
            with col2:
                st.metric("Procesados Exitosos", documentos_exitosos)
            with col3:
                st.metric("Fallidos", documentos_fallidos)
            with col4:
                st.metric("CIs Procesados", cis_procesados)
            
            if documentos_exitosos > 0:
                st.success(f"🎉 Carga masiva desde ZIP completada por {st.session_state.mongo_username}! {documentos_exitosos} documentos procesados exitosamente.")
                st.balloons()
                
                # Actualizar estadísticas
                st.session_state.last_delete_time = datetime.now().timestamp()
            
            if documentos_duplicados > 0:
                st.info(f"💡 {documentos_duplicados} documentos no se procesaron por duplicados. "
                       "Marca 'Sobrescribir documentos existentes' para forzar el reprocesamiento.")
                
    except Exception as e:
        st.error(f"❌ Error en el procesamiento masivo desde ZIP: {str(e)}")

# ... (MANTENER TODAS LAS FUNCIONES ORIGINALES EXCEPTO LAS DE CARGA LOCAL Y MASIVA)

# Las funciones originales de procesamiento de archivos, búsqueda, etc. se mantienen igual
# Solo reemplazamos las funciones de carga local y masiva

def procesar_archivo(archivo, tipo_archivo):
    try:
        contenido_binario = archivo.read()
        return Binary(contenido_binario), len(contenido_binario), None
    except Exception as e:
        return None, 0, f"Error procesando {tipo_archivo}: {e}"

def crear_boton_descarga(contenido_binario, nombre_archivo, tipo_archivo):
    try:
        b64 = base64.b64encode(contenido_binario).decode()
        
        mime_types = {
            "pdf": "application/pdf",
            "word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "doc": "application/msword",
            "imagen": "image/jpeg"
        }
        
        mime_type = mime_types.get(tipo_archivo, "application/octet-stream")
        
        href = f'''
        <a href="data:{mime_type};base64,{b64}" download="{nombre_archivo}" 
           style="background-color: #4CAF50; color: white; padding: 8px 12px; 
                  text-decoration: none; border-radius: 5px; display: inline-block;
                  font-weight: bold; font-size: 0.8rem;">
           📥 Descargar
        </a>
        '''
        return href
    except Exception as e:
        return f"❌ Error: {e}"

def buscar_documentos(db, criterio_busqueda, tipo_busqueda, filtros_adicionales=None):
    try:
        query = {}
        
        busqueda_map = {
            "nombre": "titulo",
            "autor": "autor",
            "contenido": "contenido",
            "tags": "tags",
            "categoria": "categoria",
            "ci": "ci",
            "descripcion": "descripcion",
            "usuario": "usuario_creacion"
        }
        
        campo = busqueda_map.get(tipo_busqueda)
        if campo:
            if tipo_busqueda == "tags":
                query[campo] = {"$in": [criterio_busqueda.strip()]}
            else:
                query[campo] = {"$regex": criterio_busqueda, "$options": "i"}
        
        if filtros_adicionales:
            query.update(filtros_adicionales)
        
        documentos = list(db.documentos.find(query).sort("fecha_creacion", -1))
        return documentos, None
        
    except Exception as e:
        return None, str(e)

def mostrar_documento_compacto(doc, key_suffix=""):
    """Muestra un documento en formato compacto y profesional"""
    
    iconos = {
        "pdf": "📄",
        "word": "📝", 
        "texto": "📃",
        "imagen": "🖼️"
    }
    
    icono = iconos.get(doc.get('tipo'), '📎')
    doc_id = str(doc['_id'])
    
    with st.container():
        st.markdown(f'<div class="document-card">', unsafe_allow_html=True)
        
        col1, col2 = st.columns([5, 1])
        
        with col1:
            st.markdown(f"**{icono} {doc['titulo']}**")
            
            meta_col1, meta_col2, meta_col3 = st.columns(3)
            with meta_col1:
                st.markdown(f'<div class="compact-metadata">👤 **Autor:** {doc["autor"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="compact-metadata">📂 **Categoría:** {doc["categoria"]}</div>', unsafe_allow_html=True)
            with meta_col2:
                st.markdown(f'<div class="compact-metadata">🔢 **CI:** {doc.get("ci", "N/A")}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="compact-metadata">🔄 **Versión:** {doc["version"]}</div>', unsafe_allow_html=True)
            with meta_col3:
                st.markdown(f'<div class="compact-metadata">📅 **Creado:** {doc["fecha_creacion"].strftime("%d/%m/%Y")}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="compact-metadata">👥 **Por:** {doc.get("usuario_creacion", "N/A")}</div>', unsafe_allow_html=True)
            
            if doc.get('almacenamiento') == 'zip':
                st.markdown(f'<div class="compact-metadata">💾 **Almacenamiento:** Archivo ZIP</div>', unsafe_allow_html=True)
            elif doc.get('almacenamiento') == 'local':
                st.markdown(f'<div class="compact-metadata">💾 **Almacenamiento:** Local ({doc.get("ruta_local", "N/A")})</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="compact-metadata">💾 **Almacenamiento:** Base de datos</div>', unsafe_allow_html=True)
            
            if doc.get('fecha_actualizacion') and doc.get('usuario_actualizacion'):
                st.markdown(f'<div class="compact-metadata">✏️ **Actualizado:** {doc["fecha_actualizacion"].strftime("%d/%m/%Y")} por {doc["usuario_actualizacion"]}</div>', unsafe_allow_html=True)
            
            if doc.get('tags'):
                tags_html = " ".join([f'<span class="tag">{tag}</span>' for tag in doc['tags']])
                st.markdown(f'<div class="compact-metadata">🏷️ **Tags:** {tags_html}</div>', unsafe_allow_html=True)
            
            if doc.get('tipo') == 'texto':
                contenido_preview = doc['contenido'][:100] + "..." if len(doc['contenido']) > 100 else doc['contenido']
                st.markdown(f'<div class="compact-metadata">📝 **Contenido:** {contenido_preview}</div>', unsafe_allow_html=True)
            elif doc.get('tipo') in ['pdf', 'word']:
                st.markdown(f'<div class="compact-metadata">📋 **Archivo:** {doc.get("nombre_archivo", "N/A")}</div>', unsafe_allow_html=True)
                if doc.get('tamaño_bytes'):
                    tamaño_mb = doc['tamaño_bytes'] / (1024 * 1024)
                    st.markdown(f'<div class="compact-metadata">💾 **Tamaño:** {tamaño_mb:.2f} MB</div>', unsafe_allow_html=True)
                
                if doc.get('contenido_binario') and doc.get('almacenamiento') != 'zip':
                    boton_descarga = crear_boton_descarga(
                        doc['contenido_binario'],
                        doc['nombre_archivo'],
                        doc['tipo']
                    )
                    st.markdown(boton_descarga, unsafe_allow_html=True)
                elif doc.get('almacenamiento') == 'zip':
                    st.markdown(f'<div class="compact-metadata">📍 **Archivo en ZIP:** No disponible para descarga directa</div>', unsafe_allow_html=True)
            
            st.markdown(f'<div class="compact-metadata" style="font-size: 0.7rem; color: #999;">🆔 **ID:** {doc_id[:12]}...</div>', unsafe_allow_html=True)
        
        with col2:
            st.write("")
            if st.button("🗑️", key=f"delete_{doc_id}_{key_suffix}", help="Eliminar documento", use_container_width=True):
                with st.spinner("Eliminando..."):
                    try:
                        doc_existente = st.session_state.db_connection.documentos.find_one({"_id": doc["_id"]})
                        if not doc_existente:
                            st.error("❌ El documento ya no existe")
                            return
                        
                        result = st.session_state.db_connection.documentos.delete_one({"_id": doc["_id"]})
                        
                        if result.deleted_count > 0:
                            st.success("✅ Documento eliminado")
                            st.session_state.last_delete_time = datetime.now().timestamp()
                            st.session_state.refresh_counter += 1
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error("❌ No se pudo eliminar")
                            
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        
        st.markdown('</div>', unsafe_allow_html=True)

def crear_formulario_documento(tipo_documento, tab_key):
    """Crea un formulario reutilizable para diferentes tipos de documentos"""
    
    with st.form(f"form_{tipo_documento}_{tab_key}", clear_on_submit=True):
        st.markdown(f"### 📝 Información del Documento")
        
        st.info(f"**Usuario de BD:** 👤 {st.session_state.mongo_username}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            titulo = st.text_input(
                "**Título del documento** *",
                placeholder=f"Ej: Manual de Usuario {tipo_documento.upper()}",
                help="Nombre descriptivo del documento",
                key=f"titulo_{tipo_documento}_{tab_key}"
            )
            categoria = st.selectbox(
                "**Categoría** *",
                ["Técnica", "Usuario", "API", "Tutorial", "prueba", "Procedimiento", "Política", "Otros"],
                help="Categoría principal del documento",
                key=f"categoria_{tipo_documento}_{tab_key}"
            )
            autor = st.text_input(
                "**Autor** *",
                placeholder="Nombre completo del autor",
                help="Persona responsable del documento",
                key=f"autor_{tipo_documento}_{tab_key}"
            )
            
        with col2:
            ci = st.text_input(
                "**CI/Cédula** *",
                placeholder="Número de identificación",
                help="Cédula de identidad del autor",
                key=f"ci_{tipo_documento}_{tab_key}"
            )
            version = st.text_input(
                "**Versión**",
                value="1.0",
                placeholder="Ej: 1.2.3",
                help="Versión del documento",
                key=f"version_{tipo_documento}_{tab_key}"
            )
            tags_input = st.text_input(
                "**Etiquetas**",
                placeholder="tecnico,manual,instalacion",
                help="Separar con comas",
                key=f"tags_{tipo_documento}_{tab_key}"
            )
            prioridad = st.select_slider(
                "**Prioridad**",
                options=["Baja", "Media", "Alta"],
                value="Media",
                help="Nivel de prioridad del documento",
                key=f"prioridad_{tipo_documento}_{tab_key}"
            )
        
        if tipo_documento == "texto":
            contenido = st.text_area(
                "**Contenido del documento** *",
                height=200,
                placeholder="Escribe el contenido completo del documento aquí...",
                help="Contenido principal en formato texto",
                key=f"contenido_{tipo_documento}_{tab_key}"
            )
        else:
            archivo = st.file_uploader(
                f"**Seleccionar archivo {tipo_documento.upper()}** *",
                type=[tipo_documento] if tipo_documento != 'word' else ['docx', 'doc'],
                help=f"Sube tu archivo {tipo_documento.upper()}",
                key=f"archivo_{tipo_documento}_{tab_key}"
            )
            descripcion = st.text_area(
                "**Descripción del documento**",
                height=80,
                placeholder="Breve descripción del contenido del archivo...",
                help="Resumen del contenido del documento",
                key=f"descripcion_{tipo_documento}_{tab_key}"
            )
        
        submitted = st.form_submit_button(
            f"💾 Guardar Documento {tipo_documento.upper()}",
            use_container_width=True,
            key=f"submit_{tipo_documento}_{tab_key}"
        )
        
        if submitted:
            return validar_y_guardar_documento(tipo_documento, locals())
    
    return False

def validar_y_guardar_documento(tipo_documento, variables_locales):
    """Valida y guarda el documento en la base de datos"""
    
    titulo = variables_locales['titulo']
    autor = variables_locales['autor']
    ci = variables_locales['ci']
    
    if not all([titulo, autor, ci]):
        st.warning("⚠️ Completa los campos obligatorios (*)")
        return False
    
    if tipo_documento == "texto":
        if not variables_locales['contenido']:
            st.warning("⚠️ El contenido del documento es obligatorio")
            return False
    else:
        if not variables_locales['archivo']:
            st.warning("⚠️ Debes seleccionar un archivo")
            return False
    
    documento = {
        "titulo": titulo,
        "categoria": variables_locales['categoria'],
        "autor": autor,
        "ci": ci,
        "version": variables_locales['version'],
        "tags": [tag.strip() for tag in variables_locales['tags_input'].split(",")] if variables_locales['tags_input'] else [],
        "prioridad": variables_locales['prioridad'],
        "tipo": tipo_documento,
        "fecha_creacion": datetime.utcnow(),
        "fecha_actualizacion": datetime.utcnow(),
        "usuario_creacion": st.session_state.mongo_username,
        "usuario_actualizacion": st.session_state.mongo_username,
        "almacenamiento": "base_datos"
    }
    
    if tipo_documento == "texto":
        documento["contenido"] = variables_locales['contenido']
    else:
        archivo = variables_locales['archivo']
        contenido_binario, tamaño, error = procesar_archivo(archivo, tipo_documento)
        
        if error:
            st.error(f"❌ {error}")
            return False
            
        documento.update({
            "descripcion": variables_locales['descripcion'],
            "nombre_archivo": archivo.name,
            "contenido_binario": contenido_binario,
            "tamaño_bytes": tamaño
        })
    
    try:
        result = st.session_state.db_connection.documentos.insert_one(documento)
        st.success(f"✅ Documento '{titulo}' guardado exitosamente por {st.session_state.mongo_username}!")
        st.balloons()
        
        st.session_state.last_delete_time = datetime.now().timestamp()
        return True
    except Exception as e:
        st.error(f"❌ Error al guardar: {str(e)}")
        return False

def validar_csv_metadatos(df):
    """Valida la estructura del CSV de metadatos"""
    errores = []
    
    if df.empty:
        errores.append("El archivo CSV está vacío")
        return errores
    
    if len(df.columns) == 0:
        errores.append("El archivo CSV no tiene columnas")
        return errores
    
    campos_obligatorios = ['ci', 'nombre']
    for campo in campos_obligatorios:
        if campo not in df.columns:
            errores.append(f"Falta columna obligatoria: '{campo}'")
    
    if errores:
        return errores
    
    if df['ci'].isnull().any():
        errores.append("Hay valores nulos en la columna 'ci'")
    
    return errores

def cargar_y_validar_csv(archivo_csv, nombre_funcionalidad="carga"):
    """Carga y valida un archivo CSV con manejo de errores mejorado"""
    try:
        if archivo_csv.size == 0:
            return None, "El archivo CSV está vacío"
        
        contenido = archivo_csv.getvalue().decode('utf-8')
        
        if not contenido.strip():
            return None, "El archivo CSV está vacío"
        
        lineas = contenido.strip().split('\n')
        
        if len(lineas) == 0:
            return None, "El archivo CSV no contiene datos"
        
        if len(lineas) < 2:
            return None, "El archivo CSV no contiene filas de datos"
        
        try:
            archivo_csv.seek(0)
            df = pd.read_csv(archivo_csv)
        except Exception as e:
            try:
                headers = lineas[0].split(',')
                data = []
                
                for line in lineas[1:]:
                    if line.strip():
                        values = line.split(',')
                        if len(values) == len(headers):
                            data.append(values)
                
                if len(data) == 0:
                    return None, "No se encontraron filas de datos válidas"
                
                df = pd.DataFrame(data, columns=headers)
                st.success("✅ CSV cargado con procesamiento manual")
                
            except Exception as e2:
                return None, f"No se pudo leer el CSV: {str(e2)}"
        
        if df.empty:
            return None, "El archivo CSV no contiene filas de datos"
        
        if len(df.columns) == 0:
            return None, "El archivo CSV no tiene columnas identificables"
        
        df.columns = df.columns.str.strip()
        
        st.success(f"✅ CSV cargado exitosamente: {len(df)} registros, {len(df.columns)} columnas")
        
        errores = validar_csv_metadatos(df)
        if errores:
            return None, " | ".join(errores)
        
        return df, None
        
    except Exception as e:
        return None, f"Error inesperado al procesar el CSV: {str(e)}"

def crear_plantilla_carga_masiva():
    """Crea y descarga plantilla CSV para carga masiva"""
    
    datos_ejemplo = {
        'ci': ['12345678', '87654321', '11223344', '55667788', '99887766'],
        'nombre': ['Juan Pérez García', 'María López Martínez', 'Carlos Rodríguez Silva', 
                  'Ana Fernández Cruz', 'Pedro González Reyes'],
        'titulo': ['Contrato Laboral', 'Identificación Oficial', 'Curriculum Vitae', 
                  'Certificado Estudios', 'Comprobante Domicilio'],
        'categoria': ['Legal', 'Identificación', 'Laboral', 'Educación', 'Personal'],
        'autor': ['Departamento Legal', 'Sistema Automático', 'Recursos Humanos', 
                 'Institución Educativa', 'Usuario'],
        'version': ['1.0', '1.0', '2.1', '1.0', '1.0'],
        'etiquetas': ['contrato,laboral,legal', 'identificacion,oficial', 
                     'curriculum,laboral', 'educacion,certificado', 'domicilio,personal'],
        'prioridad': ['Alta', 'Alta', 'Media', 'Media', 'Baja']
    }
    
    df_plantilla = pd.DataFrame(datos_ejemplo)
    
    output = io.BytesIO()
    df_plantilla.to_csv(output, index=False, encoding='utf-8')
    output.seek(0)
    
    b64 = base64.b64encode(output.read()).decode()
    href = f'''
    <a href="data:text/csv;base64,{b64}" 
       download="plantilla_carga_masiva_ci.csv" 
       style="background-color: #2196F3; color: white; padding: 12px 20px; 
              text-decoration: none; border-radius: 5px; display: inline-block;
              font-weight: bold; font-size: 16px;">
       📥 Descargar Plantilla CSV
    </a>
    '''
    st.markdown(href, unsafe_allow_html=True)

# --- SIDEBAR MEJORADO ---

with st.sidebar:
    st.markdown("## 🔐 Configuración")
    
    st.image("https://cdn-icons-png.flaticon.com/512/2721/2721264.png", width=80)
    
    st.markdown("### 👤 Usuario de Base de Datos")
    st.markdown(f'<div class="user-badge">👤 {st.session_state.mongo_username}</div>', unsafe_allow_html=True)
    st.write(f"**Estado:** {st.session_state.current_user}")
    
    mongo_uri = st.text_input(
        "**Cadena de Conexión MongoDB**",
        type="password",
        placeholder="mongodb+srv://usuario:contraseña@cluster...",
        help="Ingresa tu URI de conexión a MongoDB Atlas",
        key="mongo_uri_input"
    )
    
    col_conn1, col_conn2 = st.columns(2)
    with col_conn1:
        connect_btn = st.button("🔗 Conectar", use_container_width=True, key="connect_btn")
    with col_conn2:
        disconnect_btn = st.button("🔓 Desconectar", use_container_width=True, key="disconnect_btn")
    
    if disconnect_btn:
        st.session_state.db_connection = None
        st.session_state.db_connected = False
        st.session_state.current_user = "No conectado"
        st.session_state.mongo_username = "Desconocido"
        st.session_state.df_metadatos_local = None
        st.session_state.df_metadatos_masiva = None
        st.session_state.last_delete_time = datetime.now().timestamp()
        st.session_state.archivos_zip_procesados = {}
        st.success("🔓 Desconectado de la base de datos")
        st.rerun()
    
    if connect_btn and mongo_uri:
        with st.spinner("Conectando a MongoDB..."):
            db, connected, message, username = connect_mongodb(mongo_uri)
            if connected:
                st.session_state.db_connection = db
                st.session_state.db_connected = True
                st.session_state.current_user = "Conectado"
                st.session_state.mongo_username = username
                st.session_state.last_delete_time = datetime.now().timestamp()
                st.success(f"✅ {message}")
            else:
                st.error(f"❌ {message}")
    
    if st.session_state.db_connected:
        st.success(f"✅ Conexión activa | 👤 {st.session_state.mongo_username}")
        st.markdown("---")
        
        try:
            db = st.session_state.db_connection
            
            total_docs = db.documentos.count_documents({})
            pdf_count = db.documentos.count_documents({"tipo": "pdf"})
            word_count = db.documentos.count_documents({"tipo": "word"})
            text_count = db.documentos.count_documents({"tipo": "texto"})
            image_count = db.documentos.count_documents({"tipo": "imagen"})
            zip_count = db.documentos.count_documents({"almacenamiento": "zip"})
            usuarios_activos = db.documentos.distinct("usuario_creacion")
            
            st.markdown("### 📊 Estadísticas")
            
            st.metric("📄 Total Documentos", total_docs)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("📝 Texto", text_count)
                st.metric("📄 PDF", pdf_count)
            with col2:
                st.metric("📋 Word", word_count)
                st.metric("🖼️ Imágenes", image_count)
            
            st.metric("👥 Usuarios Activos", len(usuarios_activos))
            st.metric("📦 Archivos ZIP", zip_count)
                
        except Exception as e:
            st.error(f"❌ Error obteniendo estadísticas: {str(e)}")
            st.session_state.db_connection = None
            st.session_state.db_connected = False
    
    elif mongo_uri and not st.session_state.db_connected:
        st.warning("⚠️ Presiona 'Conectar' para establecer la conexión")
    else:
        st.info("👈 Ingresa la cadena de conexión MongoDB")

# --- APLICACIÓN PRINCIPAL ---

if st.session_state.db_connected and st.session_state.db_connection is not None:
    db = st.session_state.db_connection
    st.success(f"🚀 Conectado a la base de datos | 👤 Usuario: {st.session_state.mongo_username}")
    
    st.markdown("---")
    st.markdown("## 📁 Gestión de Documentos")
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🔍 Buscar Documentos", 
        "📝 Crear Texto", 
        "📄 Subir PDF", 
        "📝 Subir Word", 
        "📂 Todos los Documentos",
        "🚀 Carga Masiva ZIP",
        "💾 Carga Local ZIP"
    ])
    
    # PESTAÑA 1: BÚSQUEDA AVANZADA
    with tab1:
        st.markdown("### 🔍 Búsqueda Avanzada de Documentos")
        
        with st.expander("**🔎 Opciones de Búsqueda**", expanded=True):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                criterio_busqueda = st.text_input(
                    "**Término de búsqueda**",
                    placeholder="Ingresa palabras clave, nombre, CI, autor...",
                    key="busqueda_principal_tab1"
                )
            
            with col2:
                tipo_busqueda = st.selectbox(
                    "**Buscar por:**",
                    ["nombre", "autor", "contenido", "tags", "categoria", "ci", "descripcion", "usuario"],
                    format_func=lambda x: {
                        "nombre": "📄 Nombre del documento",
                        "autor": "👤 Autor", 
                        "contenido": "📝 Contenido",
                        "tags": "🏷️ Etiquetas",
                        "categoria": "📂 Categoría",
                        "ci": "🔢 CI/Cédula",
                        "descripcion": "📋 Descripción",
                        "usuario": "👥 Usuario creador"
                    }[x],
                    key="tipo_busqueda_tab1"
                )
            
            with col3:
                st.write("")
                st.write("")
                buscar_btn = st.button("🔎 Ejecutar Búsqueda", use_container_width=True, key="buscar_btn_tab1")
        
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filtro_tipo_busq = st.selectbox("Filtrar por tipo", ["Todos", "Texto", "PDF", "Word", "Imagen"], key="filtro_tipo_tab1")
        with col_f2:
            filtro_categoria_busq = st.selectbox("Filtrar por categoría", ["Todas"] + ["Técnica", "Usuario", "API", "Tutorial", "Referencia", "Procedimiento", "Política", "Otros"], key="filtro_categoria_tab1")
        with col_f3:
            filtro_prioridad_busq = st.selectbox("Filtrar por prioridad", ["Todas", "Alta", "Media", "Baja"], key="filtro_prioridad_tab1")
        
        if buscar_btn and criterio_busqueda:
            with st.spinner("🔍 Buscando en la base de datos..."):
                filtros_adicionales = {}
                if filtro_tipo_busq != "Todos":
                    filtros_adicionales["tipo"] = filtro_tipo_busq.lower()
                if filtro_categoria_busq != "Todas":
                    filtros_adicionales["categoria"] = filtro_categoria_busq
                if filtro_prioridad_busq != "Todas":
                    filtros_adicionales["prioridad"] = filtro_prioridad_busq
                
                documentos_encontrados, error = buscar_documentos(
                    db, criterio_busqueda, tipo_busqueda, filtros_adicionales
                )
                
                if error:
                    st.error(f"❌ Error en búsqueda: {error}")
                elif documentos_encontrados:
                    st.success(f"✅ Encontrados {len(documentos_encontrados)} documento(s)")
                    
                    for i, doc in enumerate(documentos_encontrados):
                        mostrar_documento_compacto(doc, f"search_{i}")
                else:
                    st.info("🔍 No se encontraron documentos con esos criterios")
        
        elif buscar_btn and not criterio_busqueda:
            st.warning("⚠️ Ingresa un término de búsqueda")
    
    # PESTAÑA 2: Crear Texto Simple
    with tab2:
        st.markdown("### Crear Documento de Texto")
        crear_formulario_documento("texto", "tab2")
    
    # PESTAÑA 3: Subir PDF
    with tab3:
        st.markdown("### Subir Documento PDF")
        crear_formulario_documento("pdf", "tab3")
    
    # PESTAÑA 4: Subir Word
    with tab4:
        st.markdown("### Subir Documento Word")
        crear_formulario_documento("word", "tab4")
    
    # PESTAÑA 5: Todos los Documentos
    with tab5:
        st.markdown("### 📂 Biblioteca de Documentos")
        
        with st.expander("**🎛️ Filtros Avanzados**", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                filtro_tipo = st.selectbox("Tipo de documento", ["Todos", "Texto", "PDF", "Word", "Imagen"], key="filtro_tipo_tab5")
            with col2:
                filtro_categoria = st.selectbox("Categoría", ["Todas"] + ["Técnica", "Usuario", "API", "Tutorial", "Referencia", "Procedimiento", "Política", "Otros"], key="filtro_categoria_tab5")
            with col3:
                filtro_prioridad = st.selectbox("Prioridad", ["Todas", "Alta", "Media", "Baja"], key="filtro_prioridad_tab5")
            with col4:
                fecha_desde = st.date_input("Desde fecha", key="fecha_desde_tab5")
        
        busqueda_rapida = st.text_input("🔍 Búsqueda rápida por título o CI", key="busqueda_rapida_tab5")
        
        query = {}
        if filtro_tipo != "Todos":
            query["tipo"] = filtro_tipo.lower()
        if filtro_categoria != "Todas":
            query["categoria"] = filtro_categoria
        if filtro_prioridad != "Todas":
            query["prioridad"] = filtro_prioridad
        if fecha_desde:
            query["fecha_creacion"] = {"$gte": datetime.combine(fecha_desde, datetime.min.time())}
        if busqueda_rapida:
            query["$or"] = [
                {"titulo": {"$regex": busqueda_rapida, "$options": "i"}},
                {"ci": {"$regex": busqueda_rapida, "$options": "i"}},
                {"autor": {"$regex": busqueda_rapida, "$options": "i"}},
                {"usuario_creacion": {"$regex": busqueda_rapida, "$options": "i"}}
            ]
        
        try:
            with st.spinner("Cargando documentos..."):
                documentos = list(db.documentos.find(query).sort("fecha_creacion", -1))
            
            if documentos:
                st.info(f"📊 Mostrando {len(documentos)} documento(s)")
                
                for i, doc in enumerate(documentos):
                    mostrar_documento_compacto(doc, f"all_{i}")
            else:
                st.info("📝 No se encontraron documentos. ¡Agrega el primero en las pestañas de arriba!")
                
        except Exception as e:
            st.error(f"❌ Error al cargar documentos: {str(e)}")
    
    # PESTAÑA 6: Carga Masiva por CI CON ZIP
    with tab6:
        st.markdown("### 🚀 Carga Masiva desde ZIP")
        st.info(f"""
        **Carga masiva de documentos desde archivo ZIP**
        - Sube un ZIP con documentos organizados
        - Los documentos se almacenan en la base de datos
        - Soporta: PDF, Word, imágenes, texto
        - Hasta 10,000 documentos por carga
        - **Usuario de BD:** 👤 {st.session_state.mongo_username}
        """)
        
        # Configuración
        col_config1, col_config2 = st.columns(2)
        
        with col_config1:
            st.markdown("#### 📦 Subir Archivo ZIP")
            
            archivo_zip_masivo = st.file_uploader(
                "**Selecciona archivo ZIP** *",
                type=['zip'],
                help="ZIP con documentos organizados",
                key="archivo_zip_masivo_tab6"
            )
            
            if archivo_zip_masivo:
                # Extraer y mostrar información del ZIP
                archivos_zip, error_zip = extraer_archivos_desde_zip(archivo_zip_masivo)
                
                if error_zip:
                    st.error(f"❌ {error_zip}")
                else:
                    st.session_state.archivos_zip_procesados['masivo'] = archivos_zip
                    st.success(f"✅ ZIP procesado: {len(archivos_zip)} archivos extraídos")
                    
                    with st.expander("📋 Ver contenido del ZIP", expanded=True):
                        st.write(f"**Total de archivos:** {len(archivos_zip)}")
                        for i, (nombre, archivo) in enumerate(list(archivos_zip.items())[:10]):
                            tamaño_mb = len(archivo.getvalue()) / (1024 * 1024)
                            st.write(f"{i+1}. 📄 {nombre} ({tamaño_mb:.2f} MB)")
                        if len(archivos_zip) > 10:
                            st.write(f"... y {len(archivos_zip) - 10} archivos más")
            
            tipos_archivo = st.multiselect(
                "**Tipos de archivo a procesar** *",
                ['.pdf', '.docx', '.doc', '.jpg', '.jpeg', '.png', '.txt'],
                default=['.pdf', '.docx', '.doc'],
                help="Selecciona los tipos de archivo a incluir",
                key="tipos_archivo_tab6"
            )
        
        with col_config2:
            st.markdown("#### 📊 Configuración de Procesamiento")
            max_documentos = st.number_input(
                "**Límite de documentos**",
                min_value=100,
                max_value=10000,
                value=3000,
                step=100,
                help="Máximo número de documentos a procesar",
                key="max_documentos_tab6"
            )
            
            tamaño_lote = st.slider(
                "**Tamaño del lote**",
                min_value=50,
                max_value=500,
                value=100,
                help="Documentos procesados por lote (mejora performance)",
                key="tamaño_lote_tab6"
            )
            
            sobrescribir_existentes = st.checkbox(
                "**Sobrescribir documentos existentes**",
                value=False,
                help="Reemplazar documentos que ya existen en la base de datos",
                key="sobrescribir_existentes_tab6"
            )
        
        # Sección para CSV de metadatos
        st.markdown("#### 📋 Archivo CSV con Metadatos")
        st.info("""
        **El CSV debe contener las columnas:**
        - `ci` (obligatorio): Número de cédula
        - `nombre` (obligatorio): Nombre completo
        - `titulo`: Título del documento
        - `categoria`: Categoría del documento
        - `autor`: Autor del documento  
        - `version`: Versión del documento
        - `etiquetas`: Tags separados por comas
        - `prioridad`: Baja, Media, Alta
        """)
        
        archivo_csv = st.file_uploader(
            "**Subir CSV con metadatos** *",
            type=['csv'],
            help="CSV con información de CI, nombres, títulos, etc.",
            key="archivo_csv_tab6"
        )
        
        if archivo_csv:
            try:
                content = archivo_csv.getvalue().decode('utf-8')
                lines = content.split('\n')
                
                st.success(f"✅ Archivo CSV cargado: {len(lines)} líneas detectadas")
                
                with st.expander("📊 Vista previa del CSV (primeras 5 líneas)", expanded=True):
                    st.write("**Contenido del CSV:**")
                    for i, line in enumerate(lines[:6]):
                        st.text(f"Línea {i+1}: {line}")
                
                if st.button("🔍 Validar estructura del CSV", key="validar_csv_tab6"):
                    with st.spinner("Validando CSV..."):
                        archivo_csv.seek(0)
                        df_metadatos, error_csv = cargar_y_validar_csv(archivo_csv, "carga masiva")
                        
                        if error_csv:
                            st.error(f"❌ Error en el CSV: {error_csv}")
                        else:
                            st.session_state.df_metadatos_masiva = df_metadatos
                            st.success(f"✅ CSV validado correctamente: {len(df_metadatos)} registros de {df_metadatos['ci'].nunique()} CIs diferentes")
                            
                            with st.expander("📋 Resumen del CSV validado", expanded=True):
                                st.dataframe(df_metadatos.head(), use_container_width=True)
                                st.write(f"**Total de registros:** {len(df_metadatos)}")
                                st.write(f"**CIs únicos:** {df_metadatos['ci'].nunique()}")
                                st.write(f"**Columnas:** {list(df_metadatos.columns)}")
            
            except Exception as e:
                st.error(f"❌ Error al leer el CSV: {str(e)}")
        
        st.markdown("---")
        st.markdown("#### 🧪 Generar Plantilla")
        crear_plantilla_carga_masiva()
        
        st.markdown("#### ⚡ Procesamiento Masivo desde ZIP")
        
        if st.button("🚀 Iniciar Carga Masiva desde ZIP", type="primary", use_container_width=True, key="btn_carga_masiva_tab6"):
            if 'masivo' not in st.session_state.archivos_zip_procesados:
                st.error("❌ Primero debes subir y procesar un archivo ZIP")
            elif st.session_state.df_metadatos_masiva is None:
                st.error("❌ Primero debes validar el CSV usando el botón 'Validar estructura del CSV'")
            elif not tipos_archivo:
                st.error("❌ Debes seleccionar al menos un tipo de archivo")
            else:
                archivos_zip = st.session_state.archivos_zip_procesados['masivo']
                df_metadatos = st.session_state.df_metadatos_masiva
                
                st.info(f"📋 **Resumen a procesar:** {len(archivos_zip)} archivos en ZIP, {len(df_metadatos)} registros de {df_metadatos['ci'].nunique()} CIs")
                
                with st.spinner("🔄 Iniciando procesamiento masivo desde ZIP..."):
                    resultado = procesar_carga_masiva_ci_zip(
                        db=db,
                        archivos_zip=archivos_zip,
                        df_metadatos=df_metadatos,
                        tipos_archivo=tipos_archivo,
                        max_documentos=max_documentos,
                        tamaño_lote=tamaño_lote,
                        sobrescribir_existentes=sobrescribir_existentes
                    )

    # PESTAÑA 7: Carga Local CON ZIP (VERSIÓN STREAMLIT CLOUD)
    with tab7:
        st.markdown("### 💾 Carga Local desde ZIP")
        st.info(f"""
        **Carga masiva manteniendo referencia a archivos en ZIP**
        - Sube un ZIP con todos los documentos
        - Solo los metadatos se almacenan en MongoDB
        - Los archivos permanecen referenciados desde el ZIP
        - Soporta: PDF, Word, imágenes, texto
        - Hasta 10,000 documentos por carga
        - **Usuario de BD:** 👤 {st.session_state.mongo_username}
        """)
        
        # Configuración
        col_config1, col_config2 = st.columns(2)
        
        with col_config1:
            st.markdown("#### 📦 Subir Archivo ZIP")
            
            archivo_zip_local = st.file_uploader(
                "**Selecciona archivo ZIP con documentos** *",
                type=['zip'],
                help="ZIP conteniendo todos los documentos a procesar",
                key="archivo_zip_local_tab7"
            )
            
            if archivo_zip_local:
                # Extraer y mostrar información del ZIP
                archivos_zip, error_zip = extraer_archivos_desde_zip(archivo_zip_local)
                
                if error_zip:
                    st.error(f"❌ {error_zip}")
                else:
                    st.session_state.archivos_zip_procesados['local'] = archivos_zip
                    st.success(f"✅ ZIP procesado: {len(archivos_zip)} archivos extraídos")
                    
                    # Mostrar estadísticas del ZIP
                    with st.expander("📊 Estadísticas del ZIP", expanded=True):
                        st.markdown(f'<div class="zip-info">', unsafe_allow_html=True)
                        st.write(f"**📦 Archivo ZIP:** {archivo_zip_local.name}")
                        st.write(f"**📄 Total de archivos:** {len(archivos_zip)}")
                        
                        # Contar por tipo
                        contadores = {
                            'pdf': 0, 'word': 0, 'imagen': 0, 'texto': 0, 'otros': 0
                        }
                        
                        for nombre_archivo in archivos_zip.keys():
                            extension = Path(nombre_archivo).suffix.lower()
                            if extension == '.pdf':
                                contadores['pdf'] += 1
                            elif extension in ['.docx', '.doc']:
                                contadores['word'] += 1
                            elif extension in ['.jpg', '.jpeg', '.png']:
                                contadores['imagen'] += 1
                            elif extension == '.txt':
                                contadores['texto'] += 1
                            else:
                                contadores['otros'] += 1
                        
                        col_stats1, col_stats2, col_stats3 = st.columns(3)
                        with col_stats1:
                            st.metric("📄 PDF", contadores['pdf'])
                            st.metric("📝 Word", contadores['word'])
                        with col_stats2:
                            st.metric("🖼️ Imágenes", contadores['imagen'])
                            st.metric("📃 Texto", contadores['texto'])
                        with col_stats3:
                            st.metric("📎 Otros", contadores['otros'])
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Mostrar primeros archivos
                    with st.expander("📋 Ver primeros 15 archivos", expanded=False):
                        for i, (nombre, archivo) in enumerate(list(archivos_zip.items())[:15]):
                            tamaño_mb = len(archivo.getvalue()) / (1024 * 1024)
                            st.write(f"{i+1}. 📄 `{nombre}` ({tamaño_mb:.2f} MB)")
                        if len(archivos_zip) > 15:
                            st.write(f"... y {len(archivos_zip) - 15} archivos más")
            
            tipos_archivo_local = st.multiselect(
                "**Tipos de archivo a procesar** *",
                ['.pdf', '.docx', '.doc', '.jpg', '.jpeg', '.png', '.txt'],
                default=['.pdf', '.docx', '.doc'],
                help="Selecciona los tipos de archivo a incluir",
                key="tipos_archivo_local_tab7"
            )
            
            patron_busqueda = st.selectbox(
                "**Patrón de búsqueda de CI** *",
                ["CI al inicio", "CI en cualquier parte", "CI específico en nombre"],
                help="Cómo buscar el CI en los nombres de archivo",
                key="patron_busqueda_tab7"
            )
        
        with col_config2:
            st.markdown("#### 📊 Configuración de Procesamiento")
            max_documentos_local = st.number_input(
                "**Límite de documentos**",
                min_value=100,
                max_value=10000,
                value=3000,
                step=100,
                help="Máximo número de documentos a procesar",
                key="max_documentos_local_tab7"
            )
            
            tamaño_lote_local = st.slider(
                "**Tamaño del lote**",
                min_value=50,
                max_value=500,
                value=100,
                help="Documentos procesados por lote (mejora performance)",
                key="tamaño_lote_local_tab7"
            )
            
            sobrescribir_existentes_local = st.checkbox(
                "**Sobrescribir documentos existentes**",
                value=False,
                help="Reemplazar documentos que ya existen en la base de datos",
                key="sobrescribir_existentes_local_tab7"
            )
        
        # Sección para CSV de metadatos
        st.markdown("#### 📋 Archivo CSV con Metadatos")
        st.info("""
        **El CSV debe contener las columnas:**
        - `ci` (obligatorio): Número de cédula (debe coincidir con los nombres de archivo)
        - `nombre` (obligatorio): Nombre completo
        - `titulo`: Título del documento (si no se especifica, se genera automáticamente)
        - `categoria`: Categoría del documento
        - `autor`: Autor del documento  
        - `version`: Versión del documento
        - `etiquetas`: Tags separados por comas
        - `prioridad`: Baja, Media, Alta
        
        **Ejemplos de nombres de archivo en el ZIP:**
        - `12345678_contrato.pdf` (CI al inicio)
        - `contrato_12345678.pdf` (CI en cualquier parte)
        - `CI_12345678_identificacion.jpg` (CI específico)
        """)
        
        archivo_csv_local = st.file_uploader(
            "**Subir CSV con metadatos** *",
            type=['csv'],
            help="CSV con información de CI, nombres, títulos, etc.",
            key="archivo_csv_local_tab7"
        )
        
        if archivo_csv_local:
            try:
                content = archivo_csv_local.getvalue().decode('utf-8')
                lines = content.split('\n')
                
                st.success(f"✅ Archivo CSV cargado: {len(lines)} líneas detectadas")
                
                with st.expander("📊 Vista previa del CSV (primeras 5 líneas)", expanded=True):
                    st.write("**Contenido del CSV:**")
                    for i, line in enumerate(lines[:6]):
                        st.text(f"Línea {i+1}: {line}")
                
                if st.button("🔍 Validar estructura del CSV", key="validar_csv_tab7"):
                    with st.spinner("Validando CSV..."):
                        archivo_csv_local.seek(0)
                        df_metadatos_local, error_csv = cargar_y_validar_csv(archivo_csv_local, "carga local")
                        
                        if error_csv:
                            st.error(f"❌ Error en el CSV: {error_csv}")
                        else:
                            st.session_state.df_metadatos_local = df_metadatos_local
                            st.success(f"✅ CSV validado correctamente: {len(df_metadatos_local)} registros de {df_metadatos_local['ci'].nunique()} CIs diferentes")
                            
                            with st.expander("📋 Resumen del CSV validado", expanded=True):
                                st.dataframe(df_metadatos_local.head(), use_container_width=True)
                                st.write(f"**Total de registros:** {len(df_metadatos_local)}")
                                st.write(f"**CIs únicos:** {df_metadatos_local['ci'].nunique()}")
                                st.write(f"**Columnas:** {list(df_metadatos_local.columns)}")
            
            except Exception as e:
                st.error(f"❌ Error al leer el CSV: {str(e)}")
        
        # Botón de procesamiento
        st.markdown("#### ⚡ Procesamiento Local desde ZIP")
        
        if st.button("🚀 Iniciar Carga Local desde ZIP", type="primary", use_container_width=True, key="btn_carga_local_tab7"):
            if 'local' not in st.session_state.archivos_zip_procesados:
                st.error("❌ Primero debes subir y procesar un archivo ZIP")
            elif st.session_state.df_metadatos_local is None:
                st.error("❌ Primero debes validar el CSV usando el botón 'Validar estructura del CSV'")
            elif not tipos_archivo_local:
                st.error("❌ Debes seleccionar al menos un tipo de archivo")
            else:
                archivos_zip = st.session_state.archivos_zip_procesados['local']
                df_metadatos_local = st.session_state.df_metadatos_local
                
                st.info(f"📋 **Resumen a procesar:** {len(archivos_zip)} archivos en ZIP, {len(df_metadatos_local)} registros de {df_metadatos_local['ci'].nunique()} CIs")
                
                with st.spinner("🔄 Iniciando procesamiento local desde ZIP..."):
                    resultado = procesar_carga_local_zip(
                        db=db,
                        archivos_zip=archivos_zip,
                        df_metadatos=df_metadatos_local,
                        tipos_archivo=tipos_archivo_local,
                        max_documentos=max_documentos_local,
                        tamaño_lote=tamaño_lote_local,
                        patron_busqueda=patron_busqueda,
                        sobrescribir_existentes=sobrescribir_existentes_local
                    )

else:
    st.info("👈 Configura la conexión a MongoDB en la barra lateral para comenzar")

# Footer mejorado
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>Sistema de Gestión Documental | 📧 erp@ec.aseyco.com | 📞 02483914</p>
    <p>© 2024 Marathon Sports. Todos los derechos reservados.</p>
</div>
""", unsafe_allow_html=True)
