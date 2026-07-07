import streamlit as st
from supabase import create_client, Client
from datetime import date, datetime, timedelta
import os
import pandas as pd
import hashlib
import io
from PIL import Image
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go

def scroll_to_top():
    st.markdown("""
        <script>
            window.scrollTo(0, 0);
        </script>
    """, unsafe_allow_html=True)

# ========== FUNCIÓN DE NAVEGACIÓN CON SCROLL ==========
def go_to_step(step_number):
    """Cambia de paso y fuerza scroll al inicio"""
    st.session_state.step = step_number
    # Forzar scroll usando múltiples métodos
    st.markdown("""
        <div id="nav-scroll-top"></div>
        <script>
            function forceScroll() {
                window.scrollTo({top: 0, behavior: 'smooth'});
                document.body.scrollTop = 0;
                document.documentElement.scrollTop = 0;
                var el = document.getElementById('nav-scroll-top');
                if (el) el.scrollIntoView({behavior: 'smooth', block: 'start'});
            }
            forceScroll();
            setTimeout(forceScroll, 100);
            setTimeout(forceScroll, 300);
        </script>
        <style>
            #nav-scroll-top {
                scroll-margin-top: 0px;
                height: 0px;
                overflow: hidden;
            }
        </style>
    """, unsafe_allow_html=True)
    st.rerun()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ========== CONFIGURACIÓN DE PÁGINA ==========
