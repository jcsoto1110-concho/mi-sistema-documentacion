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
st.title("📄 Sistema de Documentación con Búsqueda Avanzada")
st.markdown("Busca documentos por nombre, CI, identificación, autor o contenido")
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
        contenido_binario = archivo.read()
        return Binary(contenido_binario)
    except Exception as e:
        st.error(f"Error procesando PDF: {e}")
        return None

# Procesar archivos Word
def procesar_word(archivo):
    try:
        contenido_binario = archivo.read()
        return Binary(contenido_binario)
    except Exception as e:
        st.error(f"Error procesando Word: {e}")
        return None

# Función para descargar archivos
def crear_boton_descarga(contenido_binario, nombre_archivo, tipo_archivo):
    try:
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

# Función de búsqueda avanzada
def buscar_documentos(db, criterio_busqueda, tipo_busqueda):
    try:
        query = {}
        
        if tipo_busqueda == "nombre":
            query["titulo"] = {"$regex": criterio_busqueda, "$options": "i"}
        elif tipo_busqueda == "autor":
            query["autor"] = {"$regex": criterio_busqueda, "$options": "i"}
        elif tipo_busqueda == "contenido":
            query["contenido"] = {"$regex": criterio_busqueda, "$options": "i"}
        elif tipo_busqueda == "tags":
            query["tags"] = {"$in": [criterio_busqueda]}
        elif tipo_busqueda == "categoria":
            query["categoria"] = {"$regex": criterio_busqueda, "$options": "i"}
        elif tipo_busqueda == "identificacion":
            query["identificacion"] = {"$regex": criterio_busqueda, "$options": "i"}
        elif tipo_busqueda == "ci":
            query["ci"] = {"$regex": criterio_busqueda, "$options": "i"}
        
        documentos = list(db.documentos.find(query).sort("fecha_creacion", -1))
        return documentos, None
        
    except Exception as e:
        return None, str(e)

