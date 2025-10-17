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
</style>
""", unsafe_allow_html=True)

# Título principal mejorado
st.markdown('<h1 class="main-header">📚 Sistema de Gestión Documental</h1>', unsafe_allow_html=True)
st.markdown('<p class="subheader">Gestión centralizada de documentos con búsqueda avanzada y control de versiones</p>', unsafe_allow_html=True)

# Sidebar mejorado
with st.sidebar:
    st.markdown("## 🔐 Configuración")
    
    # Logo o imagen de la empresa
    st.image("https://cdn-icons-png.flaticon.com/512/2721/2721264.png", width=80)
    
    mongo_uri = st.text_input(
        "**Cadena de Conexión MongoDB**",
        type="password",
        placeholder="mongodb+srv://usuario:contraseña@cluster...",
        help="Ingresa tu URI de conexión a MongoDB Atlas"
    )
    
    if mongo_uri:
        st.success("✅ Conexión configurada")
        st.markdown("---")
        
        # Estadísticas rápidas si hay conexión
        try:
            client = pymongo.MongoClient(mongo_uri)
            db = client.documentation_db
            
            # USAR TIMESTAMP PARA ACTUALIZAR ESTADÍSTICAS
            cache_buster = st.session_state.get('last_delete_time', '')
            
            total_docs = db.documentos.count_documents({})
            pdf_count = db.documentos.count_documents({"tipo": "pdf"})
            word_count = db.documentos.count_documents({"tipo": "word"})
            text_count = db.documentos.count_documents({"tipo": "texto"})
            
            st.markdown("### 📊 Estadísticas")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Docs", total_docs)
                st.metric("PDFs", pdf_count)
            with col2:
                st.metric("Word", word_count)
                st.metric("Texto", text_count)
        except:
            pass
    else:
        st.warning("⚠️ Configura la conexión a la base de datos")

# Función de conexión mejorada
@st.cache_resource(show_spinner="Conectando a la base de datos...")
def connect_mongodb(uri):
    try:
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client.documentation_db
        return db, True, "Conexión exitosa"
    except pymongo.errors.ServerSelectionTimeoutError:
        return None, False, "Error: Timeout de conexión"
    except pymongo.errors.ConnectionFailure:
        return None, False, "Error: No se pudo conectar al servidor"
    except Exception as e:
        return None, False, f"Error: {str(e)}"

# Funciones de procesamiento mejoradas
def procesar_archivo(archivo, tipo_archivo):
    try:
        contenido_binario = archivo.read()
        return Binary(contenido_binario), len(contenido_binario), None
    except Exception as e:
        return None, 0, f"Error procesando {tipo_archivo}: {e}"

# Función para descargar archivos mejorada
def crear_boton_descarga(contenido_binario, nombre_archivo, tipo_archivo):
    try:
        b64 = base64.b64encode(contenido_binario).decode()
        
        mime_types = {
            "pdf": "application/pdf",
            "word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "doc": "application/msword"
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

# Función de búsqueda mejorada
def buscar_documentos(db, criterio_busqueda, tipo_busqueda, filtros_adicionales=None):
    try:
        query = {}
        
        # Mapeo de tipos de búsqueda
        busqueda_map = {
            "nombre": "titulo",
            "autor": "autor",
            "contenido": "contenido",
            "tags": "tags",
            "categoria": "categoria",
            "ci": "ci",
            "descripcion": "descripcion"
        }
        
        campo = busqueda_map.get(tipo_busqueda)
        if campo:
            if tipo_busqueda == "tags":
                query[campo] = {"$in": [criterio_busqueda.strip()]}
            else:
                query[campo] = {"$regex": criterio_busqueda, "$options": "i"}
        
        # Aplicar filtros adicionales
        if filtros_adicionales:
            query.update(filtros_adicionales)
        
        # AGREGAR TIMESTAMP PARA INVALIDAR CACHE
        cache_key = st.session_state.get('last_delete_time', '')
        
        documentos = list(db.documentos.find(query).sort("fecha_creacion", -1))
        return documentos, None
        
    except Exception as e:
        return None, str(e)

# Función para mostrar documentos de manera COMPACTA
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
    
    # Crear tarjeta compacta
    with st.container():
        st.markdown(f'<div class="document-card">', unsafe_allow_html=True)
        
        col1, col2 = st.columns([5, 1])
        
        with col1:
            # Header compacto
            st.markdown(f"**{icono} {doc['titulo']}**")
            
            # Metadatos en línea compacta
            meta_col1, meta_col2, meta_col3 = st.columns(3)
            with meta_col1:
                st.markdown(f'<div class="compact-metadata">👤 **Autor:** {doc["autor"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="compact-metadata">📂 **Categoría:** {doc["categoria"]}</div>', unsafe_allow_html=True)
            with meta_col2:
                st.markdown(f'<div class="compact-metadata">🔢 **CI:** {doc.get("ci", "N/A")}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="compact-metadata">🔄 **Versión:** {doc["version"]}</div>', unsafe_allow_html=True)
            with meta_col3:
                st.markdown(f'<div class="compact-metadata">📅 **Fecha:** {doc["fecha_creacion"].strftime("%d/%m/%Y")}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="compact-metadata">⚡ **Prioridad:** {doc["prioridad"]}</div>', unsafe_allow_html=True)
            
            # Tags compactos
            if doc.get('tags'):
                tags_html = " ".join([f'<span class="tag">{tag}</span>' for tag in doc['tags']])
                st.markdown(f'<div class="compact-metadata">🏷️ **Tags:** {tags_html}</div>', unsafe_allow_html=True)
            
            # Información específica del tipo
            if doc.get('tipo') == 'texto':
                contenido_preview = doc['contenido'][:100] + "..." if len(doc['contenido']) > 100 else doc['contenido']
                st.markdown(f'<div class="compact-metadata">📝 **Contenido:** {contenido_preview}</div>', unsafe_allow_html=True)
            elif doc.get('tipo') in ['pdf', 'word']:
                st.markdown(f'<div class="compact-metadata">📋 **Archivo:** {doc.get("nombre_archivo", "N/A")}</div>', unsafe_allow_html=True)
                if doc.get('tamaño_bytes'):
                    tamaño_mb = doc['tamaño_bytes'] / (1024 * 1024)
                    st.markdown(f'<div class="compact-metadata">💾 **Tamaño:** {tamaño_mb:.2f} MB</div>', unsafe_allow_html=True)
                
                # Botón de descarga compacto
                if doc.get('contenido_binario'):
                    boton_descarga = crear_boton_descarga(
                        doc['contenido_binario'],
                        doc['nombre_archivo'],
                        doc['tipo']
                    )
                    st.markdown(boton_descarga, unsafe_allow_html=True)
            
            # ID único (pequeño y discreto)
            st.markdown(f'<div class="compact-metadata" style="font-size: 0.7rem; color: #999;">🆔 **ID:** {doc_id[:12]}...</div>', unsafe_allow_html=True)
        
        with col2:
            # Botón de eliminar compacto
            st.write("")  # Espacio
            if st.button("🗑️", key=f"delete_{doc_id}_{key_suffix}", help="Eliminar documento", use_container_width=True):
                with st.spinner("Eliminando..."):
                    try:
                        # Verificar que el documento existe antes de eliminar
                        doc_existente = db.documentos.find_one({"_id": doc["_id"]})
                        if not doc_existente:
                            st.error("❌ El documento ya no existe")
                            return
                        
                        # Eliminar el documento
                        result = db.documentos.delete_one({"_id": doc["_id"]})
                        
                        if result.deleted_count > 0:
                            st.success("✅ Documento eliminado")
                            
                            # ACTUALIZAR SESSION_STATE PARA INVALIDAR CACHE
                            st.session_state.last_delete_time = datetime.now().timestamp()
                            st.session_state.refresh_counter += 1
                            
                            # Esperar y recargar
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error("❌ No se pudo eliminar")
                            
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        
        st.markdown('</div>', unsafe_allow_html=True)

# Formulario reutilizable para documentos
def crear_formulario_documento(tipo_documento):
    """Crea un formulario reutilizable para diferentes tipos de documentos"""
    
    with st.form(f"form_{tipo_documento}", clear_on_submit=True):
        st.markdown(f"### 📝 Información del Documento")
        
        col1, col2 = st.columns(2)
        
        with col1:
            titulo = st.text_input(
                "**Título del documento** *",
                placeholder=f"Ej: Manual de Usuario {tipo_documento.upper()}",
                help="Nombre descriptivo del documento"
            )
            categoria = st.selectbox(
                "**Categoría** *",
                ["Técnica", "Usuario", "API", "Tutorial", "prueba", "Procedimiento", "Política", "Otros"],
                help="Categoría principal del documento"
            )
            autor = st.text_input(
                "**Autor** *",
                placeholder="Nombre completo del autor",
                help="Persona responsable del documento"
            )
            
        with col2:
            ci = st.text_input(
                "**CI/Cédula** *",
                placeholder="Número de identificación",
                help="Cédula de identidad del autor"
            )
            version = st.text_input(
                "**Versión**",
                value="1.0",
                placeholder="Ej: 1.2.3",
                help="Versión del documento"
            )
            tags_input = st.text_input(
                "**Etiquetas**",
                placeholder="tecnico,manual,instalacion",
                help="Separar con comas"
            )
            prioridad = st.select_slider(
                "**Prioridad**",
                options=["Baja", "Media", "Alta"],
                value="Media",
                help="Nivel de prioridad del documento"
            )
        
        # Campos específicos por tipo
        if tipo_documento == "texto":
            contenido = st.text_area(
                "**Contenido del documento** *",
                height=200,
                placeholder="Escribe el contenido completo del documento aquí...",
                help="Contenido principal en formato texto"
            )
        else:
            archivo = st.file_uploader(
                f"**Seleccionar archivo {tipo_documento.upper()}** *",
                type=[tipo_documento] if tipo_documento != 'word' else ['docx', 'doc'],
                help=f"Sube tu archivo {tipo_documento.upper()}"
            )
            descripcion = st.text_area(
                "**Descripción del documento**",
                height=80,
                placeholder="Breve descripción del contenido del archivo...",
                help="Resumen del contenido del documento"
            )
        
        submitted = st.form_submit_button(
            f"💾 Guardar Documento {tipo_documento.upper()}",
            use_container_width=True
        )
        
        if submitted:
            return validar_y_guardar_documento(tipo_documento, locals())
    
    return False

def validar_y_guardar_documento(tipo_documento, variables_locales):
    """Valida y guarda el documento en la base de datos"""
    
    # Extraer variables del contexto local
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
    
    # Preparar documento
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
        "fecha_actualizacion": datetime.utcnow()
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
        result = db.documentos.insert_one(documento)
        st.success(f"✅ Documento '{titulo}' guardado exitosamente!")
        st.balloons()
        return True
    except Exception as e:
        st.error(f"❌ Error al guardar: {str(e)}")
        return False

# --- FUNCIONES PARA CARGA MASIVA ---

def validar_csv_metadatos(df):
    """Valida la estructura del CSV de metadatos"""
    errores = []
    
    # Campos obligatorios
    if 'ci' not in df.columns:
        errores.append("Falta columna obligatoria: 'ci'")
    if 'nombre' not in df.columns:
        errores.append("Falta columna obligatoria: 'nombre'")
    
    if errores:
        return errores
    
    # Validar que CI sean únicos y válidos
    if df['ci'].isnull().any():
        errores.append("Hay valores nulos en la columna 'ci'")
    
    return errores

def buscar_archivos_por_ci(ruta_base, ci, tipos_archivo, procesar_subcarpetas):
    """Busca archivos para un CI específico"""
    try:
        ci_str = str(ci).strip()
        carpeta_ci = Path(ruta_base) / ci_str
        
        if not carpeta_ci.exists():
            return []
        
        archivos = []
        
        # Buscar en carpeta principal
        for extension in tipos_archivo:
            patron = f"*{extension}"
            if procesar_subcarpetas:
                archivos.extend(carpeta_ci.rglob(patron))
            else:
                archivos.extend(carpeta_ci.glob(patron))
        
        return archivos
    
    except Exception as e:
        return []

def procesar_archivo_masivo(archivo_path, ci, metadatos_ci, config):
    """Procesa un archivo individual para la carga masiva"""
    try:
        # Leer contenido binario
        with open(archivo_path, 'rb') as f:
            contenido_binario = Binary(f.read())
        
        # Determinar tipo de archivo
        extension = archivo_path.suffix.lower()
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
            nombre_archivo = archivo_path.stem
            titulo = f"{nombre_archivo} - {metadatos_ci['nombre']}"
        
        # Procesar etiquetas
        etiquetas = []
        if 'etiquetas' in metadatos_ci and pd.notna(metadatos_ci['etiquetas']):
            etiquetas = [tag.strip() for tag in str(metadatos_ci['etiquetas']).split(',')]
        
        # Agregar etiquetas automáticas
        etiquetas.extend([str(ci), 'carga_masiva', 'automático', tipo_archivo])
        
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
            "nombre_archivo": archivo_path.name,
            "contenido_binario": contenido_binario,
            "tamaño_bytes": len(contenido_binario),
            "ruta_original": str(archivo_path),
            "fecha_creacion": datetime.utcnow(),
            "fecha_actualizacion": datetime.utcnow(),
            "procesado_masivo": True,
            "lote_carga": config.get('lote_id')
        }
        
        return documento, None
        
    except Exception as e:
        return None, f"Error procesando {archivo_path}: {str(e)}"

def procesar_carga_masiva_ci(db, ruta_base, df_metadatos, tipos_archivo, max_documentos, 
                           tamaño_lote, procesar_subcarpetas, sobrescribir_existentes):
    """Función principal para procesar carga masiva por CI"""
    
    try:
        # Configuración
        config = {
            'lote_id': f"masivo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
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
        
        st.info("🔍 Buscando archivos en carpetas CI...")
        
        # Buscar archivos para cada CI en el CSV
        for _, fila in df_metadatos.iterrows():
            ci = fila['ci']
            archivos_ci = buscar_archivos_por_ci(ruta_base, ci, tipos_archivo, procesar_subcarpetas)
            
            if archivos_ci:
                cis_procesados += 1
                for archivo in archivos_ci:
                    if total_archivos < max_documentos:
                        todos_documentos.append((archivo, ci, fila.to_dict()))
                        total_archivos += 1
                    else:
                        break
            
            if total_archivos >= max_documentos:
                break
        
        if not todos_documentos:
            st.warning("⚠️ No se encontraron archivos para procesar")
            return
        
        st.success(f"🎯 Encontrados {total_archivos} archivos en {cis_procesados} carpetas CI")
        
        # Configurar interfaz de progreso
        progress_bar = st.progress(0)
        status_text = st.empty()
        resultados_container = st.container()
        
        # Procesar por lotes
        for i in range(0, len(todos_documentos), tamaño_lote):
            lote_actual = todos_documentos[i:i + tamaño_lote]
            documentos_a_insertar = []
            
            for archivo_path, ci, metadatos in lote_actual:
                # Verificar duplicados si no se permite sobrescribir
                if not sobrescribir_existentes:
                    existe = db.documentos.count_documents({
                        "nombre_archivo": archivo_path.name,
                        "ci": str(ci)
                    }) > 0
                    
                    if existe:
                        documentos_duplicados += 1
                        continue
                
                # Procesar archivo
                documento, error = procesar_archivo_masivo(archivo_path, ci, metadatos, config)
                
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
            st.markdown("### 📈 Resultados Finales")
            
            # Métricas principales
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Archivos Encontrados", len(todos_documentos))
            with col2:
                st.metric("Procesados Exitosos", documentos_exitosos,
                         delta=f"{(documentos_exitosos/len(todos_documentos)*100):.1f}%")
            with col3:
                st.metric("Fallidos", documentos_fallidos,
                         delta=f"-{(documentos_fallidos/len(todos_documentos)*100):.1f}%" if documentos_fallidos > 0 else None,
                         delta_color="inverse")
            with col4:
                st.metric("CIs Procesados", cis_procesados)
            
            if documentos_exitosos > 0:
                st.success(f"🎉 Carga masiva completada! {documentos_exitosos} documentos procesados exitosamente.")
                st.balloons()
            
            if documentos_duplicados > 0:
                st.info(f"💡 {documentos_duplicados} documentos no se procesaron por duplicados. "
                       "Marca 'Sobrescribir documentos existentes' para forzar el reprocesamiento.")
                
    except Exception as e:
        st.error(f"❌ Error en el procesamiento masivo: {str(e)}")

# --- FUNCIÓN SIMPLIFICADA PARA CREAR PLANTILLA CSV ---

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
    
    # Crear archivo CSV en memoria
    output = io.BytesIO()
    df_plantilla.to_csv(output, index=False, encoding='utf-8')
    output.seek(0)
    
    # Botón de descarga CSV
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

# --- APLICACIÓN PRINCIPAL ---

if mongo_uri:
    db, connected, connection_message = connect_mongodb(mongo_uri)
    
    if connected:
        st.success(f"🚀 {connection_message}")
        
        # --- PESTAÑAS REORGANIZADAS ---
        st.markdown("---")
        st.markdown("## 📁 Gestión de Documentos")
        
        # NUEVA ORGANIZACIÓN DE PESTAÑAS
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "🔍 Buscar Documentos", 
            "📝 Crear Texto", 
            "📄 Subir PDF", 
            "📝 Subir Word", 
            "📂 Todos los Documentos",
            "🚀 Carga Masiva",
            "💾 Carga Local"
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
                        key="busqueda_principal"
                    )
                
                with col2:
                    tipo_busqueda = st.selectbox(
                        "**Buscar por:**",
                        ["nombre", "autor", "contenido", "tags", "categoria", "ci", "descripcion"],
                        format_func=lambda x: {
                            "nombre": "📄 Nombre del documento",
                            "autor": "👤 Autor", 
                            "contenido": "📝 Contenido",
                            "tags": "🏷️ Etiquetas",
                            "categoria": "📂 Categoría",
                            "ci": "🔢 CI/Cédula",
                            "descripcion": "📋 Descripción"
                        }[x]
                    )
                
                with col3:
                    st.write("")
                    st.write("")
                    buscar_btn = st.button("🔎 Ejecutar Búsqueda", use_container_width=True)
            
            # Filtros adicionales compactos
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                filtro_tipo_busq = st.selectbox("Filtrar por tipo", ["Todos", "Texto", "PDF", "Word", "Imagen"])
            with col_f2:
                filtro_categoria_busq = st.selectbox("Filtrar por categoría", ["Todas"] + ["Técnica", "Usuario", "API", "Tutorial", "Referencia", "Procedimiento", "Política", "Otros"])
            with col_f3:
                filtro_prioridad_busq = st.selectbox("Filtrar por prioridad", ["Todas", "Alta", "Media", "Baja"])
            
            # Realizar búsqueda
            if buscar_btn and criterio_busqueda:
                with st.spinner("🔍 Buscando en la base de datos..."):
                    # Preparar filtros adicionales
                    filtros_adicionales = {}
                    if filtro_tipo_busq != "Todos":
                        filtros_adicionales["tipo"] = filtro_tipo_busq.lower()
                    if filtro_categoria_busq != "Todas":
                        filtros_adicionales["categoria"] = filtro_categoria_busq
                    if filtro_prioridad_busq != "Todas":
                        filtros_adicionales["prioridad"] = filtro_prioridad_busq
                    
                    # USAR TIMESTAMP PARA EVITAR CACHE
                    cache_buster = st.session_state.get('last_delete_time', '')
                    
                    documentos_encontrados, error = buscar_documentos(
                        db, criterio_busqueda, tipo_busqueda, filtros_adicionales
                    )
                    
                    if error:
                        st.error(f"❌ Error en búsqueda: {error}")
                    elif documentos_encontrados:
                        st.success(f"✅ Encontrados {len(documentos_encontrados)} documento(s)")
                        
                        # Mostrar resultados en formato compacto
                        for i, doc in enumerate(documentos_encontrados):
                            mostrar_documento_compacto(doc, f"search_{i}")
                    else:
                        st.info("🔍 No se encontraron documentos con esos criterios")
            
            elif buscar_btn and not criterio_busqueda:
                st.warning("⚠️ Ingresa un término de búsqueda")
        
        # PESTAÑA 2: Crear Texto Simple
        with tab2:
            st.markdown("### Crear Documento de Texto")
            crear_formulario_documento("texto")
        
        # PESTAÑA 3: Subir PDF
        with tab3:
            st.markdown("### Subir Documento PDF")
            crear_formulario_documento("pdf")
        
        # PESTAÑA 4: Subir Word
        with tab4:
            st.markdown("### Subir Documento Word")
            crear_formulario_documento("word")
        
        # PESTAÑA 5: Todos los Documentos
        with tab5:
            st.markdown("### 📂 Biblioteca de Documentos")
            
            # Filtros avanzados compactos
            with st.expander("**🎛️ Filtros Avanzados**", expanded=False):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    filtro_tipo = st.selectbox("Tipo de documento", ["Todos", "Texto", "PDF", "Word", "Imagen"], key="filtro_tipo_all")
                with col2:
                    filtro_categoria = st.selectbox("Categoría", ["Todas"] + ["Técnica", "Usuario", "API", "Tutorial", "Referencia", "Procedimiento", "Política", "Otros"], key="filtro_categoria_all")
                with col3:
                    filtro_prioridad = st.selectbox("Prioridad", ["Todas", "Alta", "Media", "Baja"], key="filtro_prioridad_all")
                with col4:
                    fecha_desde = st.date_input("Desde fecha", key="fecha_desde")
            
            # Búsqueda rápida
            busqueda_rapida = st.text_input("🔍 Búsqueda rápida por título o CI", key="busqueda_rapida_all")
            
            # Construir query
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
                    {"autor": {"$regex": busqueda_rapida, "$options": "i"}}
                ]
            
            try:
                # USAR TIMESTAMP PARA EVITAR CACHE
                cache_buster = st.session_state.get('last_delete_time', '')
                
                with st.spinner("Cargando documentos..."):
                    documentos = list(db.documentos.find(query).sort("fecha_creacion", -1))
                
                if documentos:
                    st.info(f"📊 Mostrando {len(documentos)} documento(s)")
                    
                    # Mostrar en formato compacto
                    for i, doc in enumerate(documentos):
                        mostrar_documento_compacto(doc, f"all_{i}")
                else:
                    st.info("📝 No se encontraron documentos. ¡Agrega el primero en las pestañas de arriba!")
                    
            except Exception as e:
                st.error(f"❌ Error al cargar documentos: {str(e)}")
        
        # PESTAÑA 6: Carga Masiva por CI
        with tab6:
            st.markdown("### 🚀 Carga Masiva de Archivos")
            st.info("""
            **Carga masiva de documentos organizados por carpetas de CI**
            - Estructura: `C:/ruta/carpetas/CI/archivos.pdf`
            - Soporta: PDF, Word, imágenes, texto
            - Metadatos automáticos desde CSV
            - Hasta 10,000 documentos por carga
            """)
            
            # Configuración en dos columnas
            col_config1, col_config2 = st.columns(2)
            
            with col_config1:
                st.markdown("#### 📁 Configuración de Carpetas")
                ruta_base = st.text_input(
                    "**Ruta base de carpetas CI** *",
                    value="C:\\documentos\\",
                    placeholder="C:\\ruta\\carpetas_ci\\",
                    help="Ruta donde están las carpetas organizadas por número de CI"
                )
                
                tipos_archivo = st.multiselect(
                    "**Tipos de archivo a procesar** *",
                    ['.pdf', '.docx', '.doc', '.jpg', '.jpeg', '.png', '.txt'],
                    default=['.pdf', '.docx', '.doc'],
                    help="Selecciona los tipos de archivo a incluir"
                )
                
                procesar_subcarpetas = st.checkbox(
                    "**Procesar subcarpetas dentro de cada CI**",
                    value=True,
                    help="Buscar documentos en subcarpetas dentro de cada carpeta de CI"
                )
            
            with col_config2:
                st.markdown("#### 📊 Configuración de Procesamiento")
                max_documentos = st.number_input(
                    "**Límite de documentos**",
                    min_value=100,
                    max_value=10000,
                    value=3000,
                    step=100,
                    help="Máximo número de documentos a procesar"
                )
                
                tamaño_lote = st.slider(
                    "**Tamaño del lote**",
                    min_value=50,
                    max_value=500,
                    value=100,
                    help="Documentos procesados por lote (mejora performance)"
                )
                
                sobrescribir_existentes = st.checkbox(
                    "**Sobrescribir documentos existentes**",
                    value=False,
                    help="Reemplazar documentos que ya existen en la base de datos"
                )
            
            # Sección para CSV de metadatos
            st.markdown("#### 📋 Archivo CSV con Metadatos")
            st.info("""
            **El CSV debe contener las columnas:**
            - `ci` (obligatorio): Número de cédula
            - `nombre` (obligatorio): Nombre completo
            - `titulo`: Título del documento (si no se especifica, se genera automáticamente)
            - `categoria`: Categoría del documento
            - `autor`: Autor del documento  
            - `version`: Versión del documento
            - `etiquetas`: Tags separados por comas
            - `prioridad`: Baja, Media, Alta
            """)
            
            archivo_csv = st.file_uploader(
                "**Subir CSV con metadatos** *",
                type=['csv'],
                help="CSV con información de CI, nombres, títulos, etc."
            )
            
            # Previsualización del CSV
            if archivo_csv:
                try:
                    df_metadatos = pd.read_csv(archivo_csv)
                    st.success(f"✅ CSV cargado: {len(df_metadatos)} registros de CI encontrados")
                    
                    with st.expander("📊 Vista previa del CSV", expanded=True):
                        st.dataframe(df_metadatos.head(10), use_container_width=True)
                        
                        # Estadísticas del CSV
                        col_stats1, col_stats2, col_stats3 = st.columns(3)
                        with col_stats1:
                            st.metric("Total CIs", len(df_metadatos))
                        with col_stats2:
                            st.metric("Columnas", len(df_metadatos.columns))
                        with col_stats3:
                            cis_unicos = df_metadatos['ci'].nunique() if 'ci' in df_metadatos.columns else 0
                            st.metric("CIs Únicos", cis_unicos)
                
                except Exception as e:
                    st.error(f"❌ Error al leer el CSV: {str(e)}")
            
            # Sección para descargar plantilla
            st.markdown("---")
            st.markdown("#### 🧪 Generar Plantilla")
            crear_plantilla_carga_masiva()
            
            # Botón de procesamiento
            st.markdown("#### ⚡ Procesamiento Masivo")
            
            if st.button("🚀 Iniciar Carga Masiva", type="primary", use_container_width=True):
                if not archivo_csv:
                    st.error("❌ Debes subir un archivo CSV con los metadatos")
                elif not ruta_base:
                    st.error("❌ Debes especificar la ruta base de las carpetas CI")
                elif not tipos_archivo:
                    st.error("❌ Debes seleccionar al menos un tipo de archivo")
                else:
                    # Validar estructura del CSV
                    try:
                        df_metadatos = pd.read_csv(archivo_csv)
                        errores = validar_csv_metadatos(df_metadatos)
                        
                        if errores:
                            st.error("❌ Errores en el CSV:")
                            for error in errores:
                                st.write(f"• {error}")
                        else:
                            # Procesar carga masiva
                            with st.spinner("🔄 Iniciando procesamiento masivo..."):
                                resultado = procesar_carga_masiva_ci(
                                    db=db,
                                    ruta_base=ruta_base,
                                    df_metadatos=df_metadatos,
                                    tipos_archivo=tipos_archivo,
                                    max_documentos=max_documentos,
                                    tamaño_lote=tamaño_lote,
                                    procesar_subcarpetas=procesar_subcarpetas,
                                    sobrescribir_existentes=sobrescribir_existentes
                                )
                    
                    except Exception as e:
                        st.error(f"❌ Error en validación: {str(e)}")

        # PESTAÑA 7: Carga Masiva con Archivos Locales
        with tab7:
            st.markdown("### 💾 Carga Masiva (Archivos Locales)")
            st.info("""
            **Carga masiva manteniendo archivos en sistema local**
            - Estructura: `C:/subir_archivos/archivos_con_CI_en_nombre.pdf`
            - Solo metadatos en MongoDB, archivos permanecen en carpeta local
            - Soporta: PDF, Word, imágenes, texto
            - Hasta 10,000 documentos por carga
            """)
            
            # Configuración simplificada
            col_config1, col_config2 = st.columns(2)
            
            with col_config1:
                ruta_base_local = st.text_input(
                    "**Ruta de carpeta de archivos** *",
                    value="C:\\subir_archivos\\",
                    placeholder="C:\\subir_archivos\\",
                    help="Ruta donde están todos los archivos"
                )
                
                tipos_archivo_local = st.multiselect(
                    "**Tipos de archivo a procesar** *",
                    ['.pdf', '.docx', '.doc', '.jpg', '.jpeg', '.png', '.txt'],
                    default=['.pdf', '.docx', '.doc'],
                    help="Selecciona los tipos de archivo a incluir"
                )
            
            with col_config2:
                max_documentos_local = st.number_input(
                    "**Límite de documentos**",
                    min_value=100,
                    max_value=10000,
                    value=3000,
                    step=100,
                    help="Máximo número de documentos a procesar"
                )
                
                patron_busqueda = st.selectbox(
                    "**Patrón de búsqueda de CI**",
                    ["CI al inicio", "CI en cualquier parte", "CI específico en nombre"],
                    help="Cómo buscar el CI en los nombres de archivo"
                )
            
            archivo_csv_local = st.file_uploader(
                "**Subir CSV con metadatos** *",
                type=['csv'],
                help="CSV con información de CI, nombres, títulos, etc."
            )
            
            if st.button("🚀 Iniciar Carga Local", type="primary", use_container_width=True):
                st.info("ℹ️ Esta funcionalidad está disponible en la versión completa")

    else:
        st.error(f"❌ {connection_message}")

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
