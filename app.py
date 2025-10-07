import streamlit as st
import pymongo
from datetime import datetime
import os

# Configuración de la página
st.set_page_config(
    page_title="Sistema de Documentación",
    page_icon="📄",
    layout="wide"
)

# Título principal
st.title("📄 Sistema de Documentación con MongoDB")
st.markdown("---")

# Sidebar para configuración
with st.sidebar:
    st.header("🔧 Configuración MongoDB")
    
    # Input para la conexión de MongoDB
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
        # Probar la conexión
        client.admin.command('ping')
        db = client.documentation_db
        return db, True
    except Exception as e:
        st.error(f"❌ Error de conexión: {str(e)}")
        return None, False

# Solo intentar conexión si hay URI
if mongo_uri:
    db, connected = connect_mongodb(mongo_uri)
    
    if connected:
        st.success("🚀 Conectado a MongoDB Cloud!")
        
        # --- SECCIÓN PARA AGREGAR DOCUMENTOS ---
        st.header("➕ Agregar Nuevo Documento")
        
        with st.form("nuevo_documento", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                titulo = st.text_input("Título del documento*", placeholder="Ej: Guía de Instalación")
                categoria = st.selectbox(
                    "Categoría*", 
                    ["Técnica", "Usuario", "API", "Tutorial", "Referencia", "Otros"]
                )
                autor = st.text_input("Autor*", placeholder="Tu nombre")
                
            with col2:
                version = st.text_input("Versión", value="1.0")
                tags_input = st.text_input("Tags", placeholder="python,documentación,sistema")
                prioridad = st.select_slider("Prioridad", options=["Baja", "Media", "Alta"])
            
            contenido = st.text_area(
                "Contenido del documento*", 
                height=200,
                placeholder="Escribe el contenido completo del documento aquí..."
            )
            
            submitted = st.form_submit_button("💾 Guardar Documento")
            
            if submitted:
                if titulo and contenido and autor:
                    # Procesar tags
                    tags = [tag.strip() for tag in tags_input.split(",")] if tags_input else []
                    
                    documento = {
                        "titulo": titulo,
                        "contenido": contenido,
                        "categoria": categoria,
                        "autor": autor,
                        "version": version,
                        "tags": tags,
                        "prioridad": prioridad,
                        "fecha_creacion": datetime.utcnow(),
                        "fecha_actualizacion": datetime.utcnow()
                    }
                    
                    try:
                        result = db.documentos.insert_one(documento)
                        st.success(f"✅ Documento '{titulo}' guardado exitosamente!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"❌ Error al guardar: {str(e)}")
                else:
                    st.warning("⚠️ Completa los campos obligatorios (*)")

        # --- SECCIÓN PARA VER DOCUMENTOS ---
        st.header("📂 Documentos Existentes")
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_categoria = st.selectbox(
                "Filtrar por categoría",
                ["Todas"] + ["Técnica", "Usuario", "API", "Tutorial", "Referencia", "Otros"]
            )
        with col2:
            filtro_prioridad = st.selectbox(
                "Filtrar por prioridad", 
                ["Todas", "Alta", "Media", "Baja"]
            )
        with col3:
            busqueda = st.text_input("🔍 Buscar por título")

        # Construir query de filtro
        query = {}
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
                    with st.expander(
                        f"📄 **{doc['titulo']}** - "
                        f"_{doc['categoria']}_ - "
                        f"Prioridad: {doc['prioridad']} - "
                        f"📅 {doc['fecha_creacion'].strftime('%d/%m/%Y')}"
                    ):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**Autor:** {doc['autor']}")
                            st.write(f"**Versión:** {doc['version']}")
                            st.write(f"**Tags:** {', '.join(doc['tags']) if doc['tags'] else 'Ninguno'}")
                            st.write("---")
                            st.write(f"**Contenido:**")
                            st.write(doc['contenido'])
                        
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
st.caption("Sistema de Documentación - Desarrollado con Streamlit + MongoDB")