st.set_page_config(
    page_title="COOPROGRESO - Sistema de Capacidad Productiva",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== ESTILOS ==========
st.markdown("""
<style>
    .stButton button, .stFormSubmit button {
        padding: 12px !important;
        font-size: 16px !important;
        font-weight: bold !important;
        border-radius: 10px !important;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-card .value {
        font-size: 32px;
        font-weight: bold;
    }
    .metric-card .label {
        font-size: 14px;
        opacity: 0.9;
    }
    .admin-expanded {
        padding: 20px;
        background: #f8f9fa;
        border-radius: 10px;
        margin: 10px 0;
    }
    .form-container {
        max-width: 800px;
        margin: 0 auto;
    }
    .dataframe {
        font-size: 14px !important;
    }
    .dataframe th {
        background-color: #4CAF50 !important;
        color: white !important;
        padding: 10px !important;
    }
    .dataframe td {
        padding: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

# ========== CARGAR CREDENCIALES ==========
load_dotenv()

url = os.getenv("SUPABASE_URL")
anon_key = os.getenv("SUPABASE_ANON_KEY")
service_key = os.getenv("SUPABASE_SERVICE_KEY")

if not url or not anon_key:
    st.error("❌ No se encontraron credenciales de Supabase")
    st.stop()

# ========== INICIALIZAR CLIENTES ==========
supabase_anon: Client = create_client(url, anon_key)
supabase_admin: Client = create_client(url, service_key) if service_key else None
supabase = supabase_anon

# ========== FUNCIONES DE PERMISOS ==========
def is_admin():
    return st.session_state.get("authenticated", False) and st.session_state.get("admin_mode", False)

def get_supabase_client():
    if is_admin() and supabase_admin:
        return supabase_admin
    return supabase_anon

def get_admin_client():
    if not supabase_admin:
        st.error("❌ No se configuró la clave de servicio de Supabase")
        st.info("Añade SUPABASE_SERVICE_KEY a tu archivo .env")
        return None
    return supabase_admin

# ========== CONSTANTES ==========
TIPOS_PROPIEDAD = ["Propietario", "Poseedor", "Arrendatario"]
TIPOS_SUELO = ["Arenoso", "Mixto", "Arcilloso"]
TIPOS_IDENTIFICACION = ["Cédula de Ciudadanía", "Tarjeta de Identidad", "Registro Civil de Nacimiento", "Cédula de Extranjería", "Pasaporte", "NIT"]
UNIDADES_MEDIDA = ["kg", "litro", "docena", "unidad", "libra", "arroba", "tonelada", "bushel", "saco", "otro"]
PERIODICIDADES = ["Diaria", "Semanal", "Quincenal", "Mensual", "Bimestral", "Trimestral", "Semestral", "Anual"]
PARENTESCOS = ["Principal", "Cónyuge", "Hijo(a)", "Padre", "Madre", "Hermano(a)", "Abuelo(a)", "Nieto(a)", "Otro"]
NIVEL_ESCOLAR = ["Ninguno", "Primaria", "Secundaria", "Técnico", "Tecnólogo", "Pregrado", "Posgrado"]
CALIDADES = ["Excelente", "Buena", "Regular", "Baja", "No tiene"]
UBICACION_PRODUCCION = ["Patio", "Predio Principal", "Predio Adicional"]

# ========== SISBÉN IV ==========
SISBEN_GRUPOS = {
    "A": {"nombre": "Pobreza extrema", "descripcion": "Población con menor capacidad de generación de ingresos", "color": "🔴", "subgrupos": ["A1", "A2", "A3", "A4", "A5"]},
    "B": {"nombre": "Pobreza moderada", "descripcion": "Hogares en condición de pobreza con capacidad de generar ingresos ligeramente mayor", "color": "🟠", "subgrupos": ["B1", "B2", "B3", "B4", "B5", "B6", "B7"]},
    "C": {"nombre": "Población vulnerable", "descripcion": "Hogares en riesgo de caer en situación de pobreza", "color": "🟡", "subgrupos": ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C11", "C12", "C13", "C14", "C15", "C16", "C17", "C18"]},
    "D": {"nombre": "No pobre ni vulnerable", "descripcion": "Población que no se encuentra en condición de pobreza ni vulnerabilidad", "color": "🟢", "subgrupos": ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12", "D13", "D14", "D15", "D16", "D17", "D18", "D19", "D20", "D21"]}
}

SISBEN_SUBGRUPOS = []
for grupo, info in SISBEN_GRUPOS.items():
    for subgrupo in info["subgrupos"]:
        SISBEN_SUBGRUPOS.append(subgrupo)

SISBEN_OPCIONES = ["No aplica"] + SISBEN_SUBGRUPOS

# ========== FUNCIONES AUXILIARES ==========
def get_grupo_from_subgrupo(subgrupo):
    if subgrupo and subgrupo != "No aplica":
        for grupo, info in SISBEN_GRUPOS.items():
            if subgrupo in info["subgrupos"]:
                return grupo
    return None

def get_info_sisben(subgrupo):
    if subgrupo and subgrupo != "No aplica":
        for grupo, info in SISBEN_GRUPOS.items():
            if subgrupo in info["subgrupos"]:
                return {"grupo": grupo, "nombre_grupo": info["nombre"], "descripcion": info["descripcion"], "color": info["color"], "subgrupo": subgrupo}
    return None

def get_grupo_descripcion(grupo):
    if grupo in SISBEN_GRUPOS:
        return SISBEN_GRUPOS[grupo]["nombre"]
    return None

def get_sisben_color(subgrupo):
    if subgrupo and subgrupo != "No aplica":
        for grupo, info in SISBEN_GRUPOS.items():
            if subgrupo in info["subgrupos"]:
                return info["color"]
    return "⚪"

def to_iso_date(fecha):
    if fecha:
        return fecha.isoformat()
    return None

def scroll_to_top():
    st.markdown("""
        <script>
            window.scrollTo(0, 0);
        </script>
    """, unsafe_allow_html=True)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def formato_cop(valor):
    if valor is None or valor == 0:
        return "$ 0"
    return f"$ {valor:,.0f}".replace(",", ".")

# ========== FUNCIÓN DE FOTOS ==========
def upload_photo(survey_id, photo_bytes, description, photo_type):
    try:
        counter = st.session_state.get("photo_counter", 0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{survey_id}_{photo_type}_{timestamp}_{counter}.jpg"
        response = supabase.storage.from_("survey_photos").upload(file_name, photo_bytes, {"content-type": "image/jpeg"})
        url = supabase.storage.from_("survey_photos").get_public_url(file_name)
        supabase.table("survey_photos").insert({"survey_id": survey_id, "photo_url": url, "photo_description": description, "photo_type": photo_type}).execute()
        st.session_state.photo_counter = counter + 1
        return url
    except Exception as e:
        st.error(f"Error al subir foto: {e}")
        return None

# ========== FUNCIÓN DE GUARDADO ==========
def save_survey(data):
    client = supabase_anon
    
    survey_data = {
        "registration_date": to_iso_date(data["registration_date"]),
        "type": data["type"],
        "reason": data["reason"],
        "signature": data.get("signature", False),
        "synced": False
    }
    result = client.table("survey_registry").insert(survey_data).execute()
    survey_id = result.data[0]["id"]
    
    for member in data["family_members"]:
        member["survey_id"] = survey_id
        member["birth_date"] = to_iso_date(member.get("birth_date"))
        if member.get("sisben_subgrupo") and member["sisben_subgrupo"] != "No aplica":
            member["sisben_grupo"] = get_grupo_from_subgrupo(member["sisben_subgrupo"])
        member["id_type"] = member.get("id_type", "")
        member["id_number"] = member.get("id_number", "")
        client.table("family_members").insert(member).execute()
    
    housing_data = data["housing"]
    housing_data["survey_id"] = survey_id
    client.table("housing").insert(housing_data).execute()
    
    land_data = data["land"]
    land_data["survey_id"] = survey_id
    client.table("land").insert(land_data).execute()
    
    if "predios_adicionales" in data and data["predios_adicionales"]:
        for predio in data["predios_adicionales"]:
            predio["survey_id"] = survey_id
            client.table("land").insert(predio).execute()
    
    for prod in data["productions"]:
        prod["survey_id"] = survey_id
        prod["start_date"] = to_iso_date(prod.get("start_date"))
        prod["production_date"] = to_iso_date(prod.get("production_date"))
        prod["ubicacion"] = prod.get("ubicacion", "No especificada")
        client.table("production_capacity").insert(prod).execute()
    
    for serv in data["services"]:
        serv["survey_id"] = survey_id
        serv["season_start"] = to_iso_date(serv.get("season_start"))
        serv["season_end"] = to_iso_date(serv.get("season_end"))
        if "total_value" not in serv:
            serv["total_value"] = serv.get("quantity", 0) * serv.get("price", 0)
        serv["ubicacion"] = serv.get("ubicacion", "No especificada")
        client.table("service_capacity").insert(serv).execute()
    
    if "temp_photos" in st.session_state and st.session_state.temp_photos:
        for photo in st.session_state.temp_photos:
            upload_photo(survey_id, photo["bytes"], photo["description"], photo["type"])
        st.session_state.temp_photos = []
        st.session_state.photo_counter = 0
    
    return survey_id

# ========== PASO 1: PRODUCTOR PRINCIPAL ==========
def step1():
    scroll_to_top()
    st.header("📋 Paso 1: Datos del levantamiento y productor principal")
    
    with st.form("step1_form"):
        col1, col2 = st.columns(2)
        with col1:
            reg_date = st.date_input("Fecha de registro *", value=date.today(), max_value=date.today())
            reg_type = st.selectbox("Tipo *", ["INICIAL", "ACTUAL"])
        with col2:
            reason = st.text_area("Razón del levantamiento")
            signature = st.checkbox("Firma del productor asociado")
        
        st.subheader("👤 Productor principal")
        col1, col2, col3 = st.columns(3)
        with col1:
            nombres = st.text_input("Nombres *")
            apellidos = st.text_input("Apellidos *")
            id_num = st.text_input("Número de identificación *")
        with col2:
            birth = st.date_input("Fecha nacimiento *", value=None, min_value=date(1900, 1, 1), max_value=date.today() - timedelta(days=365*18))
            id_place = st.text_input("Lugar expedición")
            id_type = st.selectbox("Tipo de identificación", TIPOS_IDENTIFICACION)
        with col3:
            phone = st.text_input("Teléfono/Celular")
            email = st.text_input("Email")
        
        nivel = st.selectbox("Nivel escolar", NIVEL_ESCOLAR)
        disciplina = st.text_input("Disciplina / Oficio")
        ocupacion = st.text_input("Ocupación actual")
        
        st.subheader("📊 Sisbén IV")
        col_sisben1, col_sisben2 = st.columns(2)
        with col_sisben1:
            sisben_id = st.text_input("# Ficha Sisbén")
            sisben_subgrupo = st.selectbox("Subgrupo Sisbén IV *", SISBEN_OPCIONES)
        with col_sisben2:
            if sisben_subgrupo and sisben_subgrupo != "No aplica":
                info = get_info_sisben(sisben_subgrupo)
                if info:
                    st.info(f"{info['color']} **Grupo {info['grupo']}** - {info['nombre_grupo']}\n\n📝 {info['descripcion']}\n\n🔹 **Subgrupo:** {info['subgrupo']}")
            else:
                st.info("📊 **Sisbén IV**\n\nSelecciona tu subgrupo según tu ficha Sisbén.\n\nSi no tienes Sisbén, selecciona **'No aplica'**.")
        
        submitted = st.form_submit_button("Siguiente →")
        if submitted:
            if nombres and apellidos and id_num and birth:
                st.session_state.temp_data.update({
                    "registration_date": reg_date,
                    "type": reg_type,
                    "reason": reason,
                    "signature": signature,
                    "family_members": [{
                        "is_main": True,
                        "nombres": nombres,
                        "apellidos": apellidos,
                        "parentesco": "Principal",
                        "birth_date": birth,
                        "id_type": id_type,
                        "id_number": id_num,
                        "id_issue_place": id_place,
                        "phone": phone,
                        "email": email,
                        "education_level": nivel,
                        "discipline": disciplina,
                        "occupation": ocupacion,
                        "sisben_id": sisben_id,
                        "sisben_subgrupo": sisben_subgrupo,
                        "sisben_grupo": get_grupo_from_subgrupo(sisben_subgrupo) if sisben_subgrupo != "No aplica" else None,
                        "sisben_category": sisben_subgrupo
                    }]
                })
                go_to_step(2)  # ←CAMBIADO: antes era st.session_state.step=2
            else:
                st.error("Nombres, apellidos, identificación y fecha de nacimiento son obligatorios")

# ========== PASO 2: FAMILIARES ==========
def step2():
    scroll_to_top()
    st.header("👨‍👩‍👧‍👦 Paso 2: Miembros de la familia")
    st.info("Agrega todos los miembros de tu familia. El productor principal ya está incluido.")
    
    if "extra_family" not in st.session_state:
        st.session_state.extra_family = []
    
    if st.session_state.extra_family:
        st.subheader(f"👨‍👩‍👧‍👦 Familiares agregados: {len(st.session_state.extra_family)}")
        for i, m in enumerate(st.session_state.extra_family):
            with st.expander(f"👤 {m.get('nombres', '')} {m.get('apellidos', '')} - {m.get('parentesco', '')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Nombres:** {m.get('nombres', '')}")
                    st.write(f"**Apellidos:** {m.get('apellidos', '')}")
                    st.write(f"**Parentesco:** {m.get('parentesco', '')}")
                    st.write(f"**Tipo ID:** {m.get('id_type', '')}")
                    st.write(f"**Número ID:** {m.get('id_number', '')}")
                with col2:
                    st.write(f"**Teléfono:** {m.get('phone', '')}")
                    st.write(f"**Ocupación:** {m.get('occupation', '')}")
                    st.write(f"**Nivel escolar:** {m.get('education_level', '')}")
                    st.write(f"**Fecha nacimiento:** {m.get('birth_date', '')}")
                    if m.get('sisben_subgrupo') and m.get('sisben_subgrupo') != "No aplica":
                        color = get_sisben_color(m.get('sisben_subgrupo'))
                        st.write(f"**Sisbén:** {color} {m.get('sisben_subgrupo', '')}")
                if st.button(f"🗑️ Eliminar", key=f"del_fam_{i}"):
                    st.session_state.extra_family.pop(i)
                    st.rerun()
    
    with st.form("add_family_form"):
        st.subheader("➕ Agregar nuevo familiar")
        col1, col2, col3 = st.columns(3)
        with col1:
            fam_nombres = st.text_input("Nombres *", key="fam_nombres")
            fam_apellidos = st.text_input("Apellidos *", key="fam_apellidos")
            fam_id_type = st.selectbox("Tipo de identificación", TIPOS_IDENTIFICACION, key="fam_id_type")
        with col2:
            fam_parentesco = st.selectbox("Parentesco *", PARENTESCOS, key="fam_parentesco")
            fam_id_num = st.text_input("Número de identificación", key="fam_id_num")
            fam_phone = st.text_input("Teléfono/Celular", key="fam_phone")
        with col3:
            fam_ocupacion = st.text_input("Ocupación", key="fam_ocupacion")
            fam_nivel = st.selectbox("Nivel escolar", NIVEL_ESCOLAR, key="fam_nivel")
        
        fam_birth = st.date_input("Fecha nacimiento", value=None, min_value=date(1900, 1, 1), max_value=date.today(), key="fam_birth")
        
        st.subheader("📊 Sisbén del familiar")
        fam_sisben_subgrupo = st.selectbox("Subgrupo Sisbén", SISBEN_OPCIONES, key="fam_sisben")
        if fam_sisben_subgrupo and fam_sisben_subgrupo != "No aplica":
            info = get_info_sisben(fam_sisben_subgrupo)
            if info:
                st.caption(f"{info['color']} Grupo {info['grupo']}: {info['nombre_grupo']}")
        
        agregar = st.form_submit_button("➕ Agregar familiar")
        if agregar:
            if fam_nombres and fam_apellidos:
                nuevo_familiar = {
                    "is_main": False,
                    "nombres": fam_nombres,
                    "apellidos": fam_apellidos,
                    "parentesco": fam_parentesco,
                    "birth_date": fam_birth,
                    "id_type": fam_id_type,
                    "id_number": fam_id_num,
                    "id_issue_place": "",
                    "phone": fam_phone,
                    "email": "",
                    "education_level": fam_nivel,
                    "discipline": "",
                    "occupation": fam_ocupacion,
                    "sisben_id": "",
                    "sisben_subgrupo": fam_sisben_subgrupo,
                    "sisben_grupo": get_grupo_from_subgrupo(fam_sisben_subgrupo) if fam_sisben_subgrupo != "No aplica" else None,
                    "sisben_category": fam_sisben_subgrupo
                }
                st.session_state.extra_family.append(nuevo_familiar)
                st.success(f"✅ {fam_nombres} {fam_apellidos} agregado")
                st.rerun()
            else:
                st.error("Nombres y apellidos son obligatorios")
    
    col_b, col_n = st.columns(2)
    with col_b:
        if st.button("← Atrás"):
            st.session_state.temp_data["family_members"].extend(st.session_state.extra_family)
            go_to_step(1)  # ← CAMBIADO
    with col_n:
        if st.button("Siguiente →"):
            st.session_state.temp_data["family_members"].extend(st.session_state.extra_family)
            go_to_step(3)  # ← CAMBIADO

# ========== PASO 3: VIVIENDA Y PREDIO ==========
def step3():
    scroll_to_top()
    st.header("🏠 Paso 3: Vivienda y Predios")
    
    if "predios_adicionales" not in st.session_state:
        st.session_state.predios_adicionales = []
    
    if st.session_state.predios_adicionales:
        st.markdown("---")
        st.subheader("🌳 Predios adicionales agregados")
        for i, predio in enumerate(st.session_state.predios_adicionales):
            with st.expander(f"🌳 Predio adicional {i+1}: {predio.get('land_name', 'Sin nombre')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Tipo propiedad:** {predio.get('property_type', '')}")
                    st.write(f"**Ubicación:** {predio.get('location', '')}")
                with col2:
                    st.write(f"**Área:** {predio.get('total_area_m2', 0)} m²")
                    st.write(f"**Tipo de suelo:** {predio.get('tipo_suelo', '')}")
                st.info("🌱 Puedes asignar producciones a este predio en el Paso 4")
                if st.button(f"🗑️ Eliminar predio {i+1}", key=f"del_predio_{i}"):
                    st.session_state.predios_adicionales.pop(i)
                    st.rerun()
    
    with st.form("housing_land_form"):
        st.subheader("🏠 Datos de la vivienda")
        col1, col2 = st.columns(2)
        with col1:
            housing_type = st.selectbox("Tipo de propiedad (vivienda)", TIPOS_PROPIEDAD, key="housing_type")
            housing_loc = st.text_input("Ubicación geográfica (vereda, corregimiento)", key="housing_loc")
            housing_cat = st.text_input("ID Catastral", key="housing_cat")
        with col2:
            built_area = st.number_input("Área construida (m²)", min_value=0.0, step=10.0, key="built_area")
            patio_area = st.number_input("Área de patio (m²)", min_value=0.0, step=10.0, key="patio_area")
            patio_tipo_suelo = st.selectbox("Tipo de suelo del patio", TIPOS_SUELO, key="patio_tipo_suelo")
        
        patio_productivo = st.checkbox("✅ El patio es productivo (tiene cultivos, animales, etc.)", key="patio_productivo")
        if patio_productivo:
            st.info("🌱 Recuerda: Cuando agregues productos en el Paso 4, selecciona 'Patio' como ubicación.")
        
        st.subheader("Servicios básicos (vivienda)")
        colq1, colq2, colq3 = st.columns(3)
        with colq1:
            water_q = st.selectbox("Calidad del agua", ["Buena", "Regular", "Mala", "No tiene"], key="water_q")
            energy_q = st.selectbox("Calidad energía", ["Buena", "Regular", "Mala", "No tiene"], key="energy_q")
        with colq2:
            internet_q = st.selectbox("Calidad internet", ["Buena", "Regular", "Mala", "No tiene"], key="internet_q")
            sewage = st.selectbox("Alcantarillado", ["Si", "No", "Pozo séptico", "Letrina"], key="sewage")
        with colq3:
            waste = st.selectbox("Recolección de aseo", ["Si", "No", "Quema", "Entierro"], key="waste")
        
        st.markdown("---")
        st.subheader("🌳 Datos del predio principal")
        colL1, colL2 = st.columns(2)
        with colL1:
            land_prop_type = st.selectbox("Tipo propiedad del predio", TIPOS_PROPIEDAD, key="land_prop_type")
            land_name = st.text_input("Nombre del predio", key="land_name")
            land_loc = st.text_input("Ubicación del predio", key="land_loc")
        with colL2:
            land_cat = st.text_input("ID Catastral del predio", key="land_cat")
            total_area = st.number_input("Área total (m²)", min_value=0.0, step=100.0, key="total_area")
            land_tipo_suelo = st.selectbox("Tipo de suelo del predio", TIPOS_SUELO, key="land_tipo_suelo")
        
        colL3, colL4 = st.columns(2)
        with colL3:
            land_type = st.selectbox("Uso del suelo", ["Suelo agrícola", "Suelo pecuario", "Mixto", "Bosque", "Cuerpo de agua"], key="land_type")
            floodable = st.checkbox("¿Es inundable?", key="floodable")
        with colL4:
            slope = st.selectbox("Grado de inclinación", ["Plano", "Ligero", "Moderado", "Escarpado"], key="slope")
            reg_inmob = st.text_input("Matrícula inmobiliaria (opcional)", key="reg_inmob")
        
        st.subheader("Servicios básicos en el predio")
        colW1, colW2 = st.columns(2)
        with colW1:
            land_water = st.selectbox("Calidad del agua (predio)", ["Buena", "Regular", "Mala", "No tiene"], key="land_water")
            land_energy = st.selectbox("Calidad energía (predio)", ["Buena", "Regular", "Mala", "No tiene"], key="land_energy")
        with colW2:
            land_internet = st.selectbox("Calidad internet (predio)", ["Buena", "Regular", "Mala", "No tiene"], key="land_internet")
            land_sewage = st.selectbox("Alcantarillado (predio)", ["Si", "No", "Pozo séptico", "Letrina"], key="land_sewage")
        land_waste = st.selectbox("Aseo (predio)", ["Si", "No", "Quema", "Entierro"], key="land_waste")
        
        st.info("🌱 Recuerda: Cuando agregues productos en el Paso 4, selecciona 'Predio Principal' como ubicación.")
        
        st.markdown("---")
        st.subheader("➕ Agregar predio adicional")
        st.info("Si tienes más de un predio, agrégalos aquí. Luego podrás asignar producciones a cada uno en el Paso 4.")
        
        colA1, colA2 = st.columns(2)
        with colA1:
            predio_nombre = st.text_input("Nombre del predio adicional", key="predio_nombre")
            predio_prop = st.selectbox("Tipo propiedad", TIPOS_PROPIEDAD, key="predio_prop")
            predio_ubicacion = st.text_input("Ubicación", key="predio_ubicacion")
            # 🔴 AGREGAR ESTE CAMPO
            predio_catastral = st.text_input("ID Catastral del predio adicional", key="predio_catastral")
        with colA2:
            predio_area = st.number_input("Área (m²)", min_value=0.0, step=100.0, key="predio_area")
            predio_suelo = st.selectbox("Tipo de suelo", TIPOS_SUELO, key="predio_suelo")
            predio_uso = st.selectbox("Uso del suelo", ["Suelo agrícola", "Suelo pecuario", "Mixto", "Bosque", "Cuerpo de agua"], key="predio_uso")
        
        agregar_predio = st.form_submit_button("➕ Agregar predio")
        if agregar_predio:
            if predio_nombre:
                nuevo_predio = {
                    "property_type": predio_prop,
                    "land_name": predio_nombre,
                    "location": predio_ubicacion,
                    "cadastral_id": predio_catastral,
                    "total_area_m2": predio_area,
                    "tipo_suelo": predio_suelo,
                    "land_type": predio_uso,
                    "cadastral_id": "",
                    "is_floodable": False,
                    "water_quality": "",
                    "slope_degree": "",
                    "energy_quality": "",
                    "internet_quality": "",
                    "sewage": "",
                    "waste_management": "",
                    "real_estate_registration": ""
                }
                st.session_state.predios_adicionales.append(nuevo_predio)
                st.success(f"✅ Predio {predio_nombre} agregado")
                st.rerun()
            else:
                st.error("El nombre del predio es obligatorio")
        
        st.markdown("---")
        submitted = st.form_submit_button("Siguiente →")
        if submitted:
            st.session_state.temp_data["housing"] = {
                "property_type": housing_type,
                "location": housing_loc,
                "cadastral_id": housing_cat,
                "built_area_m2": built_area,
                "patio_area_m2": patio_area,
                "patio_tipo_suelo": patio_tipo_suelo,
                "patio_productivo": patio_productivo,
                "water_quality": water_q,
                "energy_quality": energy_q,
                "internet_quality": internet_q,
                "sewage": sewage,
                "waste_management": waste
            }
            st.session_state.temp_data["land"] = {
                "property_type": land_prop_type,
                "land_name": land_name,
                "location": land_loc,
                "cadastral_id": land_cat,
                "total_area_m2": total_area,
                "tipo_suelo": land_tipo_suelo,
                "land_type": land_type,
                "is_floodable": floodable,
                "water_quality": land_water,
                "slope_degree": slope,
                "energy_quality": land_energy,
                "internet_quality": land_internet,
                "sewage": land_sewage,
                "waste_management": land_waste,
                "real_estate_registration": reg_inmob
            }
            st.session_state.temp_data["predios_adicionales"] = st.session_state.predios_adicionales
            go_to_step(4)  # ← CAMBIADO
    
    if st.button("← Atrás"):
        go_to_step(2)  # ← CAMBIADO

# ========== PASO 4: PRODUCTOS ==========
def step4():
    scroll_to_top()
    st.header("🌽 Paso 4: ¿Qué produce? (Bienes)")
    st.info("Agrega los productos que produces. Puedes asignar cada producto al patio, predio principal o predios adicionales.")
    
    if "productions" not in st.session_state.temp_data:
        st.session_state.temp_data["productions"] = []
    
    if st.session_state.temp_data["productions"]:
        st.subheader(f"📦 Productos agregados: {len(st.session_state.temp_data['productions'])}")
        for i, prod in enumerate(st.session_state.temp_data["productions"]):
            with st.expander(f"📦 {prod.get('product_name', 'Producto')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Producto:** {prod.get('product_name', '')}")
                    st.write(f"**Unidad:** {prod.get('measure_unit', '')}")
                    st.write(f"**Cantidad:** {prod.get('quantity_produced', 0)}")
                    st.write(f"**Ubicación:** {prod.get('ubicacion', 'No especificada')}")
                with col2:
                    st.write(f"**Precio unitario:** {formato_cop(prod.get('unit_price', 0))}")
                    st.write(f"**Precio total:** {formato_cop(prod.get('total_price', 0))}")
                    st.write(f"**Calidad:** {prod.get('product_quality', '')}")
                if st.button(f"🗑️ Eliminar", key=f"del_prod_{i}"):
                    st.session_state.temp_data["productions"].pop(i)
                    st.rerun()
    
    with st.form("add_production_form"):
        st.subheader("➕ Agregar nuevo producto")
        col1, col2 = st.columns(2)
        with col1:
            prod_name = st.text_input("Nombre del producto *", key="prod_name")
            unit = st.selectbox("Unidad de medida *", UNIDADES_MEDIDA, key="unit")
            area_used = st.number_input("Área ocupada (m²)", min_value=0.0, step=10.0, key="area_used")
        with col2:
            start_date = st.date_input("Fecha de inicio producción", value=None, key="start_date")
            frequency = st.selectbox("Periodicidad", PERIODICIDADES, key="frequency")
            quality = st.selectbox("Calidad del bien", CALIDADES, key="quality")
        
        st.subheader("📍 Ubicación de la producción")
        ubicacion = st.selectbox("¿Dónde se produce este producto?", UBICACION_PRODUCCION, key="ubicacion_prod")
        
        # 🔴 CAMBIO: Solo mostrar selección de predio adicional si la ubicación es "Predio Adicional"
        ubicacion_completa = ubicacion
        if ubicacion == "Predio Adicional":
            if st.session_state.predios_adicionales:
                nombres_predios = [p["land_name"] for p in st.session_state.predios_adicionales]
                predio_seleccionado = st.selectbox("Selecciona el predio adicional", nombres_predios, key="predio_seleccionado")
                ubicacion_completa = f"Predio Adicional: {predio_seleccionado}"
            else:
                st.warning("⚠️ No hay predios adicionales registrados. Agrega uno en el Paso 3.")
                ubicacion_completa = "Predio Adicional (sin predios registrados)"
        
        col3, col4 = st.columns(2)
        with col3:
            quantity = st.number_input("Cantidad producida por periodo *", min_value=0.0, step=1.0, key="quantity")
            unit_price = st.number_input("Precio por unidad (COP) *", min_value=0.0, step=100.0, key="unit_price")
        with col4:
            total_price = quantity * unit_price
            st.number_input("💰 Valor de la venta total (COP)", value=total_price, disabled=True)
            st.caption(f"💡 Cálculo: {quantity} × {formato_cop(unit_price)} = {formato_cop(total_price)}")
        
        agregar = st.form_submit_button("➕ Agregar producto")
        if agregar:
            if prod_name and unit and quantity > 0 and unit_price > 0:
                st.session_state.temp_data["productions"].append({
                    "product_name": prod_name,
                    "measure_unit": unit,
                    "occupied_area_m2": area_used,
                    "start_date": start_date,
                    "production_date": start_date,
                    "frequency": frequency,
                    "quantity_produced": quantity,
                    "total_price": total_price,
                    "unit_price": unit_price,
                    "product_quality": quality,
                    "ubicacion": ubicacion_completa
                })
                st.success(f"✅ {prod_name} agregado en {ubicacion_completa}")
                st.rerun()
            else:
                st.error("Nombre, unidad, cantidad y precio son obligatorios")
    
    col_b, col_n = st.columns(2)
    with col_b:
        if st.button("← Atrás"):
            go_to_step(3)
    with col_n:
        if st.button("Siguiente →"):
            if len(st.session_state.temp_data["productions"]) == 0:
                st.warning("Agrega al menos un producto. Si no produces, escribe 'Ninguno'.")
            else:
                go_to_step(5)

# ========== PASO 5: SERVICIOS ==========
def step5():
    scroll_to_top()
    st.header("🛠️ Paso 5: ¿Ofrece servicios?")
    st.info("Agrega los servicios que ofreces. El valor total vendido se calcula automáticamente.")
    
    if "services" not in st.session_state.temp_data:
        st.session_state.temp_data["services"] = []
    
    if st.session_state.temp_data["services"]:
        st.subheader(f"🔧 Servicios agregados: {len(st.session_state.temp_data['services'])}")
        for i, serv in enumerate(st.session_state.temp_data["services"]):
            with st.expander(f"🔧 {serv.get('service_name', 'Servicio')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Servicio:** {serv.get('service_name', '')}")
                    st.write(f"**Unidad:** {serv.get('measure_unit', '')}")
                    st.write(f"**Cantidad:** {serv.get('quantity', 0)}")
                    st.write(f"**Ubicación:** {serv.get('ubicacion', 'No especificada')}")
                with col2:
                    st.write(f"**Precio unitario:** {formato_cop(serv.get('price', 0))}")
                    st.write(f"**Valor total:** {formato_cop(serv.get('total_value', 0))}")
                    st.write(f"**Calidad:** {serv.get('service_quality', '')}")
                if st.button(f"🗑️ Eliminar", key=f"del_serv_{i}"):
                    st.session_state.temp_data["services"].pop(i)
                    st.rerun()
    
    with st.form("step5_form"):
        st.subheader("➕ Agregar nuevo servicio")
        col1, col2 = st.columns(2)
        with col1:
            serv_name = st.text_input("Nombre del servicio *", key="serv_name")
            serv_unit = st.text_input("Unidad de medida (horas, días, viajes, etc.) *", key="serv_unit")
            serv_area = st.number_input("Área ocupada (m²)", min_value=0.0, step=10.0, key="serv_area")
        with col2:
            serv_freq = st.selectbox("Periodicidad", PERIODICIDADES, key="serv_freq")
            serv_quality = st.selectbox("Calidad del servicio", CALIDADES, key="serv_quality")
        
        st.subheader("📍 Ubicación del servicio")
        ubicacion_servicio = st.selectbox("¿Dónde se ofrece este servicio?", UBICACION_PRODUCCION, key="ubicacion_serv")
        
        # Solo mostrar selección de predio adicional si la ubicación es "Predio Adicional"
        ubicacion_completa_serv = ubicacion_servicio
        if ubicacion_servicio == "Predio Adicional":
            if st.session_state.predios_adicionales:
                nombres_predios = [p["land_name"] for p in st.session_state.predios_adicionales]
                predio_seleccionado_serv = st.selectbox("Selecciona el predio adicional", nombres_predios, key="predio_seleccionado_serv")
                ubicacion_completa_serv = f"Predio Adicional: {predio_seleccionado_serv}"
            else:
                st.warning("⚠️ No hay predios adicionales registrados. Agrega uno en el Paso 3.")
                ubicacion_completa_serv = "Predio Adicional (sin predios registrados)"
        
        col3, col4 = st.columns(2)
        with col3:
            serv_quantity = st.number_input("Cantidad ofrecida por periodo *", min_value=0.0, step=1.0, key="serv_quantity")
            serv_price = st.number_input("Precio por unidad (COP) *", min_value=0.0, step=100.0, key="serv_price")
        with col4:
            total_value = serv_quantity * serv_price
            st.number_input("💰 Valor total vendido por periodo (COP)", value=total_value, disabled=True)
            st.caption(f"💡 Cálculo: {serv_quantity} × {formato_cop(serv_price)} = {formato_cop(total_value)}")
        
        agregar = st.form_submit_button("➕ Agregar servicio")
        if agregar:
            if serv_name and serv_unit and serv_quantity > 0 and serv_price > 0:
                st.session_state.temp_data["services"].append({
                    "service_name": serv_name,
                    "measure_unit": serv_unit,
                    "occupied_area_m2": serv_area,
                    "season_start": date.today(),
                    "season_end": None,
                    "frequency": serv_freq,
                    "quantity": serv_quantity,
                    "price": serv_price,
                    "total_value": total_value,
                    "service_quality": serv_quality,
                    "ubicacion": ubicacion_completa_serv
                })
                st.success(f"✅ {serv_name} agregado en {ubicacion_completa_serv}")
                st.rerun()
            else:
                st.error("Nombre, unidad, cantidad y precio son obligatorios")
        
        st.markdown("---")
        st.subheader("📤 Finalizar formulario")
        st.info("Revisa que todos los datos estén correctos antes de guardar.")
        
        # 🔴 ESTE ES EL BOTÓN DE GUARDAR - DENTRO DEL FORMULARIO (BIEN)
        guardar = st.form_submit_button("✅ Guardar todo en la base de datos", use_container_width=True)
    
    # 🔴 ESTE BLOQUE DE CÓDIGO ESTÁ FUERA DEL FORMULARIO (CORREGIDO)
    # Aquí se procesa el guardado después de que el formulario se envía
    if guardar:
        try:
            survey_id = save_survey(st.session_state.temp_data)
            
            # 🎉 Mensaje de éxito con agradecimiento
            st.balloons()
            
            # Contenedor con estilo para el mensaje de éxito
            st.markdown("""
            <div style="background: linear-gradient(135deg, #4CAF50, #2E7D32); 
                        padding: 30px; 
                        border-radius: 15px; 
                        text-align: center;
                        color: white;
                        margin: 20px 0;
                        box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
                <h1 style="font-size: 48px; margin: 0;">🌾</h1>
                <h2 style="margin: 10px 0;">✅ ¡Formulario guardado con éxito!</h2>
                <p style="font-size: 18px; opacity: 0.9;">
                    ID del registro: <strong style="background: rgba(255,255,255,0.2); 
                    padding: 4px 12px; 
                    border-radius: 5px;">{}</strong>
                </p>
                <hr style="border-color: rgba(255,255,255,0.3); margin: 20px 0;">
                <p style="font-size: 20px;">🙏 ¡Gracias por tu información!</p>
                <p style="font-size: 16px; opacity: 0.9;">
                    Tus datos nos ayudan a fortalecer la cooperativa y<br>
                    mejorar la calidad de vida de todos los asociados.
                </p>
            </div>
            """.format(survey_id[:8]), unsafe_allow_html=True)
            
            # Mostrar resumen de lo guardado
            with st.expander("📋 Ver resumen de lo guardado", expanded=True):
                col_res1, col_res2 = st.columns(2)
                with col_res1:
                    st.write("**👤 Productor:**")
                    main = st.session_state.temp_data["family_members"][0]
                    st.write(f"- {main.get('nombres', '')} {main.get('apellidos', '')}")
                    st.write(f"- 📞 {main.get('phone', 'No registrado')}")
                    
                    st.write("**🏠 Vivienda:**")
                    housing = st.session_state.temp_data["housing"]
                    st.write(f"- Ubicación: {housing.get('location', 'No registrada')}")
                    st.write(f"- Área: {housing.get('built_area_m2', 0)} m²")
                    
                    st.write("**🌳 Predios:**")
                    land = st.session_state.temp_data["land"]
                    st.write(f"- Principal: {land.get('land_name', 'No registrado')}")
                    if st.session_state.predios_adicionales:
                        for p in st.session_state.predios_adicionales:
                            st.write(f"- Adicional: {p.get('land_name', '')}")
                
                with col_res2:
                    st.write("**🌽 Productos:**")
                    if st.session_state.temp_data["productions"]:
                        for prod in st.session_state.temp_data["productions"]:
                            st.write(f"- {prod.get('product_name', '')}: {prod.get('quantity_produced', 0)} {prod.get('measure_unit', '')}")
                    else:
                        st.write("- No hay productos registrados")
                    
                    st.write("**🛠️ Servicios:**")
                    if st.session_state.temp_data["services"]:
                        for serv in st.session_state.temp_data["services"]:
                            st.write(f"- {serv.get('service_name', '')}: {serv.get('quantity', 0)} {serv.get('measure_unit', '')}")
                    else:
                        st.write("- No hay servicios registrados")
            
            # 🔴 BOTÓN "Registrar otro productor" - FUERA DEL FORMULARIO (BIEN)
            # Se muestra solo después de guardar exitosamente
            if st.button("📝 Registrar otro productor", use_container_width=True):
                for key in list(st.session_state.keys()):
                    if key not in ["authenticated", "admin_username", "admin_mode"]:
                        del st.session_state[key]
                st.rerun()
                
        except Exception as e:
            st.error(f"Error al guardar: {e}")
    
    # 🔴 BOTÓN "Atrás" - FUERA DEL FORMULARIO (BIEN)
    col_b, _ = st.columns(2)
    with col_b:
        if st.button("← Atrás"):
            go_to_step(4)

# ========== FUNCIONES DE ADMINISTRACIÓN ==========
def login_page():
    st.sidebar.title("🔐 Acceso Administrador")
    username = st.sidebar.text_input("Usuario")
    password = st.sidebar.text_input("Contraseña", type="password")
    
    if st.sidebar.button("Iniciar sesión"):
        admin_client = get_admin_client()
        if not admin_client:
            return False
        
        hashed = hash_password(password)
        try:
            result = admin_client.table("admin_users").select("*").eq("username", username).eq("password_hash", hashed).execute()
            if result.data:
                st.session_state.authenticated = True
                st.session_state.admin_username = username
                st.session_state.admin_mode = True
                st.success("¡Bienvenido!")
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
        except Exception as e:
            st.error(f"Error de autenticación: {e}")
    
    if st.session_state.get("authenticated", False):
        st.sidebar.success(f"✅ Conectado como: {username}")
        return True
    return False

def view_records():
    st.header("📋 Registros de Productores")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        tipo = st.selectbox("Filtrar por tipo", ["Todos", "INICIAL", "ACTUAL"])
    with col2:
        fecha_inicio = st.date_input("Fecha desde", value=None)
    with col3:
        fecha_fin = st.date_input("Fecha hasta", value=None)
    
    client = get_admin_client()
    if not client:
        return
    
    query = client.table("survey_registry").select("*").order("created_at", desc=True)
    if tipo != "Todos":
        query = query.eq("type", tipo)
    if fecha_inicio:
        query = query.gte("registration_date", str(fecha_inicio))
    if fecha_fin:
        query = query.lte("registration_date", str(fecha_fin))
    
    result = query.execute()
    surveys = result.data
    
    if surveys:
        for survey in surveys:
            with st.expander(f"📝 Registro {survey['id'][:8]} - {survey['registration_date']} ({survey['type']})", expanded=False):
                family = client.table("family_members").select("*").eq("survey_id", survey["id"]).eq("is_main", True).execute()
                if family.data:
                    main = family.data[0]
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Productor:** {main['nombres']} {main['apellidos']}")
                    with col2:
                        st.write(f"**Teléfono:** {main.get('phone', 'No registrado')}")
                    with col3:
                        sisben = main.get('sisben_subgrupo')
                        if sisben and sisben != "No aplica":
                            color = get_sisben_color(sisben)
                            st.write(f"**Sisbén:** {color} {sisben}")
                
                photos = client.table("survey_photos").select("*").eq("survey_id", survey["id"]).execute()
                if photos.data:
                    st.write("**📸 Fotos:**")
                    cols = st.columns(3)
                    for i, photo in enumerate(photos.data[:3]):
                        with cols[i]:
                            st.image(photo["photo_url"], caption=photo["photo_description"], use_container_width=True)
                
                # Botones de acción
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button(f"📄 Ver detalle", key=f"detail_{survey['id']}"):
                        show_full_survey(survey["id"])
                
                with col_btn2:
                    # Botón de eliminar (solo para admin)
                    if st.button(f"🗑️ Eliminar", key=f"delete_{survey['id']}", type="secondary"):
                        st.session_state.delete_id = survey["id"]
                        st.rerun()
                
                # Confirmación de eliminación
                if st.session_state.get("delete_id") == survey["id"]:
                    st.warning("⚠️ ¿Estás seguro de eliminar este registro? Esta acción no se puede deshacer.")
                    col_confirm1, col_confirm2 = st.columns(2)
                    with col_confirm1:
                        if st.button("✅ Sí, eliminar", key=f"confirm_delete_{survey['id']}"):
                            if delete_survey(survey["id"]):
                                st.success("✅ Registro eliminado exitosamente")
                                st.session_state.delete_id = None
                                st.rerun()
                            else:
                                st.error("❌ Error al eliminar el registro")
                    with col_confirm2:
                        if st.button("❌ Cancelar", key=f"cancel_delete_{survey['id']}"):
                            st.session_state.delete_id = None
                            st.rerun()
    else:
        st.info("No hay registros para mostrar")

# ========== ESTADÍSTICAS MEJORADAS ==========
def show_statistics():
    st.header("📈 Estadísticas Generales")
    
    client = get_admin_client()
    if not client:
        return
    
    total = client.table("survey_registry").select("count", count="exact").execute()
    inicial = client.table("survey_registry").select("count", count="exact").eq("type", "INICIAL").execute()
    actual = client.table("survey_registry").select("count", count="exact").eq("type", "ACTUAL").execute()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="value">{total.count}</div>
            <div class="label">Total Registros</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #2193b0 0%, #6dd5ed 100%);">
            <div class="value">{inicial.count}</div>
            <div class="label">Registros Iniciales</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);">
            <div class="value">{actual.count}</div>
            <div class="label">Actualizaciones</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        porcentaje = f"{actual.count/total.count*100:.1f}%" if total.count > 0 else "0%"
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #fc4a1a 0%, #f7b733 100%);">
            <div class="value">{porcentaje}</div>
            <div class="label">% Actualizados</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🌽 Top 10 Productos")
        products = client.table("production_capacity").select("product_name").execute()
        if products.data:
            df = pd.DataFrame(products.data)
            top = df["product_name"].value_counts().head(10)
            fig = px.bar(x=top.values, y=top.index, orientation='h', title="Productos más producidos", labels={'x': 'Cantidad de productores', 'y': 'Producto'}, color=top.values, color_continuous_scale='Viridis')
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay productos registrados")
    
    with col2:
        st.subheader("🛠️ Top 10 Servicios")
        services = client.table("service_capacity").select("service_name").execute()
        if services.data:
            df = pd.DataFrame(services.data)
            top = df["service_name"].value_counts().head(10)
            fig = px.bar(x=top.values, y=top.index, orientation='h', title="Servicios más ofrecidos", labels={'x': 'Cantidad de oferentes', 'y': 'Servicio'}, color=top.values, color_continuous_scale='Plasma')
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay servicios registrados")
    
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Distribución Sisbén IV")
        familiares = client.table("family_members").select("sisben_grupo, sisben_subgrupo").eq("is_main", True).execute()
        if familiares.data:
            df_sisben = pd.DataFrame(familiares.data)
            if "sisben_grupo" in df_sisben.columns:
                grupos_count = df_sisben["sisben_grupo"].value_counts()
                fig = px.pie(values=grupos_count.values, names=grupos_count.index, title="Distribución por Grupo Sisbén", color_discrete_sequence=px.colors.sequential.RdBu)
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📋 Resumen")
        if familiares.data:
            df_sisben = pd.DataFrame(familiares.data)
            if "sisben_grupo" in df_sisben.columns:
                grupos_count = df_sisben["sisben_grupo"].value_counts()
                for grupo, count in grupos_count.items():
                    if grupo:
                        nombre_grupo = get_grupo_descripcion(grupo) or "Sin grupo"
                        color = "🔴" if grupo == "A" else "🟠" if grupo == "B" else "🟡" if grupo == "C" else "🟢"
                        st.metric(label=f"{color} Grupo {grupo} - {nombre_grupo}", value=f"{count} personas", delta=f"{count/len(df_sisben)*100:.1f}%")
    
    st.markdown("---")
    
    st.subheader("📍 Producción por Ubicación")
    prod_data = client.table("production_capacity").select("ubicacion, total_price").execute()
    if prod_data.data:
        df_prod = pd.DataFrame(prod_data.data)
        ubicacion_sum = df_prod.groupby("ubicacion")["total_price"].sum().reset_index()
        fig = px.bar(ubicacion_sum, x="ubicacion", y="total_price", title="Valor de Producción por Ubicación", labels={'total_price': 'Valor Total (COP)', 'ubicacion': 'Ubicación'}, color="ubicacion", color_discrete_sequence=px.colors.qualitative.Set3)
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("💰 Resumen de Ingresos")
    col1, col2, col3 = st.columns(3)
    prod_total = client.table("production_capacity").select("total_price").execute()
    serv_total = client.table("service_capacity").select("total_value").execute()
    total_prod = sum([p["total_price"] for p in prod_total.data]) if prod_total.data else 0
    total_serv = sum([s["total_value"] for s in serv_total.data]) if serv_total.data else 0
    with col1:
        st.metric("💰 Producción Total", formato_cop(total_prod))
    with col2:
        st.metric("💰 Servicios Totales", formato_cop(total_serv))
    with col3:
        st.metric("💰 Ingresos Totales", formato_cop(total_prod + total_serv))

# ========== FUNCIONES DE EXPORTACIÓN ==========
def export_consolidated_excel():
    """Exporta todos los datos en una sola hoja de Excel"""
    client = get_admin_client()
    if not client:
        return None
    
    try:
        surveys = client.table("survey_registry").select("*").execute().data
    except Exception as e:
        st.error(f"Error al obtener registros: {e}")
        return None
    
    if not surveys:
        st.warning("No hay registros en la base de datos")
        return None
    
    consolidated_data = []
    
    for survey in surveys:
        try:
            survey_id = survey["id"]
            
            family = client.table("family_members").select("*").eq("survey_id", survey_id).eq("is_main", True).execute().data
            if not family:
                continue
            main = family[0]
            
            other_family = client.table("family_members").select("*").eq("survey_id", survey_id).eq("is_main", False).execute().data
            housing = client.table("housing").select("*").eq("survey_id", survey_id).execute().data
            housing_data = housing[0] if housing else {}
            lands = client.table("land").select("*").eq("survey_id", survey_id).execute().data
            productions = client.table("production_capacity").select("*").eq("survey_id", survey_id).execute().data
            services = client.table("service_capacity").select("*").eq("survey_id", survey_id).execute().data
            
            base_row = {
                "ID Registro": survey_id,
                "Fecha Registro": survey.get("registration_date", ""),
                "Tipo": survey.get("type", ""),
                "Razón": survey.get("reason", ""),
                "Firma": "Sí" if survey.get("signature") else "No",
                "Productor Nombres": main.get("nombres", ""),
                "Productor Apellidos": main.get("apellidos", ""),
                "Tipo Identificación": main.get("id_type", ""),
                "Número Identificación": main.get("id_number", ""),
                "Fecha Nacimiento": main.get("birth_date", ""),
                "Teléfono": main.get("phone", ""),
                "Email": main.get("email", ""),
                "Nivel Escolar": main.get("education_level", ""),
                "Disciplina": main.get("discipline", ""),
                "Ocupación": main.get("occupation", ""),
                "Sisbén Ficha": main.get("sisben_id", ""),
                "Sisbén Subgrupo": main.get("sisben_subgrupo", ""),
                "Sisbén Grupo": main.get("sisben_grupo", ""),
                "Tipo Propiedad Vivienda": housing_data.get("property_type", ""),
                "Ubicación Vivienda": housing_data.get("location", ""),
                "ID Catastral Vivienda": housing_data.get("cadastral_id", ""),
                "Área Construida (m²)": housing_data.get("built_area_m2", 0),
                "Área Patio (m²)": housing_data.get("patio_area_m2", 0),
                "Patio Productivo": "Sí" if housing_data.get("patio_productivo") else "No",
                "Calidad Agua Vivienda": housing_data.get("water_quality", ""),
                "Calidad Energía Vivienda": housing_data.get("energy_quality", ""),
                "Calidad Internet Vivienda": housing_data.get("internet_quality", ""),
                "Alcantarillado Vivienda": housing_data.get("sewage", ""),
                "Aseo Vivienda": housing_data.get("waste_management", ""),
            }
            
            for i, fam in enumerate(other_family[:5], 1):
                base_row.update({
                    f"Familiar {i} Nombres": fam.get("nombres", ""),
                    f"Familiar {i} Apellidos": fam.get("apellidos", ""),
                    f"Familiar {i} Parentesco": fam.get("parentesco", ""),
                    f"Familiar {i} Teléfono": fam.get("phone", ""),
                    f"Familiar {i} Ocupación": fam.get("occupation", ""),
                })
            
            predio_count = 0
            for land in lands:
                predio_count += 1
                ubicacion = "Predio Principal" if predio_count == 1 else f"Predio Adicional {predio_count-1}"
                
                producciones_predio = [p for p in productions if ubicacion in p.get("ubicacion", "")]
                servicios_predio = [s for s in services if ubicacion in s.get("ubicacion", "")]
                
                base_row.update({
                    f"{ubicacion} Nombre": land.get("land_name", ""),
                    f"{ubicacion} Tipo Propiedad": land.get("property_type", ""),
                    f"{ubicacion} Ubicación": land.get("location", ""),
                    f"{ubicacion} ID Catastral": land.get("cadastral_id", ""),
                    f"{ubicacion} Área (m²)": land.get("total_area_m2", 0),
                    f"{ubicacion} Tipo Suelo": land.get("tipo_suelo", ""),
                    f"{ubicacion} Uso Suelo": land.get("land_type", ""),
                    f"{ubicacion} Inundable": "Sí" if land.get("is_floodable") else "No",
                    f"{ubicacion} Calidad Agua": land.get("water_quality", ""),
                    f"{ubicacion} Calidad Energía": land.get("energy_quality", ""),
                    f"{ubicacion} Productos": ", ".join([p["product_name"] for p in producciones_predio]),
                    f"{ubicacion} Cantidad Productos": len(producciones_predio),
                    f"{ubicacion} Producción Total (COP)": sum([p.get("total_price", 0) for p in producciones_predio]),
                    f"{ubicacion} Servicios": ", ".join([s["service_name"] for s in servicios_predio]),
                    f"{ubicacion} Cantidad Servicios": len(servicios_predio),
                    f"{ubicacion} Servicios Total (COP)": sum([s.get("total_value", 0) for s in servicios_predio]),
                })
            
            for i, prod in enumerate(productions[:10], 1):
                base_row.update({
                    f"Producto {i}": prod.get("product_name", ""),
                    f"Producto {i} Unidad": prod.get("measure_unit", ""),
                    f"Producto {i} Cantidad": prod.get("quantity_produced", 0),
                    f"Producto {i} Precio Unitario": prod.get("unit_price", 0),
                    f"Producto {i} Total": prod.get("total_price", 0),
                    f"Producto {i} Ubicación": prod.get("ubicacion", ""),
                    f"Producto {i} Frecuencia": prod.get("frequency", ""),
                    f"Producto {i} Calidad": prod.get("product_quality", ""),
                })
            
            for i, serv in enumerate(services[:10], 1):
                base_row.update({
                    f"Servicio {i}": serv.get("service_name", ""),
                    f"Servicio {i} Unidad": serv.get("measure_unit", ""),
                    f"Servicio {i} Cantidad": serv.get("quantity", 0),
                    f"Servicio {i} Precio Unitario": serv.get("price", 0),
                    f"Servicio {i} Total": serv.get("total_value", 0),
                    f"Servicio {i} Ubicación": serv.get("ubicacion", ""),
                    f"Servicio {i} Frecuencia": serv.get("frequency", ""),
                    f"Servicio {i} Calidad": serv.get("service_quality", ""),
                })
            
            total_produccion = sum([p.get("total_price", 0) for p in productions])
            total_servicios = sum([s.get("total_value", 0) for s in services])
            base_row.update({
                "Total Producción (COP)": total_produccion,
                "Total Servicios (COP)": total_servicios,
                "Total Ingresos (COP)": total_produccion + total_servicios,
                "Cantidad Productos": len(productions),
                "Cantidad Servicios": len(services),
            })
            
            consolidated_data.append(base_row)
            
        except Exception as e:
            st.warning(f"Error procesando registro {survey.get('id', 'desconocido')[:8]}: {e}")
            continue
    
    if not consolidated_data:
        st.warning("No se pudieron consolidar datos. Verifica que los registros tengan productor principal.")
        return None
    
    df = pd.DataFrame(consolidated_data)
    
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name="Datos Consolidados", index=False)
            
            workbook = writer.book
            worksheet = writer.sheets["Datos Consolidados"]
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        return output.getvalue()
    except Exception as e:
        st.error(f"Error al crear Excel: {e}")
        return None

def export_all_data():
    """Función principal de exportación"""
    st.header("📤 Exportar Datos")
    
    export_type = st.radio(
        "Tipo de exportación:",
        ["📊 Consolidado (una hoja con todos los datos)", "📋 Datos separados por tablas"]
    )
    
    if st.button("📥 Generar Exportación", use_container_width=True):
        with st.spinner("Generando archivo de exportación..."):
            if export_type.startswith("📊 Consolidado"):
                excel_data = export_consolidated_excel()
                if excel_data:
                    st.download_button(
                        label="📥 Descargar Excel Consolidado",
                        data=excel_data,
                        file_name=f"cooprogreso_consolidado_{date.today()}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                    st.success("✅ Excel consolidado generado exitosamente")
                else:
                    st.error("❌ No hay datos para exportar")
            else:
                tables_to_export = [
                    "survey_registry", "family_members", "housing", "land", 
                    "production_capacity", "service_capacity", "survey_photos"
                ]
                
                client = get_admin_client()
                if not client:
                    return
                
                output = io.BytesIO()
                exported_tables = []
                
                try:
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        for table in tables_to_export:
                            try:
                                data = client.table(table).select("*").execute().data
                                if data:
                                    df = pd.DataFrame(data)
                                    df.to_excel(writer, sheet_name=table[:31], index=False)
                                    exported_tables.append(table)
                                else:
                                    empty_df = pd.DataFrame({"Mensaje": [f"La tabla {table} está vacía"]})
                                    empty_df.to_excel(writer, sheet_name=table[:31], index=False)
                                    exported_tables.append(f"{table} (vacía)")
                            except Exception as e:
                                exported_tables.append(f"{table} (error)")
                    
                    if exported_tables:
                        st.download_button(
                            label="📥 Descargar Excel por Tablas",
                            data=output.getvalue(),
                            file_name=f"cooprogreso_tablas_{date.today()}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                        st.success(f"✅ Excel generado exitosamente")
                    else:
                        st.error("❌ No se pudo exportar ninguna tabla")
                        
                except Exception as e:
                    st.error(f"Error al exportar: {e}")

# ========== FUNCIÓN PARA ELIMINAR REGISTRO (OPTIMIZADA) ==========
def delete_survey(survey_id):
    """Elimina un registro completo de la base de datos (optimizado)"""
    client = get_admin_client()
    if not client:
        return False
    
    try:
        # Eliminar usando una sola transacción
        # Primero eliminamos todas las tablas relacionadas en lote
        
        # 1. Eliminar fotos
        client.table("survey_photos").delete().eq("survey_id", survey_id).execute()
        
        # 2. Eliminar servicios
        client.table("service_capacity").delete().eq("survey_id", survey_id).execute()
        
        # 3. Eliminar producciones
        client.table("production_capacity").delete().eq("survey_id", survey_id).execute()
        
        # 4. Eliminar predios
        client.table("land").delete().eq("survey_id", survey_id).execute()
        
        # 5. Eliminar vivienda
        client.table("housing").delete().eq("survey_id", survey_id).execute()
        
        # 6. Eliminar familiares
        client.table("family_members").delete().eq("survey_id", survey_id).execute()
        
        # 7. Eliminar el registro principal
        client.table("survey_registry").delete().eq("id", survey_id).execute()
        
        return True
    except Exception as e:
        st.error(f"Error al eliminar: {e}")
        return False

# ========== FUNCIÓN PARA LIMPIAR TODOS LOS DATOS (OPTIMIZADA) ==========
def clean_test_data():
    """Elimina todos los datos de prueba (optimizado para evitar timeouts)"""
    st.subheader("🧹 Limpiar Datos de Prueba")
    st.warning("⚠️ Esta acción eliminará TODOS los registros de la base de datos")
    st.info("Si solo quieres eliminar registros específicos, usa la opción 'Ver Registros' y elimina individualmente")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 Ver cantidad de registros", use_container_width=True):
            client = get_admin_client()
            if client:
                try:
                    total = client.table("survey_registry").select("count", count="exact").execute()
                    st.info(f"📊 Total de registros: {total.count}")
                except Exception as e:
                    st.error(f"Error al contar registros: {e}")
    
    with col2:
        if st.button("🗑️ ELIMINAR TODOS LOS REGISTROS", use_container_width=True, type="secondary"):
            st.session_state.confirm_delete_all = True
    
    if st.session_state.get("confirm_delete_all", False):
        st.error("⚠️ ¿ESTÁS SEGURO? Esta acción es IRREVERSIBLE")
        st.info("Se eliminarán TODOS los registros de todas las tablas")
        
        # Opción para eliminar en lotes
        batch_size = st.number_input(
            "Registros por lote (recomendado: 5-10 para evitar timeouts)",
            min_value=1,
            max_value=50,
            value=5
        )
        
        col_confirm1, col_confirm2 = st.columns(2)
        with col_confirm1:
            if st.button("✅ SÍ, ELIMINAR TODO", use_container_width=True):
                client = get_admin_client()
                if client:
                    try:
                        with st.spinner(f"Eliminando todos los datos en lotes de {batch_size}..."):
                            # Obtener todos los IDs de registros
                            surveys = client.table("survey_registry").select("id").execute()
                            survey_ids = [s["id"] for s in surveys.data]
                            
                            if not survey_ids:
                                st.info("No hay registros para eliminar")
                                st.session_state.confirm_delete_all = False
                                st.rerun()
                            
                            total = len(survey_ids)
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            # Eliminar en lotes
                            for i in range(0, total, batch_size):
                                batch = survey_ids[i:i+batch_size]
                                status_text.text(f"Eliminando lote {i//batch_size + 1} de {(total + batch_size - 1)//batch_size}...")
                                
                                for survey_id in batch:
                                    try:
                                        # Eliminar en orden
                                        client.table("survey_photos").delete().eq("survey_id", survey_id).execute()
                                        client.table("service_capacity").delete().eq("survey_id", survey_id).execute()
                                        client.table("production_capacity").delete().eq("survey_id", survey_id).execute()
                                        client.table("land").delete().eq("survey_id", survey_id).execute()
                                        client.table("housing").delete().eq("survey_id", survey_id).execute()
                                        client.table("family_members").delete().eq("survey_id", survey_id).execute()
                                        client.table("survey_registry").delete().eq("id", survey_id).execute()
                                    except Exception as e:
                                        st.warning(f"Error eliminando registro {survey_id[:8]}: {e}")
                                        continue
                                
                                # Actualizar barra de progreso
                                progress = min((i + batch_size) / total, 1.0)
                                progress_bar.progress(progress)
                            
                            status_text.text("✅ Eliminación completada")
                            st.success(f"✅ {total} registros eliminados exitosamente")
                            st.session_state.confirm_delete_all = False
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"Error al eliminar: {e}")
                        st.info("💡 Si el error persiste, intenta con un número menor de registros por lote")
        with col_confirm2:
            if st.button("❌ Cancelar", use_container_width=True):
                st.session_state.confirm_delete_all = False
                st.rerun()
                
# ========== FUNCIONES DE ADMINISTRACIÓN ==========
def login_page():
    st.sidebar.title("🔐 Acceso Administrador")
    username = st.sidebar.text_input("Usuario")
    password = st.sidebar.text_input("Contraseña", type="password")
    
    if st.sidebar.button("Iniciar sesión"):
        admin_client = get_admin_client()
        if not admin_client:
            return False
        
        hashed = hash_password(password)
        try:
            result = admin_client.table("admin_users").select("*").eq("username", username).eq("password_hash", hashed).execute()
            if result.data:
                st.session_state.authenticated = True
                st.session_state.admin_username = username
                st.session_state.admin_mode = True
                st.success("¡Bienvenido!")
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
        except Exception as e:
            st.error(f"Error de autenticación: {e}")
    
    if st.session_state.get("authenticated", False):
        st.sidebar.success(f"✅ Conectado como: {username}")
        return True
    return False

def view_records():
    st.header("📋 Registros de Productores")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        tipo = st.selectbox("Filtrar por tipo", ["Todos", "INICIAL", "ACTUAL"])
    with col2:
        fecha_inicio = st.date_input("Fecha desde", value=None)
    with col3:
        fecha_fin = st.date_input("Fecha hasta", value=None)
    
    client = get_admin_client()
    if not client:
        return
    
    query = client.table("survey_registry").select("*").order("created_at", desc=True)
    if tipo != "Todos":
        query = query.eq("type", tipo)
    if fecha_inicio:
        query = query.gte("registration_date", str(fecha_inicio))
    if fecha_fin:
        query = query.lte("registration_date", str(fecha_fin))
    
    result = query.execute()
    surveys = result.data
    
    if surveys:
        for survey in surveys:
            with st.expander(f"📝 Registro {survey['id'][:8]} - {survey['registration_date']} ({survey['type']})", expanded=False):
                family = client.table("family_members").select("*").eq("survey_id", survey["id"]).eq("is_main", True).execute()
                if family.data:
                    main = family.data[0]
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Productor:** {main['nombres']} {main['apellidos']}")
                    with col2:
                        st.write(f"**Teléfono:** {main.get('phone', 'No registrado')}")
                    with col3:
                        sisben = main.get('sisben_subgrupo')
                        if sisben and sisben != "No aplica":
                            color = get_sisben_color(sisben)
                            st.write(f"**Sisbén:** {color} {sisben}")
                
                photos = client.table("survey_photos").select("*").eq("survey_id", survey["id"]).execute()
                if photos.data:
                    st.write("**📸 Fotos:**")
                    cols = st.columns(3)
                    for i, photo in enumerate(photos.data[:3]):
                        with cols[i]:
                            st.image(photo["photo_url"], caption=photo["photo_description"], use_container_width=True)
                
                # Botones de acción
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button(f"📄 Ver detalle", key=f"detail_{survey['id']}"):
                        show_full_survey(survey["id"])
                
                with col_btn2:
                    # Botón de eliminar (solo para admin)
                    if st.button(f"🗑️ Eliminar", key=f"delete_{survey['id']}", type="secondary"):
                        st.session_state.delete_id = survey["id"]
                        st.rerun()
                
                # Confirmación de eliminación
                if st.session_state.get("delete_id") == survey["id"]:
                    st.warning("⚠️ ¿Estás seguro de eliminar este registro? Esta acción no se puede deshacer.")
                    col_confirm1, col_confirm2 = st.columns(2)
                    with col_confirm1:
                        if st.button("✅ Sí, eliminar", key=f"confirm_delete_{survey['id']}"):
                            if delete_survey(survey["id"]):
                                st.success("✅ Registro eliminado exitosamente")
                                st.session_state.delete_id = None
                                st.rerun()
                            else:
                                st.error("❌ Error al eliminar el registro")
                    with col_confirm2:
                        if st.button("❌ Cancelar", key=f"cancel_delete_{survey['id']}"):
                            st.session_state.delete_id = None
                            st.rerun()
    else:
        st.info("No hay registros para mostrar")

def show_full_survey(survey_id):
    st.subheader("📄 Detalle completo del registro")
    
    client = get_admin_client()
    if not client:
        return
    
    family = client.table("family_members").select("*").eq("survey_id", survey_id).execute()
    housing = client.table("housing").select("*").eq("survey_id", survey_id).execute()
    land = client.table("land").select("*").eq("survey_id", survey_id).execute()
    productions = client.table("production_capacity").select("*").eq("survey_id", survey_id).execute()
    services = client.table("service_capacity").select("*").eq("survey_id", survey_id).execute()
    photos = client.table("survey_photos").select("*").eq("survey_id", survey_id).execute()
    
    tabs = st.tabs(["👨‍👩‍👧‍👦 Familia", "🏠 Vivienda", "🌳 Predio", "🌽 Producciones", "🛠️ Servicios", "📸 Fotos"])
    
    with tabs[0]:
        if family.data:
            df = pd.DataFrame(family.data)
            columnas = ["nombres", "apellidos", "parentesco", "id_type", "id_number", "phone", "occupation", "sisben_subgrupo", "sisben_grupo"]
            columnas_existentes = [col for col in columnas if col in df.columns]
            st.dataframe(df[columnas_existentes], use_container_width=True)
    
    with tabs[1]:
        if housing.data:
            st.dataframe(pd.DataFrame(housing.data[0], index=[0]), use_container_width=True)
    
    with tabs[2]:
        if land.data:
            st.dataframe(pd.DataFrame(land.data), use_container_width=True)
    
    with tabs[3]:
        if productions.data:
            df = pd.DataFrame(productions.data)
            if "total_price" in df.columns:
                df["total_price"] = df["total_price"].apply(lambda x: formato_cop(x))
            if "unit_price" in df.columns:
                df["unit_price"] = df["unit_price"].apply(lambda x: formato_cop(x))
            st.dataframe(df, use_container_width=True)
    
    with tabs[4]:
        if services.data:
            df = pd.DataFrame(services.data)
            if "total_value" in df.columns:
                df["total_value"] = df["total_value"].apply(lambda x: formato_cop(x))
            if "price" in df.columns:
                df["price"] = df["price"].apply(lambda x: formato_cop(x))
            st.dataframe(df, use_container_width=True)
    
    with tabs[5]:
        if photos.data:
            cols = st.columns(3)
            for i, photo in enumerate(photos.data):
                with cols[i % 3]:
                    st.image(photo["photo_url"], caption=f"{photo['photo_description']} ({photo['photo_type']})", use_container_width=True)
        else:
            st.info("No hay fotos")
    
    if st.button("Cerrar detalle"):
        st.rerun()

# ========== ESTADÍSTICAS MEJORADAS ==========
def show_statistics():
    st.header("📈 Estadísticas Generales")
    
    client = get_admin_client()
    if not client:
        return
    
    total = client.table("survey_registry").select("count", count="exact").execute()
    inicial = client.table("survey_registry").select("count", count="exact").eq("type", "INICIAL").execute()
    actual = client.table("survey_registry").select("count", count="exact").eq("type", "ACTUAL").execute()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="value">{total.count}</div>
            <div class="label">Total Registros</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #2193b0 0%, #6dd5ed 100%);">
            <div class="value">{inicial.count}</div>
            <div class="label">Registros Iniciales</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);">
            <div class="value">{actual.count}</div>
            <div class="label">Actualizaciones</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        porcentaje = f"{actual.count/total.count*100:.1f}%" if total.count > 0 else "0%"
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #fc4a1a 0%, #f7b733 100%);">
            <div class="value">{porcentaje}</div>
            <div class="label">% Actualizados</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🌽 Top 10 Productos")
        products = client.table("production_capacity").select("product_name").execute()
        if products.data:
            df = pd.DataFrame(products.data)
            top = df["product_name"].value_counts().head(10)
            fig = px.bar(x=top.values, y=top.index, orientation='h', title="Productos más producidos", labels={'x': 'Cantidad de productores', 'y': 'Producto'}, color=top.values, color_continuous_scale='Viridis')
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay productos registrados")
    
    with col2:
        st.subheader("🛠️ Top 10 Servicios")
        services = client.table("service_capacity").select("service_name").execute()
        if services.data:
            df = pd.DataFrame(services.data)
            top = df["service_name"].value_counts().head(10)
            fig = px.bar(x=top.values, y=top.index, orientation='h', title="Servicios más ofrecidos", labels={'x': 'Cantidad de oferentes', 'y': 'Servicio'}, color=top.values, color_continuous_scale='Plasma')
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay servicios registrados")
    
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Distribución Sisbén IV")
        familiares = client.table("family_members").select("sisben_grupo, sisben_subgrupo").eq("is_main", True).execute()
        if familiares.data:
            df_sisben = pd.DataFrame(familiares.data)
            if "sisben_grupo" in df_sisben.columns:
                grupos_count = df_sisben["sisben_grupo"].value_counts()
                fig = px.pie(values=grupos_count.values, names=grupos_count.index, title="Distribución por Grupo Sisbén", color_discrete_sequence=px.colors.sequential.RdBu)
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📋 Resumen")
        if familiares.data:
            df_sisben = pd.DataFrame(familiares.data)
            if "sisben_grupo" in df_sisben.columns:
                grupos_count = df_sisben["sisben_grupo"].value_counts()
                for grupo, count in grupos_count.items():
                    if grupo:
                        nombre_grupo = get_grupo_descripcion(grupo) or "Sin grupo"
                        color = "🔴" if grupo == "A" else "🟠" if grupo == "B" else "🟡" if grupo == "C" else "🟢"
                        st.metric(label=f"{color} Grupo {grupo} - {nombre_grupo}", value=f"{count} personas", delta=f"{count/len(df_sisben)*100:.1f}%")
    
    st.markdown("---")
    
    st.subheader("📍 Producción por Ubicación")
    prod_data = client.table("production_capacity").select("ubicacion, total_price").execute()
    if prod_data.data:
        df_prod = pd.DataFrame(prod_data.data)
        ubicacion_sum = df_prod.groupby("ubicacion")["total_price"].sum().reset_index()
        fig = px.bar(ubicacion_sum, x="ubicacion", y="total_price", title="Valor de Producción por Ubicación", labels={'total_price': 'Valor Total (COP)', 'ubicacion': 'Ubicación'}, color="ubicacion", color_discrete_sequence=px.colors.qualitative.Set3)
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("💰 Resumen de Ingresos")
    col1, col2, col3 = st.columns(3)
    prod_total = client.table("production_capacity").select("total_price").execute()
    serv_total = client.table("service_capacity").select("total_value").execute()
    total_prod = sum([p["total_price"] for p in prod_total.data]) if prod_total.data else 0
    total_serv = sum([s["total_value"] for s in serv_total.data]) if serv_total.data else 0
    with col1:
        st.metric("💰 Producción Total", formato_cop(total_prod))
    with col2:
        st.metric("💰 Servicios Totales", formato_cop(total_serv))
    with col3:
        st.metric("💰 Ingresos Totales", formato_cop(total_prod + total_serv))

# ========== FUNCIÓN PARA MOSTRAR PERMISOS AL USUARIO ==========
def show_user_permissions():
    st.sidebar.markdown("---")
    st.sidebar.subheader("ℹ️ Información")
    st.sidebar.info("""
    **🔒 Seguridad**
    - Los datos se guardan de forma segura
    - Solo el administrador puede ver los datos
    - Los usuarios solo pueden crear registros
    """)

# ========== PANEL DE ADMINISTRACIÓN ==========
def admin_panel():
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Panel de Administración")
    admin_option = st.sidebar.radio(
        "Selecciona:",
        ["📋 Ver Registros", "📈 Estadísticas", "📤 Exportar Datos", "🧹 Limpiar Datos"]
    )
    st.sidebar.markdown("---")
    st.sidebar.info("💡 Los datos se actualizan automáticamente")
    
    if admin_option == "📋 Ver Registros":
        view_records()
    elif admin_option == "📈 Estadísticas":
        show_statistics()
    elif admin_option == "📤 Exportar Datos":
        export_all_data()
    elif admin_option == "🧹 Limpiar Datos":
        clean_test_data()

# ========== MAIN ==========
def main():
    # Inicializar variables de sesión
    if "step" not in st.session_state:
        st.session_state.step = 1
    if "temp_data" not in st.session_state:
        st.session_state.temp_data = {}
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "admin_username" not in st.session_state:
        st.session_state.admin_username = None
    if "admin_mode" not in st.session_state:
        st.session_state.admin_mode = False
    if "extra_family" not in st.session_state:
        st.session_state.extra_family = []
    if "predios_adicionales" not in st.session_state:
        st.session_state.predios_adicionales = []
    if "delete_id" not in st.session_state:
        st.session_state.delete_id = None
    if "confirm_delete_all" not in st.session_state:
        st.session_state.confirm_delete_all = False
    
    st.title("🌾 COOPROGRESO - Sistema de Capacidad Productiva")
    
    # Sidebar
    with st.sidebar:
        if not st.session_state.authenticated:
            login_page()
        else:
            st.success(f"✅ Conectado: {st.session_state.admin_username}")
            if st.button("🚪 Cerrar sesión", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.admin_username = None
                st.session_state.admin_mode = False
                st.rerun()
            admin_panel()
        
        show_user_permissions()
    
    # Mostrar contenido según modo
    if st.session_state.authenticated and st.session_state.admin_mode:
        st.markdown("---")
        st.info("👈 Selecciona una opción en el panel izquierdo para administrar los datos")
        client = get_admin_client()
        if client:
            total = client.table("survey_registry").select("count", count="exact").execute()
            if total.count > 0:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📋 Total Registros", total.count)
                with col2:
                    inicial = client.table("survey_registry").select("count", count="exact").eq("type", "INICIAL").execute()
                    st.metric("📝 Registros Iniciales", inicial.count)
                with col3:
                    actual = client.table("survey_registry").select("count", count="exact").eq("type", "ACTUAL").execute()
                    st.metric("🔄 Actualizaciones", actual.count)
    else:
        st.info("📝 Completa el formulario para registrar tus datos. Solo el administrador puede ver la información.")
        with st.container():
            if st.session_state.step == 1:
                step1()
            elif st.session_state.step == 2:
                step2()
            elif st.session_state.step == 3:
                step3()
            elif st.session_state.step == 4:
                step4()
            elif st.session_state.step == 5:
                step5()

if __name__ == "__main__":
    main()
