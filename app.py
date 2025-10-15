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
from PIL import Image
import time

# Configuración de la página
st.set_page_config(
    page_title="Sistema de Gestión Documental",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
</style>
""", unsafe_allow_html=True)

# Título principal mejorado
st.markdown('<h1 class="main-header">📚 Sistema de Gestión Documental</h1>', unsafe_allow_html=True)
st.markdown('<p class="subheader">Gestión centralizada de documentos con búsqueda avanzada y control de versiones</p>', unsafe_allow_html=True)

# Sidebar mejorado
with st.sidebar:
    st.markdown("## 🔐 Configuración")
    
    # Logo o imagen de la empresa
    st.image("https://media.marathon.store/images/hde/h28/h00/8926515298334.png", width=80)
    
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
           style="background-color: #4CAF50; color: white; padding: 10px 15px; 
                  text-decoration: none; border-radius: 5px; display: inline-block;
                  font-weight: bold;">
           📥 Descargar {nombre_archivo}
        </a>
        '''
        st.markdown(href, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"❌ Error creando botón de descarga: {e}")

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
        
        documentos = list(db.documentos.find(query).sort("fecha_creacion", -1))
        return documentos, None
        
    except Exception as e:
        return None, str(e)

# Función para mostrar documentos de manera consistente
def mostrar_documento(doc, key_suffix=""):
    """Muestra un documento en un formato consistente y profesional"""
    
    iconos = {
        "pdf": "📄",
        "word": "📝", 
        "texto": "📃"
    }
    
    icono = iconos.get(doc.get('tipo'), '📎')
    
    with st.container():
        col1, col2 = st.columns([4, 1])
        
        with col1:
            # Header del documento
            st.markdown(f"### {icono} {doc['titulo']}")
            
            # Metadatos en columnas
            meta_col1, meta_col2, meta_col3 = st.columns(3)
            with meta_col1:
                st.caption(f"**Autor:** {doc['autor']}")
                st.caption(f"**Categoría:** {doc['categoria']}")
            with meta_col2:
                st.caption(f"**Versión:** {doc['version']}")
                st.caption(f"**Prioridad:** {doc['prioridad']}")
            with meta_col3:
                st.caption(f"**CI:** {doc.get('ci', 'N/A')}")
                st.caption(f"**Fecha:** {doc['fecha_creacion'].strftime('%d/%m/%Y %H:%M')}")
            
            # Tags
            if doc.get('tags'):
                tags_html = " ".join([f"<span style='background-color: #e0e0e0; padding: 2px 8px; border-radius: 10px; margin: 2px; display: inline-block;'>{tag}</span>" for tag in doc['tags']])
                st.markdown(f"**Tags:** {tags_html}", unsafe_allow_html=True)
            
            # Contenido específico por tipo
            st.markdown("---")
            if doc.get('tipo') == 'texto':
                st.markdown("**Contenido:**")
                st.write(doc['contenido'])
            elif doc.get('tipo') in ['pdf', 'word']:
                st.write(f"**Descripción:** {doc.get('descripcion', 'Sin descripción')}")
                st.write(f"**Archivo:** {doc.get('nombre_archivo', 'N/A')}")
                if doc.get('tamaño_bytes'):
                    tamaño_mb = doc['tamaño_bytes'] / (1024 * 1024)
                    st.write(f"**Tamaño:** {tamaño_mb:.2f} MB")
                
                if doc.get('contenido_binario'):
                    crear_boton_descarga(
                        doc['contenido_binario'],
                        doc['nombre_archivo'],
                        doc['tipo']
                    )
        
        with col2:
            # Botones de acción
            st.write("")  # Espacio
            if st.button("🗑️ Eliminar", key=f"delete_{doc['_id']}_{key_suffix}", use_container_width=True):
                with st.spinner("Eliminando..."):
                    db.documentos.delete_one({"_id": doc["_id"]})
                    st.success("✅ Documento eliminado")
                    time.sleep(1)
                    st.rerun()
            
            if st.button("📋 Copiar ID", key=f"copy_{doc['_id']}_{key_suffix}", use_container_width=True):
                st.code(str(doc['_id']), language='text')
                st.success("ID copiado al portapapeles")

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
                ["Técnica", "Usuario", "API", "Tutorial", "Referencia", "Procedimiento", "Política", "Otros"],
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
                height=250,
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
                height=100,
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

# --- APLICACIÓN PRINCIPAL ---

if mongo_uri:
    db, connected, connection_message = connect_mongodb(mongo_uri)
    
    if connected:
        st.success(f"🚀 {connection_message}")
        
        # --- SECCIÓN DE BÚSQUEDA AVANZADA MEJORADA ---
        st.markdown("---")
        st.markdown("## 🔍 Búsqueda Avanzada")
        
        with st.expander("**Opciones de Búsqueda**", expanded=True):
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
        
        # Filtros adicionales
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filtro_tipo_busq = st.selectbox("Filtrar por tipo", ["Todos", "Texto", "PDF", "Word"])
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
                
                documentos_encontrados, error = buscar_documentos(
                    db, criterio_busqueda, tipo_busqueda, filtros_adicionales
                )
                
                if error:
                    st.error(f"❌ Error en búsqueda: {error}")
                elif documentos_encontrados:
                    st.success(f"✅ Encontrados {len(documentos_encontrados)} documento(s)")
                    
                    # Mostrar resultados
                    for i, doc in enumerate(documentos_encontrados):
                        mostrar_documento(doc, f"search_{i}")
                else:
                    st.info("🔍 No se encontraron documentos con esos criterios")
        
        elif buscar_btn and not criterio_busqueda:
            st.warning("⚠️ Ingresa un término de búsqueda")
        
        # --- PESTAÑAS MEJORADAS ---
        st.markdown("---")
        st.markdown("## 📁 Gestión de Documentos")
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "📝 Texto Simple", 
            "📄 Subir PDF", 
            "📝 Subir Word", 
            "📂 Todos los Documentos"
        ])
        
        # Pestaña 1: Texto Simple
        with tab1:
            st.markdown("### Crear Documento de Texto")
            crear_formulario_documento("texto")
        
        # Pestaña 2: PDF
        with tab2:
            st.markdown("### Subir Documento PDF")
            crear_formulario_documento("pdf")
        
        # Pestaña 3: Word
        with tab3:
            st.markdown("### Subir Documento Word")
            crear_formulario_documento("word")
        
        # Pestaña 4: Todos los Documentos
        with tab4:
            st.markdown("### Biblioteca de Documentos")
            
            # Filtros avanzados
            with st.expander("**Filtros Avanzados**", expanded=True):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    filtro_tipo = st.selectbox("Tipo de documento", ["Todos", "Texto", "PDF", "Word"], key="filtro_tipo_all")
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
                with st.spinner("Cargando documentos..."):
                    documentos = list(db.documentos.find(query).sort("fecha_creacion", -1))
                
                if documentos:
                    st.info(f"📊 Mostrando {len(documentos)} documento(s)")
                    
                    for i, doc in enumerate(documentos):
                        mostrar_documento(doc, f"all_{i}")
                else:
                    st.info("📝 No se encontraron documentos. ¡Agrega el primero en las pestañas de arriba!")
                    
            except Exception as e:
                st.error(f"❌ Error al cargar documentos: {str(e)}")

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


