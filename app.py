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
    st.image("data:image/jpeg;base64,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", width=80)
    
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



