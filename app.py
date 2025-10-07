import streamlit as st
import pymongo
from datetime import datetime
import os
import io
import base64
from bson import Binary
from bson.binary import Binary
import tempfile

# Configuración de la página
st.set_page_config(
    page_title="Sistema de Documentación + Archivos",
    page_icon="📄",
    layout="wide"
)

# Título principal
st.title("📄 Sistema de Documentación con Archivos")
st.markdown("Sube documentos en texto, PDF o Word")
st.markdown("---")

# Sidebar para configuración
with st.sidebar:
    st.header("🔧 Configuración MongoDB")
    
    mongo_uri = st.text_input(
        "Cadena de Conexión MongoDB",
        type="password",
        placeholder="mongodb+srv://usuario_documentos:Gloria1312@cluster...",
        help="Pega tu MONGO_URI de MongoDB Atlas"
    )
    
    if mongo_uri:
        st.success("✅ URI configurada")
    else:
        st.warning("⚠️ Ingresa tu MONGO_URI")

# Función de conexión a MongoDB
def connect_mongodb(uri):
    try:
        client = pymongo.MongoClient(uri)
        client.admin.command('ping')
        db = client.documentation_db
        return db, True
    except Exception as e:
        st.error(f"❌ Error de conexión: {str(e)}")
        return None, False

# Procesar archivos PDF
def procesar_pdf(archivo):
    try:
        # Leer el contenido binario del PDF
        contenido_binario = archivo.read()
        return Binary(contenido_binario)
    except Exception as e:
        st.error(f"Error procesando PDF: {e}")
        return None

# Procesar archivos Word (.docx)
def procesar_word(archivo):
    try:
        # Leer el contenido binario del Word
        contenido_binario = archivo.read()
        return Binary(contenido_binario)
    except Exception as e:
        st.error(f"Error procesando Word: {e}")
        return None