# Solo intentar conexión si hay URI
if mongo_uri:
    db, connected = connect_mongodb(mongo_uri)
    
    if connected:
        st.success("🚀 Conectado a MongoDB Cloud!")
        
        # --- SECCIÓN DE BÚSQUEDA AVANZADA ---
        st.header("🔍 Búsqueda Avanzada de Documentos")
        
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            criterio_busqueda = st.text_input(
                "Buscar documentos",
                placeholder="Ej: guía instalación, juan, 12345678...",
                key="busqueda_principal"
            )
        
        with col2:
            tipo_busqueda = st.selectbox(
                "Buscar por:",
                ["nombre", "autor", "contenido", "tags", "categoria", "identificacion", "ci"],
                format_func=lambda x: {
                    "nombre": "📄 Nombre del documento",
                    "autor": "👤 Autor", 
                    "contenido": "📝 Contenido",
                    "tags": "🏷️ Tags",
                    "categoria": "📂 Categoría",
                      "ci": "🔢 CI/Cédula"
                }[x]
            )
        
        with col3:
            st.write("")  # Espacio vertical
            buscar_btn = st.button("🔎 Buscar", use_container_width=True)
        
        # Realizar búsqueda si se presiona el botón
        if buscar_btn and criterio_busqueda:
            with st.spinner("Buscando documentos..."):
                documentos_encontrados, error = buscar_documentos(db, criterio_busqueda, tipo_busqueda)
                
                if error:
                    st.error(f"❌ Error en búsqueda: {error}")
                elif documentos_encontrados:
                    st.success(f"✅ Encontrados {len(documentos_encontrados)} documento(s)")
                    
                    # Mostrar resultados de búsqueda
                    for doc in documentos_encontrados:
                        icono = "📄" if doc.get('tipo') == 'pdf' else "📝" if doc.get('tipo') == 'word' else "📃"
                        
                        with st.expander(
                            f"{icono} **{doc['titulo']}** - "
                            f"_{doc.get('tipo', 'texto').upper()}_ - "
                            f"Por: {doc['autor']} - "
                            f"📅 {doc['fecha_creacion'].strftime('%d/%m/%Y')}"
                        ):
                            col1, col2 = st.columns([3, 1])
                            
                            with col1:
                                st.write(f"**Categoría:** {doc['categoria']}")
                                st.write(f"**Versión:** {doc['version']}")
                                st.write(f"**Tags:** {', '.join(doc['tags']) if doc['tags'] else 'Ninguno'}")
                                st.write(f"**Prioridad:** {doc['prioridad']}")
                                st.write(f"**CI/Cédula:** {doc.get('ci', 'No especificada')}")
                                
                                if doc.get('tipo') == 'texto':
                                    st.write("---")
                                    st.write(f"**Contenido:**")
                                    st.write(doc['contenido'])
                                elif doc.get('tipo') in ['pdf', 'word']:
                                    st.write(f"**Descripción:** {doc.get('descripcion', 'Sin descripción')}")
                                    st.write(f"**Archivo:** {doc.get('nombre_archivo', 'N/A')}")
                                    
                                    # Botón para descargar archivo
                                    if doc.get('contenido_binario'):
                                        crear_boton_descarga(
                                            doc['contenido_binario'],
                                            doc['nombre_archivo'],
                                            doc['tipo']
                                        )
                            
                            with col2:
                                if st.button("🗑️ Eliminar", key=f"delete_search_{doc['_id']}"):
                                    db.documentos.delete_one({"_id": doc["_id"]})
                                    st.success("Documento eliminado")
                                    st.rerun()
                else:
                    st.info("🔍 No se encontraron documentos con esos criterios")
        
        elif buscar_btn and not criterio_busqueda:
            st.warning("⚠️ Ingresa un criterio de búsqueda")
        
        st.markdown("---")
        
        # --- PESTAÑAS PARA AGREGAR DOCUMENTOS ---
        tab1, tab2, tab3, tab4 = st.tabs(["📝 Texto Simple", "📄 Subir PDF", "📝 Subir Word", "📂 Todos los Documentos"])
        
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
                    ci = st.text_input("CI/Cédula*", placeholder="Número de cédula", key="texto_ci")
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
                    if titulo and contenido and autor and identificacion and ci:
                        tags = [tag.strip() for tag in tags_input.split(",")] if tags_input else []
                        
                        documento = {
                            "titulo": titulo,
                            "contenido": contenido,
                            "categoria": categoria,
                            "autor": autor,
                            "identificacion": identificacion,
                            "ci": ci,
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
                    ci_pdf = st.text_input("CI/Cédula*", placeholder="Número de cédula", key="pdf_ci")
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
                    if titulo_pdf and archivo_pdf and autor_pdf and identificacion_pdf and ci_pdf:
                        contenido_pdf = procesar_pdf(archivo_pdf)
                        
                        if contenido_pdf:
                            documento_pdf = {
                                "titulo": titulo_pdf,
                                "descripcion": descripcion_pdf,
                                "categoria": categoria_pdf,
                                "autor": autor_pdf,
                                "identificacion": identificacion_pdf,
                                "ci": ci_pdf,
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
                    ci_word = st.text_input("CI/Cédula*", placeholder="Número de cédula", key="word_ci")
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
                    if titulo_word and archivo_word and autor_word and identificacion_word and ci_word:
                        contenido_word = procesar_word(archivo_word)
                        
                        if contenido_word:
                            documento_word = {
                                "titulo": titulo_word,
                                "descripcion": descripcion_word,
                                "categoria": categoria_word,
                                "autor": autor_word,
                                "identificacion": identificacion_word,
                                "ci": ci_word,
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
        
        # --- PESTAÑA 4: TODOS LOS DOCUMENTOS ---
        with tab4:
            st.header("📂 Todos los Documentos")
            
            # Filtros rápidos
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                filtro_tipo = st.selectbox(
                    "Tipo de documento",
                    ["Todos", "Texto", "PDF", "Word"],
                    key="filtro_tipo"
                )
            with col2:
                filtro_categoria = st.selectbox(
                    "Categoría",
                    ["Todas"] + ["Técnica", "Usuario", "API", "Tutorial", "Referencia", "Otros"],
                    key="filtro_categoria"
                )
            with col3:
                filtro_prioridad = st.selectbox(
                    "Prioridad", 
                    ["Todas", "Alta", "Media", "Baja"],
                    key="filtro_prioridad"
                )
            with col4:
                busqueda_rapida = st.text_input("🔍 Buscar por título", key="busqueda_rapida")
            with col5:
                busqueda_identificacion = st.text_input("🔍 Buscar por ID/CI", key="busqueda_identificacion")
            
            # Construir query
            query = {}
            if filtro_tipo != "Todos":
                query["tipo"] = filtro_tipo.lower()
            if filtro_categoria != "Todas":
                query["categoria"] = filtro_categoria
            if filtro_prioridad != "Todas":
                query["prioridad"] = filtro_prioridad
            if busqueda_rapida:
                query["titulo"] = {"$regex": busqueda_rapida, "$options": "i"}
            if busqueda_identificacion:
                query["$or"] = [
                    {"identificacion": {"$regex": busqueda_identificacion, "$options": "i"}},
                    {"ci": {"$regex": busqueda_identificacion, "$options": "i"}}
                ]
            
            try:
                documentos = list(db.documentos.find(query).sort("fecha_creacion", -1))
                
                if documentos:
                    st.info(f"📊 Mostrando {len(documentos)} documento(s)")
                    
                    for doc in documentos:
                        icono = "📄" if doc.get('tipo') == 'pdf' else "📝" if doc.get('tipo') == 'word' else "📃"
                        
                        with st.expander(
                            f"{icono} **{doc['titulo']}** - "
                            f"_{doc.get('tipo', 'texto').upper()}_ - "
                            f"Por: {doc['autor']} - "
                            f"📅 {doc['fecha_creacion'].strftime('%d/%m/%Y')}"
                        ):
                            col1, col2 = st.columns([3, 1])
                            
                            with col1:
                                st.write(f"**Categoría:** {doc['categoria']}")
                                st.write(f"**Versión:** {doc['version']}")
                                st.write(f"**Tags:** {', '.join(doc['tags']) if doc['tags'] else 'Ninguno'}")
                                st.write(f"**Prioridad:** {doc['prioridad']}")
                                 st.write(f"**CI/Cédula:** {doc.get('ci', 'No especificada')}")
                                
                                if doc.get('tipo') == 'texto':
                                    st.write("---")
                                    st.write(f"**Contenido:**")
                                    st.write(doc['contenido'])
                                elif doc.get('tipo') in ['pdf', 'word']:
                                    st.write(f"**Descripción:** {doc.get('descripcion', 'Sin descripción')}")
                                    st.write(f"**Archivo:** {doc.get('nombre_archivo', 'N/A')}")
                                    
                                    if doc.get('contenido_binario'):
                                        crear_boton_descarga(
                                            doc['contenido_binario'],
                                            doc['nombre_archivo'],
                                            doc['tipo']
                                        )
                            
                            with col2:
                                if st.button("🗑️ Eliminar", key=f"delete_all_{doc['_id']}"):
                                    db.documentos.delete_one({"_id": doc["_id"]})
                                    st.success("Documento eliminado")
                                    st.rerun()
                else:
                    st.info("📝 No se encontraron documentos. ¡Agrega el primero en las pestañas de arriba!")
                    
            except Exception as e:
                st.error(f"❌ Error al cargar documentos: {str(e)}")

else:
    st.info("👈 Ingresa tu cadena de conexión MongoDB en la barra lateral para comenzar")

# Footer
st.markdown("---")
st.caption("Sistema de Documentación - Búsqueda avanzada por nombre,  CI, autor y contenido")

