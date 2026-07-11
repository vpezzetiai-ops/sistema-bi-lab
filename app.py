import streamlit as st
import pandas as pd
import plotly.express as px
import re
import PyPDF2
from streamlit_gsheets import GSheetsConnection
import time

# ==========================================
# 1. CONFIGURAÇÕES INICIAIS
# ==========================================
st.set_page_config(page_title="Sistema BI - São Francisco", layout="wide", initial_sidebar_state="expanded")

COR_AZUL_BIC = '#002395'
COR_CINZA = '#808080'
PALETA_CORES = ['#002395', '#4A69BD', '#708ad4', '#808080', '#A6A6A6', '#C0C0C0', '#d9d9d9']
UNIDADES_OFICIAIS = ["1 - Serra Negra", "3 - AME", "4 - Amparo Unidade 4", "5 - Monte Alegre", "6 - Lindóia", "9 - Cenam", "10 - Amparo Unidade BPA", "12 - Águas de Lindóia", "Sede / Sem Unidade"]

# ==========================================
# 2. FUNÇÕES DE LIMPEZA E DADOS
# ==========================================
def padronizar_unidade(unidade):
    if pd.isna(unidade) or str(unidade).strip() == "" or "Não Informada" in str(unidade): return "Sede / Sem Unidade"
    numeros = re.findall(r'\d+', str(unidade))
    if not numeros: return "Sede / Sem Unidade"
    u_str = str(int(numeros[0]))
    mapa = {"1": "1 - Serra Negra", "3": "3 - AME", "4": "4 - Amparo Unidade 4", "5": "5 - Monte Alegre", "6": "6 - Lindóia", "9": "9 - Cenam", "10": "10 - Amparo Unidade BPA", "12": "12 - Águas de Lindóia"}
    return mapa.get(u_str, "Excluir")

def padronizar_bacteria(nome):
    if pd.isna(nome) or nome == "N/A": return "N/A"
    n = str(nome).strip().lower()
    if "coli" in n or "escherichia" in n: return "Escherichia coli"
    if "proteus" in n: return "Proteus sp."
    if "enterobact" in n: return "Enterobacter sp."
    if "pseudomon" in n: return "Pseudomonas sp."
    if "klebsiella" in n: return "Klebsiella sp."
    if "staphylococc" in n: return "Staphylococcus sp."
    if "streptococc" in n: return "Streptococcus sp."
    if "enterococc" in n: return "Enterococcus sp."
    return str(nome).strip().title()

def padronizar_material(material):
    if pd.isna(material): return "Desconhecido"
    return str(material).strip().rstrip('.').strip()

conn = st.connection("gsheets", type=GSheetsConnection)
COLUNAS_DB = ["Data", "Código_Paciente", "Material_Exame", "Resultado", "Bactéria", "Indicados (S)", "Resistentes (R)", "Unidade", "Período_Arquivo"]

def carregar_dados_salvos():
    try:
        df = conn.read(worksheet="Página1", ttl=0).dropna(how="all")
        if df.empty: return pd.DataFrame(columns=COLUNAS_DB)
        df['Bactéria'] = df['Bactéria'].apply(padronizar_bacteria)
        df['Unidade'] = df['Unidade'].apply(padronizar_unidade)
        df['Material_Exame'] = df['Material_Exame'].apply(padronizar_material)
        return df[df['Unidade'] != 'Excluir']
    except: return pd.DataFrame(columns=COLUNAS_DB)

def salvar_dados(df_final): conn.update(worksheet="Página1", data=df_final)

def carregar_usuarios():
    try:
        df_users = conn.read(worksheet="Usuarios", ttl=0).dropna(how="all")
        if df_users.empty: return pd.DataFrame(columns=["Usuario", "Senha", "Nivel_Acesso", "Unidades_Permitidas"])
        if "Nivel_Acesso" not in df_users.columns: df_users["Nivel_Acesso"] = "Administrador"
        if "Unidades_Permitidas" not in df_users.columns: df_users["Unidades_Permitidas"] = "Todas"
        df_users['Usuario'] = df_users['Usuario'].astype(str).str.strip()
        df_users['Senha'] = df_users['Senha'].astype(str).str.replace(r'\.0$', '', regex=True).str.lstrip("'").str.strip()
        return df_users
    except: return pd.DataFrame(columns=["Usuario", "Senha", "Nivel_Acesso", "Unidades_Permitidas"])

def salvar_novo_usuario(df_users): conn.update(worksheet="Usuarios", data=df_users)

# ==========================================
# 4. LOGIN (CSS DE GUERRA)
# ==========================================
if 'logado' not in st.session_state: st.session_state['logado'] = False
if not st.session_state['logado']:
    st.markdown("""
    <style>
    /* O Fundo definitivo (Laboratório) */
    .stApp {
        background: linear-gradient(rgba(0, 15, 60, 0.7), rgba(0, 15, 60, 0.7)), url("https://images.unsplash.com/photo-1579684385127-1ecd15d5681d?q=80&w=2000&auto=format&fit=crop") !important;
        background-size: cover !important;
        background-position: center !important;
    }
    
    /* Login Card */
    [data-testid="stForm"] {
        background-color: #FFFFFF !important;
        border-radius: 15px !important;
        padding: 40px !important;
        box-shadow: 0px 20px 50px rgba(0,0,0,0.5) !important;
    }
    
    /* Botão Azul São Francisco (Agressivo) */
    div.stButton > button {
        background-color: #002395 !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
    }
    /* Estiliza especificamente o botão do form de login para garantir o azul */
    [data-testid="stForm"] button[kind="primaryFormSubmit"] {
        background-color: #002395 !important;
        color: #FFFFFF !important;
    }
    </style>
    """, unsafe_allow_html=True)

    col_vazia_esq, col_login, col_vazia_dir = st.columns([1, 1.2, 1])
    with col_login:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.form(key="login_form"):
            try: st.image("logo.png", use_container_width=True)
            except: st.markdown("<h2 style='text-align: center; color:#002395;'>SÃO FRANCISCO</h2>", unsafe_allow_html=True)
            
            usuario_input = st.text_input("Nome de Usuário:")
            senha_input = st.text_input("Senha de Acesso:", type="password")
            st.checkbox("Lembrar senha neste computador")
            
            submit_button = st.form_submit_button("Fazer Login 🚀", use_container_width=True)
            
            if submit_button:
                df_usuarios = carregar_usuarios()
                usuario_encontrado = df_usuarios[df_usuarios['Usuario'] == usuario_input]
                if not usuario_encontrado.empty and str(usuario_encontrado.iloc[0]['Senha']) == senha_input:
                    st.session_state['logado'] = True
                    st.session_state['usuario'] = usuario_input
                    st.session_state['nivel_acesso'] = str(usuario_encontrado.iloc[0]['Nivel_Acesso'])
                    st.session_state['unidades_permitidas'] = str(usuario_encontrado.iloc[0]['Unidades_Permitidas'])
                    st.rerun()
                else: st.error("❌ Usuário ou senha incorretos.")
    st.stop()

# ==========================================
# DASHBOARD (PÓS LOGIN)
# ==========================================
st.markdown("""<style>.stApp { background: #F4F6F9 !important; }</style>""", unsafe_allow_html=True)
# ... [Restante do seu código permanece igual aqui] ...