# Función para descargar archivos
def crear_boton_descarga(contenido_binario, nombre_archivo, tipo_archivo):
    try:
        # Codificar en base64 para el descargable
        b64 = base64.b64encode(contenido_binario).decode()
        
        if tipo_archivo == "pdf":
            mime_type = "application/pdf"
            icono = "📄"
        elif tipo_archivo == "word":
            mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            icono = "📝"
        else:
            mime_type = "application/octet-stream"
            icono = "📎"
        
        href = f'<a href="data:{mime_type};base64,{b64}" download="{nombre_archivo}" style="text-decoration: none;">{icono} Descargar {nombre_archivo}</a>'
        st.markdown(href, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Error creando botón de descarga: {e}")

# Solo intentar conexión si hay URI
if mongo_uri:
    db, connected = connect_mongodb(mongo_uri)
    
    if connected:
        st.success("🚀 Conectado a MongoDB Cloud!")
        
        # Pestañas para diferentes tipos de contenido
        tab1, tab2, tab3 = st.tabs(["📝 Texto Simple", "📄 Subir PDF", "📝 Subir Word"])
        
        # --- PESTAÑA 1: TEXTO SIMPLE ---
        with tab1:
            st.header("📝 Agregar Documento de Texto")
            
            with st.form("nuevo_documento_texto", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    titulo = st.text_input("Título del documento*", placeholder="Ej: Guía de Instalación", key="texto_titulo")
                    categoria = st.selectbox(
                        "Categoría*", 
                        ["Técnica", "Usuario", "API", "Tutorial", "Referencia", "Otros"],
                        key="texto_categoria"
                    )
                    autor = st.text_input("Autor*", placeholder="Tu nombre", key="texto_autor")
                    
                with col2:
                    version = st.text_input("Versión", value="1.0", key="texto_version")
                    tags_input = st.text_input("Tags", placeholder="python,documentación,sistema", key="texto_tags")
                    prioridad = st.select_slider("Prioridad", options=["Baja", "Media", "Alta"], key="texto_prioridad")
                
                contenido = st.text_area(
                    "Contenido del documento*", 
                    height=200,
                    placeholder="Escribe el contenido completo del documento aquí...",
                    key="texto_contenido"
                )
                
                submitted_texto = st.form_submit_button("💾 Guardar Documento de Texto")
                
                if submitted_texto:
                    if titulo and contenido and autor:
                        tags = [tag.strip() for tag in tags_input.split(",")] if tags_input else []
                        
                        documento = {
                            "titulo": titulo,
                            "contenido": contenido,
                            "categoria": categoria,
                            "autor": autor,
                            "version": version,
                            "tags": tags,
                            "prioridad": prioridad,
                            "tipo": "texto",
                            "fecha_creacion": datetime.utcnow(),
                            "fecha_actualizacion": datetime.utcnow()
                        }
                        
                        try:
                            result = db.documentos.insert_one(documento)
                            st.success(f"✅ Documento de texto '{titulo}' guardado exitosamente!")
                            st.balloons()
                        except Exception as e:
                            st.error(f"❌ Error al guardar: {str(e)}")
                    else:
                        st.warning("⚠️ Completa los campos obligatorios (*)")
        
        # --- PESTAÑA 2: SUBIR PDF ---
        with tab2:
            st.header("📄 Subir Documento PDF")
            
            with st.form("subir_pdf", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    titulo_pdf = st.text_input("Título del documento*", placeholder="Ej: Manual de Usuario PDF", key="pdf_titulo")
                    categoria_pdf = st.selectbox(
                        "Categoría*", 
                        ["Técnica", "Usuario", "API", "Tutorial", "Referencia", "Otros"],
                        key="pdf_categoria"
                    )
                    autor_pdf = st.text_input("Autor*", placeholder="Tu nombre", key="pdf_autor")
                    
                with col2:
                    version_pdf = st.text_input("Versión", value="1.0", key="pdf_version")
                    tags_pdf = st.text_input("Tags", placeholder="pdf,manual,usuario", key="pdf_tags")
                    prioridad_pdf = st.select_slider("Prioridad", options=["Baja", "Media", "Alta"], key="pdf_prioridad")
                
                archivo_pdf = st.file_uploader(
                    "Selecciona un archivo PDF*", 
                    type=['pdf'],
                    key="pdf_uploader"
                )
                
                descripcion_pdf = st.text_area(
                    "Descripción del documento",
                    placeholder="Breve descripción del contenido del PDF...",
                    key="pdf_descripcion"
                )
                
                submitted_pdf = st.form_submit_button("📄 Subir PDF")
                
                if submitted_pdf:
                    if titulo_pdf and archivo_pdf and autor_pdf:
                        # Procesar el PDF
                        contenido_pdf = procesar_pdf(archivo_pdf)
                        
                        if contenido_pdf:
                            documento_pdf = {
                                "titulo": titulo_pdf,
                                "descripcion": descripcion_pdf,
                                "categoria": categoria_pdf,
                                "autor": autor_pdf,
                                "version": version_pdf,
                                "tags": [tag.strip() for tag in tags_pdf.split(",")] if tags_pdf else [],
                                "prioridad": prioridad_pdf,
                                "tipo": "pdf",
                                "nombre_archivo": archivo_pdf.name,
                                "contenido_binario": contenido_pdf,
                                "tamaño_bytes": len(contenido_pdf),
                                "fecha_creacion": datetime.utcnow(),
                                "fecha_actualizacion": datetime.utcnow()
                            }
                            
                            try:
                                result = db.documentos.insert_one(documento_pdf)
                                st.success(f"✅ PDF '{archivo_pdf.name}' subido exitosamente!")
                                st.balloons()
                            except Exception as e:
                                st.error(f"❌ Error al subir PDF: {str(e)}")
                    else:
                        st.warning("⚠️ Completa los campos obligatorios (*) y selecciona un archivo PDF")
        
        # --- PESTAÑA 3: SUBIR WORD ---
        with tab3:
            st.header("📝 Subir Documento Word")
            
            with st.form("subir_word", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    titulo_word = st.text_input("Título del documento*", placeholder="Ej: Reporte Técnico", key="word_titulo")
                    categoria_word = st.selectbox(
                        "Categoría*", 
                        ["Técnica", "Usuario", "API", "Tutorial", "Referencia", "Otros"],
                        key="word_categoria"
                    )
                    autor_word = st.text_input("Autor*", placeholder="Tu nombre", key="word_autor")
                    
                with col2:
                    version_word = st.text_input("Versión", value="1.0", key="word_version")
                    tags_word = st.text_input("Tags", placeholder="word,reporte,tecnico", key="word_tags")
                    prioridad_word = st.select_slider("Prioridad", options=["Baja", "Media", "Alta"], key="word_prioridad")
                
                archivo_word = st.file_uploader(
                    "Selecciona un archivo Word*", 
                    type=['docx', 'doc'],
                    key="word_uploader"
                )
                
                descripcion_word = st.text_area(
                    "Descripción del documento",
                    placeholder="Breve descripción del contenido del Word...",
                    key="word_descripcion"
                )
                
                submitted_word = st.form_submit_button("📝 Subir Word")
                
                if submitted_word:
                    if titulo_word and archivo_word and autor_word:
                        # Procesar el Word
                        contenido_word = procesar_word(archivo_word)
                        
                        if contenido_word:
                            documento_word = {
                                "titulo": titulo_word,
                                "descripcion": descripcion_word,
                                "categoria": categoria_word,
                                "autor": autor_word,
                                "version": version_word,
                                "tags": [tag.strip() for tag in tags_word.split(",")] if tags_word else [],
                                "prioridad": prioridad_word,
                                "tipo": "word",
                                "nombre_archivo": archivo_word.name,
                                "contenido_binario": contenido_word,
                                "tamaño_bytes": len(contenido_word),
                                "fecha_creacion": datetime.utcnow(),
                                "fecha_actualizacion": datetime.utcnow()
                            }
                            
                            try:
                                result = db.documentos.insert_one(documento_word)
                                st.success(f"✅ Word '{archivo_word.name}' subido exitosamente!")
                                st.balloons()
                            except Exception as e:
                                st.error(f"❌ Error al subir Word: {str(e)}")
                    else:
                        st.warning("⚠️ Completa los campos obligatorios (*) y selecciona un archivo Word")

        # --- SECCIÓN PARA VER TODOS LOS DOCUMENTOS ---
        st.header("📂 Todos los Documentos")
        
        # Filtros
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filtro_tipo = st.selectbox(
                "Tipo de documento",
                ["Todos", "Texto", "PDF", "Word"]
            )
        with col2:
            filtro_categoria = st.selectbox(
                "Categoría",
                ["Todas"] + ["Técnica", "Usuario", "API", "Tutorial", "Referencia", "Otros"]
            )
        with col3:
            filtro_prioridad = st.selectbox(
                "Prioridad", 
                ["Todas", "Alta", "Media", "Baja"]
            )
        with col4:
            busqueda = st.text_input("🔍 Buscar por título")

        # Construir query de filtro
        query = {}
        if filtro_tipo != "Todos":
            query["tipo"] = filtro_tipo.lower()
        if filtro_categoria != "Todas":
            query["categoria"] = filtro_categoria
        if filtro_prioridad != "Todas":
            query["prioridad"] = filtro_prioridad
        if busqueda:
            query["titulo"] = {"$regex": busqueda, "$options": "i"}

        try:
            documentos = list(db.documentos.find(query).sort("fecha_creacion", -1))
            
            if documentos:
                st.info(f"📊 Mostrando {len(documentos)} documento(s)")
                
                for doc in documentos:
                    # Icono según el tipo
                    icono = "📄" if doc.get('tipo') == 'pdf' else "📝" if doc.get('tipo') == 'word' else "📃"
                    
                    with st.expander(
                        f"{icono} **{doc['titulo']}** - "
                        f"_{doc.get('tipo', 'texto').upper()}_ - "
                        f"_{doc['categoria']}_ - "
                        f"Prioridad: {doc['prioridad']} - "
                        f"📅 {doc['fecha_creacion'].strftime('%d/%m/%Y')}"
                    ):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**Autor:** {doc['autor']}")
                            st.write(f"**Versión:** {doc['version']}")
                            st.write(f"**Tags:** {', '.join(doc['tags']) if doc['tags'] else 'Ninguno'}")
                            
                            if doc.get('tipo') == 'texto':
                                st.write("---")
                                st.write(f"**Contenido:**")
                                st.write(doc['contenido'])
                            elif doc.get('tipo') in ['pdf', 'word']:
                                st.write(f"**Descripción:** {doc.get('descripcion', 'Sin descripción')}")
                                st.write(f"**Archivo:** {doc.get('nombre_archivo', 'N/A')}")
                                st.write(f"**Tamaño:** {doc.get('tamaño_bytes', 0)} bytes")
                                
                                # Botón para descargar archivo
                                if doc.get('contenido_binario'):
                                    crear_boton_descarga(
                                        doc['contenido_binario'],
                                        doc['nombre_archivo'],
                                        doc['tipo']
                                    )
                        
                        with col2:
                            if st.button("🗑️ Eliminar", key=f"delete_{doc['_id']}"):
                                db.documentos.delete_one({"_id": doc["_id"]})
                                st.success("Documento eliminado")
                                st.rerun()
            else:
                st.info("📝 No se encontraron documentos. ¡Agrega el primero arriba!")
                
        except Exception as e:
            st.error(f"❌ Error al cargar documentos: {str(e)}")

else:
    st.info("👈 Ingresa tu cadena de conexión MongoDB en la barra lateral para comenzar")

# Footer
st.markdown("---")
st.caption("Sistema de Documentación - Soporte para Texto, PDF y Word")

