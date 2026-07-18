import streamlit as st
import pandas as pd
import plotly.express as px
import re
import PyPDF2
from streamlit_gsheets import GSheetsConnection
import time
import base64
import os
import random
import uuid
from datetime import datetime, timedelta

# ==========================================
# 1. PAINEL DE CONTROLE DE ARQUIVOS
# ==========================================
ARQUIVO_VIDEO_FUNDO = "video.mp4"
ARQUIVO_LOGO_LOGIN = "logo.png"
ARQUIVO_ASSINATURA = "Gemini_Generated_Image_s8ldfcs8ldfcs8ld-removebg-preview.png" 
ARQUIVO_GIF_CARREGAMENTO = "logocarregador.gif"
ARQUIVO_LOGO_PROGRAMA = "logoprograma.png" 

# ==========================================
# CONFIGURAÇÕES INICIAIS DE TEMA
# ==========================================
st.set_page_config(page_title="S.I.B.C. - Sistema Integrado", layout="wide", initial_sidebar_state="expanded")

COR_NEON = '#00eeff'
COR_POSITIVO = '#f43f5e'
COR_NEGATIVO = '#3b82f6'
PALETA_CORES = ['#00eeff', '#3b82f6', '#002395', '#8b5cf6', '#6366f1', '#a855f7']
UNIDADES_OFICIAIS = ["1 - Serra Negra", "3 - AME", "4 - Amparo Unidade 4", "5 - Monte Alegre", "6 - Lindóia", "9 - Cenam", "10 - Amparo Unidade BPA", "12 - Águas de Lindóia", "Sede / Sem Unidade"]

def get_base64_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f: return base64.b64encode(f.read()).decode()
    return None

# ==========================================
# OCULTAR ELEMENTOS EM INGLÊS DO STREAMLIT
# ==========================================
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden !important;}
    div[data-testid="InputInstructions"] {display: none !important;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# TELA DE CARREGAMENTO (GIF)
# ==========================================
gif_b64 = get_base64_file(ARQUIVO_GIF_CARREGAMENTO)
if gif_b64:
    loader_id = str(uuid.uuid4())[:8] 
    st.markdown(f"""
    <style>
    @keyframes fadeOutLoader_{loader_id} {{ 0% {{ opacity: 1; backdrop-filter: blur(10px); }} 70% {{ opacity: 1; backdrop-filter: blur(10px); }} 100% {{ opacity: 0; visibility: hidden; backdrop-filter: blur(0px); display: none; }} }}
    .splash-screen-{loader_id} {{ position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: rgba(5, 10, 20, 0.85); z-index: 9999999; display: flex; flex-direction: column; justify-content: center; align-items: center; animation: fadeOutLoader_{loader_id} 1.2s forwards ease-out; pointer-events: none; }}
    .splash-screen-{loader_id} img {{ width: 150px; filter: drop-shadow(0px 0px 20px rgba(0,238,255,0.7)); }}
    .splash-screen-{loader_id} h2 {{ color: #00eeff; font-family: 'Arial', sans-serif; margin-top: 20px; text-shadow: 0px 0px 15px rgba(0,238,255,0.9); letter-spacing: 5px; font-size: 20px; font-weight: 900; }}
    </style>
    <div class="splash-screen-{loader_id}"><img src="data:image/gif;base64,{gif_b64}"><h2>PROCESSANDO...</h2></div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. MOTOR DE BANCO DE DADOS (CORREÇÃO DE NOMES)
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
    # Remove tags como [URAB], [HEMO], [SWAB]
    mat_limpo = re.sub(r'\[.*?\]\s*', '', str(material))
    if not mat_limpo.strip(): return "Desconhecido"
    return mat_limpo.strip().rstrip('.').strip()

conn = st.connection("gsheets", type=GSheetsConnection)
COLUNAS_DB = ["Data", "Código_Paciente", "Idade", "Sexo", "Material_Exame", "Resultado", "Bactéria", "Indicados (S)", "Resistentes (R)", "Unidade", "Período_Arquivo"]

def carregar_dados_salvos():
    try:
        df = conn.read(worksheet="Página1", ttl=0).dropna(how="all")
        if df.empty: return pd.DataFrame(columns=COLUNAS_DB)
        if 'Idade' not in df.columns: df['Idade'] = "Não Informada"
        if 'Sexo' not in df.columns: df['Sexo'] = "Não Informado"
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
        df_users['Usuario'] = df_users['Usuario'].astype(str).str.strip()
        df_users['Senha'] = df_users['Senha'].astype(str).str.replace(r'\.0$', '', regex=True).str.lstrip("'").str.strip()
        return df_users
    except: return pd.DataFrame(columns=["Usuario", "Senha", "Nivel_Acesso", "Unidades_Permitidas"])

def salvar_novo_usuario(df_users): conn.update(worksheet="Usuarios", data=df_users)

def extrair_dados_pdf(texto_bruto):
    dados = []
    periodo_doc = "Período Indefinido"
    match_per = re.search(r'Per[íi]odo de (\d{2}/\d{2}/\d{4}) [àa] (\d{2}/\d{2}/\d{4})', texto_bruto, re.IGNORECASE)
    if match_per: periodo_doc = f"{match_per.group(1)} a {match_per.group(2)}"

    blocos = re.split(r'(?=\b\d{2}/\d{2}/\d{4}\s+\d{4,}\b)', texto_bruto)
    for bloco in blocos:
        if not bloco.strip(): continue
        match_header = re.search(r'(\d{2}/\d{2}/\d{4})\s+(\d{4,})', bloco)
        if not match_header: continue
        data_pac, cod_pac = match_header.group(1), match_header.group(2)
        unidade_pac = "Sede / Sem Unidade"
        match_unidade = re.search(r'Unidade Sigla:\s*(\d+)', bloco)
        if match_unidade: unidade_pac = padronizar_unidade(match_unidade.group(1))
        if unidade_pac == "Excluir": continue 
            
        sub_blocos = re.split(r'(?=\[\s*[A-Z]+\s*\])', bloco)
        for sub in sub_blocos:
            linha = {"Data": data_pac, "Código_Paciente": cod_pac, "Idade": "Não Informada", "Sexo": "Não Informado", "Material_Exame": "Desconhecido", "Resultado": "Negativo", "Bactéria": "N/A", "Indicados (S)": "", "Resistentes (R)": "", "Unidade": unidade_pac, "Período_Arquivo": periodo_doc}
            
            match_mat = re.search(r'(?:MAT(?:ERIAL)?):\s*(.*?)(?=RES|1:|\.1:|[A-Z]{3}2?:|\n|$)', sub)
            if match_mat: 
                linha["Material_Exame"] = padronizar_material(re.sub(r'[\.\d]+$', '', match_mat.group(1)).strip())
            
            if "Não houve desenvolvimento" in sub or "Não houve crescimento" in sub: linha["Resultado"] = "Negativo"
            else:
                linha["Resultado"] = "Positivo"
                regex_bac = r'(?i:identificado|MIC|\b1|\.1|aer[oó]bia[^:]*|anaer[oó]bia[^:]*)\s*:\s*([A-Z][a-z]{2,}(?:\s+[a-z]{2,})?(?:\s+sp\.?)?)'
                match_bac = re.search(regex_bac, sub)
                if match_bac:
                    bac_str = match_bac.group(1).replace(":", "").strip()
                    if "Não houve" not in bac_str and "Aplic" not in bac_str: linha["Bactéria"] = padronizar_bacteria(bac_str)
                else:
                    for bac_name in ["Escherichia", "Proteus", "Enterobacter", "Pseudomonas", "Klebsiella", "Staphylococcus", "Streptococcus", "Enterococcus"]:
                        if bac_name.lower() in sub.lower():
                            linha["Bactéria"] = padronizar_bacteria(bac_name)
                            break
                            
                sensiveis, resistentes = [], []
                matches_atb = re.findall(r'([A-Z]{2,5})\d*[\s:=]+([SR])\b', sub)
                for atb, status in matches_atb:
                    if status == 'S': sensiveis.append(atb)
                    elif status == 'R': resistentes.append(atb)
                    
                linha["Indicados (S)"] = ", ".join(sorted(list(set(sensiveis))))
                linha["Resistentes (R)"] = ", ".join(sorted(list(set(resistentes))))
            dados.append(linha)
    return pd.DataFrame(dados)

def gerar_dados_teste_premium():
    exames_mock = ["Urina Jato Médio", "Sangue Venoso", "Secreção", "Líquido Cefalorraquidiano"]
    bacterias_mock = ["Escherichia coli", "Staphylococcus aureus", "Klebsiella pneumoniae", "Pseudomonas aeruginosa", "Proteus mirabilis"]
    sexos_mock = ["Feminino", "Masculino"]
    antibioticos = ["Amicacina", "Cefepime", "Meropenem", "Ampicilina", "Ciprofloxacino", "Levofloxacino"]
    novos_dados = []
    data_base = datetime.today()
    for i in range(500): 
        is_positivo = random.random() > 0.4 
        res = "Positivo" if is_positivo else "Negativo"
        bac = random.choice(bacterias_mock) if is_positivo else "N/A"
        dias_atras = random.randint(0, 180)
        data_mock = (data_base - timedelta(days=dias_atras)).strftime("%d/%m/%Y")
        sens = ", ".join(random.sample(antibioticos, k=random.randint(2, 4))) if is_positivo else ""
        rest = ", ".join(random.sample(antibioticos, k=random.randint(1, 3))) if is_positivo else ""
        novos_dados.append({
            "Data": data_mock, "Código_Paciente": f"DEMO-{random.randint(100000, 999999)}", 
            "Idade": int(random.gauss(45, 15)), "Sexo": random.choice(sexos_mock), 
            "Material_Exame": random.choice(exames_mock), "Resultado": res, "Bactéria": bac, 
            "Indicados (S)": sens, "Resistentes (R)": rest, "Unidade": random.choice(UNIDADES_OFICIAIS[:-1]),
            "Período_Arquivo": "Gerado Demo"
        })
    return pd.DataFrame(novos_dados)

if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'usuario' not in st.session_state: st.session_state['usuario'] = ""
if 'nivel_acesso' not in st.session_state: st.session_state['nivel_acesso'] = "Visualizador"
if 'unidades_permitidas' not in st.session_state: st.session_state['unidades_permitidas'] = "Todas"

# ==========================================
# 5. TELA DE LOGIN (COMPACTA, SEM ROLAGEM, SEM INGLÊS)
# ==========================================
if not st.session_state['logado']:
    
    video_fundo_b64 = get_base64_file(ARQUIVO_VIDEO_FUNDO)
    if video_fundo_b64:
        st.markdown(f'''<video autoplay loop muted playsinline style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -999; object-fit: cover; filter: brightness(0.35) contrast(1.1);"><source src="data:video/mp4;base64,{video_fundo_b64}" type="video/mp4"></video>''', unsafe_allow_html=True)
    else:
        st.markdown('<style>.stApp { background-color: #040d21 !important; }</style>', unsafe_allow_html=True)

    st.markdown("""
    <style>
    @keyframes floating { 0% { transform: translateY(0px); } 50% { transform: translateY(-8px); } 100% { transform: translateY(0px); } }
    .stApp { background: transparent !important; }
    
    .login-wrapper {
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        height: 100vh; width: 100%; overflow: hidden; /* Corta a rolagem */
    }
    
    [data-testid="stForm"] {
        width: 380px !important; height: 380px !important; border-radius: 50% !important; 
        background: radial-gradient(circle at 40% 40%, rgba(200, 180, 50, 0.15) 0%, rgba(0, 30, 40, 0.4) 60%, rgba(0, 0, 0, 0.8) 100%) !important;
        backdrop-filter: blur(15px) !important; -webkit-backdrop-filter: blur(15px) !important;
        border: 6px solid rgba(255, 255, 255, 0.1) !important;
        border-top: 6px solid rgba(255, 255, 255, 0.3) !important;
        border-bottom: 6px solid rgba(0, 0, 0, 0.8) !important;
        box-shadow: inset 0px 0px 40px rgba(0, 238, 255, 0.1), 0px 30px 50px rgba(0,0,0,0.8), 0px 0px 30px rgba(0, 238, 255, 0.15) !important;
        display: flex !important; flex-direction: column !important; justify-content: center !important; align-items: center !important;
        margin: 15px auto !important; z-index: 10;
        animation: floating 6s ease-in-out infinite;
    }
    
    [data-testid="stForm"] > div { width: 100% !important; max-width: 250px !important; margin: 0 auto !important; }
    [data-testid="stForm"] label, [data-testid="stForm"] p { color: #f8fafc !important; font-weight: 700; text-shadow: 0px 2px 4px rgba(0,0,0,1) !important; font-size: 13px; text-align: center; width:100%;}
    
    input[type="text"], input[type="password"] {
        background-color: rgba(0, 10, 20, 0.5) !important; color: #00eeff !important; -webkit-text-fill-color: #00eeff !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important; border-bottom: 2px solid #00eeff !important; border-radius: 5px !important; padding: 10px !important;
        font-family: monospace !important; text-align: center; letter-spacing: 1px; width: 100% !important; transition: 0.3s; margin-bottom: 5px;
    }
    input[type="text"]:focus, input[type="password"]:focus { background-color: rgba(0, 0, 0, 0.8) !important; box-shadow: 0 5px 15px rgba(0, 238, 255, 0.3) !important;}
    
    [data-testid="stFormSubmitButton"] { width: 100% !important; margin-top: 15px !important; }
    [data-testid="stFormSubmitButton"] button {
        background: #0f172a !important; color: #00eeff !important;
        border: 1px solid rgba(0, 238, 255, 0.5) !important; border-radius: 5px !important; padding: 10px 0 !important;
        font-weight: 800 !important; font-size: 13px !important; letter-spacing: 1px;
        width: 100% !important; transition: 0.3s; box-shadow: 0px 5px 15px rgba(0,0,0,0.5) !important; text-transform: uppercase;
    }
    [data-testid="stFormSubmitButton"] button:hover { background: #00eeff !important; color: #0f172a !important; box-shadow: 0px 5px 20px rgba(0, 238, 255, 0.6) !important; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)

    logo_b64 = get_base64_file(ARQUIVO_LOGO_LOGIN)
    if logo_b64:
        st.markdown(f'''<div style="text-align: center;"><img src="data:image/png;base64,{logo_b64}" style="height: 100px; filter: drop-shadow(0px 5px 15px rgba(255,255,255,0.4));"></div>''', unsafe_allow_html=True)

    with st.form(key="login_form", clear_on_submit=False):
        st.markdown("<h2 style='text-align: center; color:#00eeff !important; font-family: monospace; font-weight: 900; margin-bottom: 20px; font-size: 15px; text-shadow: 0px 0px 10px rgba(0,0,0,1);'>🧫 ACESSO RESTRITO 🦠</h2>", unsafe_allow_html=True)
        usuario_input = st.text_input("🔬 Identificação:")
        senha_input = st.text_input("🧬 Sequência Genética:", type="password")
        submit_button = st.form_submit_button("INICIAR PROTOCOLO")
        
        if submit_button:
            df_usuarios = carregar_usuarios()
            usuario_encontrado = df_usuarios[df_usuarios['Usuario'] == usuario_input]
            if not usuario_encontrado.empty and str(usuario_encontrado.iloc[0]['Senha']) == senha_input:
                st.session_state['logado'] = True
                st.session_state['usuario'] = usuario_input
                st.session_state['nivel_acesso'] = str(usuario_encontrado.iloc[0]['Nivel_Acesso'])
                st.session_state['unidades_permitidas'] = str(usuario_encontrado.iloc[0]['Unidades_Permitidas'])
                st.rerun()
            else:
                st.error("❌ Acesso Negado.")

    assinatura_b64 = get_base64_file(ARQUIVO_ASSINATURA)
    if assinatura_b64:
        st.markdown(f'''<div style="text-align: center; margin-top: 10px;"><img src="data:image/png;base64,{assinatura_b64}" style="height: 50px; filter: drop-shadow(0px 2px 5px rgba(0,0,0,0.8)); opacity: 0.9;"></div>''', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==========================================
# 6. SISTEMA INTERNO (TUDO EM PORTUGUÊS E PDF CORRIGIDO)
# ==========================================
else:

    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Arial:wght@800&display=swap');
        
        .stApp {{ background-color: #0b1120 !important; color: #f8fafc !important; }}
        section[data-testid="stSidebar"] {{ background-color: #0f172a !important; border-right: 1px solid #1e293b !important; }}
        section[data-testid="stSidebar"] * {{ color: #e2e8f0 !important; }}
        
        div[data-testid="metric-container"] {{ background: linear-gradient(145deg, #111827, #1e293b) !important; border-left: 3px solid #00eeff !important; padding: 20px !important; border-radius: 8px !important; box-shadow: 0 5px 15px rgba(0,0,0,0.5) !important; }}
        div[data-testid="metric-container"] label {{ color: #94a3b8 !important; font-size: 14px !important;}}
        div[data-testid="metric-container"] div {{ color: #00eeff !important; text-shadow: 0px 0px 10px rgba(0,238,255,0.3) !important;}}
        
        /* O MODO DE IMPRESSÃO - DESTRÓI BARRAS DE ROLAGEM E EXPANDÉ TUDO */
        @media print {{
            @page {{ size: A4 landscape !important; margin: 10mm !important; }}
            html, body, .stApp, .block-container, div[data-testid="stAppViewContainer"], .main {{ height: auto !important; max-height: none !important; overflow: visible !important; position: static !important; background: white !important; background-color: white !important; color: black !important; padding: 0 !important; margin: 0 !important; }}
            h1, h2, h3, h4, p, label, div, span {{ color: black !important; text-shadow: none !important; box-shadow: none !important; }}
            section[data-testid="stSidebar"], header, button, .stButton, input, select, .stMultiSelect, div[data-testid="stFileUploader"], [data-testid="stToolbar"] {{ display: none !important; }}
            div[data-testid="column"] {{ width: 100% !important; max-width: 100% !important; flex: 0 0 100% !important; display: block !important; margin-bottom: 20px !important; page-break-inside: avoid !important; }}
            div[data-testid="stVerticalBlock"] {{ display: block !important; width: 100% !important; flex: none !important; height: auto !important; overflow: visible !important; }}
            .stDataFrame, [data-testid="stDataFrameContainer"], [data-testid="stDataFrameContainer"] > div, .stDataFrame > div {{ height: auto !important; max-height: none !important; overflow: visible !important; width: 100% !important; display: table !important; position: static !important; }}
            table {{ width: 100% !important; border-collapse: collapse !important; table-layout: auto !important; }}
            th, td {{ border: 1px solid #000 !important; padding: 6px !important; color: black !important; background: white !important; white-space: normal !important; word-wrap: break-word !important; }}
            .js-plotly-plot, .plotly {{ width: 100% !important; max-width: 100% !important; page-break-inside: avoid !important; }}
            div[data-testid="metric-container"] {{ background: white !important; border: 1px solid #000 !important; margin-bottom: 15px !important; border-left: 5px solid #000 !important; padding: 10px !important; page-break-inside: avoid !important;}}
            div[data-testid="metric-container"] div {{ color: black !important; }}
        }}
        </style>
    """, unsafe_allow_html=True)

    st.components.v1.html("""
        <script>function doPrint() { window.parent.print(); }</script>
        <button onclick="doPrint()" style="background: linear-gradient(90deg, #002395, #3b82f6); color:white; padding:12px 20px; border:none; border-radius:5px; cursor:pointer; font-weight:bold; width:100%; text-transform: uppercase; letter-spacing: 1px; box-shadow: 0px 4px 10px rgba(0,0,0,0.5);">🖨️ Exportar Documento Oficial</button>
    """, height=50)

    df_todos_dados = carregar_dados_salvos()
    df_reais = pd.DataFrame()
    df_mock = pd.DataFrame()

    if not df_todos_dados.empty:
        df_todos_dados['Data_Obj'] = pd.to_datetime(df_todos_dados['Data'], format="%d/%m/%Y", errors='coerce')
        df_todos_dados['Mês/Ano'] = df_todos_dados['Data_Obj'].dt.strftime('%m/%Y').fillna('Desconhecido')
        unid_perm = st.session_state.get('unidades_permitidas', 'Todas')
        if unid_perm != "Todas" and st.session_state['usuario'] != "vhpezzeti":
            df_todos_dados = df_todos_dados[df_todos_dados['Unidade'].isin([u.strip() for u in unid_perm.split(",")])]
        df_reais = df_todos_dados[df_todos_dados['Período_Arquivo'] != 'Gerado Demo']
        df_mock = df_todos_dados[df_todos_dados['Período_Arquivo'] == 'Gerado Demo']

    # ==========================================
    # LOGO DO MENU LATERAL (AGORA FICA VISÍVEL NO FUNDO ESCURO)
    # ==========================================
    logo_prog_b64 = get_base64_file(ARQUIVO_LOGO_PROGRAMA)
    if logo_prog_b64:
        st.sidebar.markdown(f'''
            <div style="display: flex; justify-content: center; margin-bottom: 25px;">
                <div style="background-color: rgba(255, 255, 255, 0.15); padding: 5px; border-radius: 50%; box-shadow: 0px 0px 20px rgba(0, 238, 255, 0.4);">
                    <img src="data:image/png;base64,{logo_prog_b64}" style="width: 120px; height: 120px; border-radius: 50%; object-fit: cover;">
                </div>
            </div>
        ''', unsafe_allow_html=True)
    
    st.sidebar.markdown(f"👤 **{st.session_state['usuario'].upper()}**")
    st.sidebar.markdown(f"🛡️ **Nível:** <span style='color:#00eeff;'>{st.session_state.get('nivel_acesso', '')}</span>", unsafe_allow_html=True)
    st.sidebar.markdown("---")

    opcoes_menu = ["📊 Painel Principal", "📈 Análise e Tendências"]
    if st.session_state.get('nivel_acesso') in ["Operador", "Administrador"] or st.session_state['usuario'] == "vhpezzeti":
        opcoes_menu.append("📂 Carregar Laudos")
    if st.session_state.get('nivel_acesso') == "Administrador" or st.session_state['usuario'] == "vhpezzeti":
        opcoes_menu.append("⚙️ Painel Administrativo")

    menu = st.sidebar.radio("Navegação do Sistema", opcoes_menu)
    
    # ========================================================
    # FILTROS GLOBAIS (SÓ APARECEM SE TIVER NOS PAINÉIS DE DADOS)
    # ========================================================
    df_f = pd.DataFrame()
    df_base_ativa = df_reais if not df_reais.empty else df_mock

    if menu in ["📊 Painel Principal", "📈 Análise e Tendências"] and not df_base_ativa.empty:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🎛️ Filtros de Análise")
        
        meses_disp = sorted(list(df_base_ativa[df_base_ativa['Mês/Ano'] != 'Desconhecido']['Mês/Ano'].unique()))
        unid_disp = sorted(list(df_base_ativa['Unidade'].unique()))
        exame_disp = sorted(list(df_base_ativa['Material_Exame'].unique()))
        
        meses_sel = st.sidebar.multiselect("📅 Selecione o Mês/Ano", meses_disp, default=meses_disp)
        unid_sel = st.sidebar.multiselect("🏢 Selecione a Unidade", unid_disp, default=unid_disp)
        exame_sel = st.sidebar.multiselect("🧪 Selecione o Material", exame_disp, default=exame_disp)
        
        df_f = df_base_ativa[df_base_ativa['Mês/Ano'].isin(meses_sel) & df_base_ativa['Unidade'].isin(unid_sel) & df_base_ativa['Material_Exame'].isin(exame_sel)]

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Encerrar Sessão", use_container_width=True):
        st.session_state['logado'] = False
        st.rerun()

    # ========================================================
    # TELA 1: PAINEL PRINCIPAL
    # ========================================================
    if menu == "📊 Painel Principal":
        st.title("📊 Monitoramento Clínico Operacional")
        if df_base_ativa.empty: 
            st.info("Nenhum Laudo Oficial processado. Vá em 'Carregar Laudos' para iniciar.")
        elif df_f.empty: 
            st.warning("Nenhum dado corresponde aos filtros selecionados na barra lateral.")
        else:
            t_total = len(df_f)
            t_pos = len(df_f[df_f['Resultado'] == 'Positivo'])
            t_neg = len(df_f[df_f['Resultado'] == 'Negativo'])
            pct_pos = (t_pos / t_total * 100) if t_total > 0 else 0
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Volume de Laudos", t_total)
            m2.metric("Laudos Positivos", t_pos, delta=f"{pct_pos:.1f}% Positividade", delta_color="inverse")
            m3.metric("Controle Negativo", t_neg, delta=f"{100-pct_pos:.1f}%", delta_color="normal")
            m4.metric("Média / Seleção", round(t_total / max(len(meses_sel) if 'meses_sel' in locals() else 1, 1), 1))
            
            df_pos = df_f[df_f['Resultado'] == 'Positivo']
            if not df_pos.empty:
                st.markdown("---")
                g1, g2 = st.columns(2)
                with g1:
                    st.markdown("#### ⚖️ Proporção Diagnóstica")
                    fig1 = px.pie(df_f, names='Resultado', hole=0.5, color='Resultado', color_discrete_map={'Positivo': COR_POSITIVO, 'Negativo': COR_NEGATIVO}, template="plotly_dark")
                    fig1.update_traces(textposition='inside', textinfo='percent+label')
                    fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig1, use_container_width=True)
                with g2:
                    st.markdown("#### 🧫 Contagem de Patógenos Identificados")
                    df_bact = df_pos['Bactéria'].value_counts().reset_index()
                    fig2 = px.bar(df_bact, y='Bactéria', x='count', text='count', orientation='h', template="plotly_dark", color='count', color_continuous_scale="Viridis")
                    fig2.update_traces(textposition='outside')
                    fig2.update_layout(yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis_title="Quantidade")
                    st.plotly_chart(fig2, use_container_width=True)

                st.markdown("#### 📋 Base de Dados - Perfil Crítico de Pacientes")
                st.dataframe(df_pos[['Data', 'Código_Paciente', 'Unidade', 'Material_Exame', 'Bactéria', 'Indicados (S)', 'Resistentes (R)']], use_container_width=True, hide_index=True)

    # ========================================================
    # TELA 2: ANÁLISE E TENDÊNCIAS
    # ========================================================
    elif menu == "📈 Análise e Tendências":
        st.title("📈 Análise e Tendências Hospitalares")
        
        if df_base_ativa.empty:
            st.info("O sistema não possui dados para gerar a análise.")
        elif df_f.empty:
            st.warning("Nenhum dado corresponde aos filtros selecionados na barra lateral.")
        else:
            df_pos_comp = df_f[df_f['Resultado'] == 'Positivo'].copy()
            if not df_pos_comp.empty:
                b_top = df_pos_comp['Bactéria'].value_counts().idxmax()
                exame_top = df_pos_comp['Material_Exame'].value_counts().idxmax()
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Bactéria mais Frequente", b_top)
                c2.metric("Material mais Crítico", exame_top)
                c3.metric("Total de Infecções", f"{len(df_pos_comp):,}".replace(",", "."))
                pct_geral = (len(df_pos_comp) / len(df_f)) * 100
                c4.metric("Taxa Relativa de Infecção", f"{pct_geral:.1f}%")
                
                st.markdown("---")
                
                st.markdown("### 📉 Curva de Crescimento e Localização")
                col_g1, col_g2 = st.columns([1.5, 1])
                
                with col_g1:
                    st.markdown("**Evolução de Casos Positivos no Tempo**")
                    df_pos_comp['Data_Obj'] = pd.to_datetime(df_pos_comp['Data'], format="%d/%m/%Y", errors='coerce')
                    linha_tempo = df_pos_comp.dropna(subset=['Data_Obj']).groupby(df_pos_comp['Data_Obj'].dt.to_period("W")).size().reset_index(name='Casos')
                    linha_tempo['Data_Obj'] = linha_tempo['Data_Obj'].dt.to_timestamp()
                    if not linha_tempo.empty:
                        fig_linha = px.line(linha_tempo, x='Data_Obj', y='Casos', markers=True, template="plotly_dark")
                        fig_linha.update_traces(line=dict(color=COR_NEON, width=3), marker=dict(size=8, color=COR_NEON))
                        fig_linha.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis_title="Período", yaxis_title="Quantidade de Casos")
                        st.plotly_chart(fig_linha, use_container_width=True)
                        
                with col_g2:
                    st.markdown("**Mapa de Concentração (Por Unidade)**")
                    top_unid = df_pos_comp['Unidade'].value_counts().reset_index()
                    fig_unid = px.bar(top_unid, x='count', y='Unidade', orientation='h', text='count', template="plotly_dark", color='count', color_continuous_scale="Reds")
                    fig_unid.update_traces(textposition='inside')
                    fig_unid.update_layout(yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis_title="")
                    st.plotly_chart(fig_unid, use_container_width=True)

                st.markdown("---")
                st.markdown("### 👥 Estudo Demográfico dos Pacientes")
                
                df_demo = df_pos_comp[df_pos_comp['Idade'] != 'Não Informada'].copy()
                
                if df_demo.empty:
                    st.info("⚠️ O sistema não encontrou a 'Idade' ou o 'Sexo' nos laudos carregados para montar o estudo demográfico.")
                else:
                    df_demo['Idade'] = pd.to_numeric(df_demo['Idade'], errors='coerce')
                    d1, d2, d3 = st.columns([1, 1.5, 1])
                    
                    with d1:
                        st.markdown("**Separação por Sexo**")
                        fig_sexo = px.pie(df_demo, names='Sexo', hole=0.6, color_discrete_sequence=['#f43f5e', '#38bdf8'], template="plotly_dark")
                        fig_sexo.update_traces(textposition='inside', textinfo='percent+label')
                        fig_sexo.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
                        st.plotly_chart(fig_sexo, use_container_width=True)
                        
                    with d2:
                        st.markdown("**Faixa Etária de Risco**")
                        fig_idade = px.histogram(df_demo, x='Idade', nbins=15, color_discrete_sequence=['#8b5cf6'], text_auto=True, template="plotly_dark")
                        fig_idade.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis_title="Idade", yaxis_title="Quantidade")
                        st.plotly_chart(fig_idade, use_container_width=True)
                        
                    with d3:
                        st.markdown("**Estatísticas de Idade**")
                        media_idade = df_demo['Idade'].mean()
                        min_idade = df_demo['Idade'].min()
                        max_idade = df_demo['Idade'].max()
                        
                        st.markdown(f"""
                        <div style='background: #1e293b; padding: 20px; border-radius: 10px; border-left: 5px solid #8b5cf6;'>
                            <p style='color:#cbd5e1; margin-bottom:5px;'>Média de Idade</p>
                            <h2 style='color:#00eeff; margin-top:0;'>{media_idade:.0f} anos</h2>
                            <hr style='border-color: #334155;'>
                            <p style='color:#cbd5e1; margin-bottom:5px;'>Paciente mais Novo</p>
                            <h4 style='color:white; margin-top:0;'>{min_idade:.0f} anos</h4>
                            <p style='color:#cbd5e1; margin-bottom:5px;'>Paciente mais Velho</p>
                            <h4 style='color:white; margin-top:0;'>{max_idade:.0f} anos</h4>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.warning("Variáveis insuficientes para construção da análise.")

    # ========================================================
    # TELA 3: CARREGAR LAUDOS
    # ========================================================
    elif menu == "📂 Carregar Laudos":
        st.title("📂 Processamento de Documentos")
        st.info("Selecione os arquivos PDF. O sistema irá extrair pacientes, laudos positivos, negativos e quadro de antibióticos automaticamente.")
        
        arq = st.file_uploader("Arraste os laudos laboratoriais aqui", type=['pdf', 'txt'])
        if arq and st.button("Salvar no Banco de Dados", use_container_width=True):
            texto_bruto = ""
            with st.spinner("Processando o arquivo..."):
                if arq.name.endswith('.pdf'):
                    try:
                        leitor = PyPDF2.PdfReader(arq)
                        for p in leitor.pages: texto_bruto += p.extract_text() + "\n"
                    except Exception as e: st.error(f"Erro na leitura do PDF: {e}")
                else: texto_bruto = arq.read().decode("utf-8")
                
                df_novo = extrair_dados_pdf(texto_bruto)
                if not df_novo.empty:
                    df_atual = conn.read(worksheet="Página1", ttl=0).dropna(how="all")
                    df_combinado = pd.concat([df_atual, df_novo]).drop_duplicates(subset=['Data', 'Código_Paciente', 'Material_Exame', 'Unidade'])
                    salvar_dados(df_combinado)
                    st.success(f"✅ {len(df_novo)} exames foram extraídos com sucesso e já estão no sistema!")
                    st.balloons()
                    st.dataframe(df_novo, use_container_width=True)
                else: st.error("❌ Não foi possível encontrar nenhum dado compatível neste documento.")

    # ========================================================
    # TELA 4: PAINEL ADMINISTRATIVO
    # ========================================================
    elif menu == "⚙️ Painel Administrativo":
        st.title("⚙️ Gestão do Sistema")
        tab1, tab2, tab3, tab4 = st.tabs(["➕ Novo Usuário", "✏️ Editar Usuários", "📋 Ver Tabela Bruta", "🧪 Injetar Base de Teste"])
        
        df_users_adm = carregar_usuarios()
        lista_usuarios = df_users_adm['Usuario'].tolist() if not df_users_adm.empty else []

        with tab1:
            st.markdown("### Criar Acesso")
            with st.form("form_cadastro"):
                c1, c2 = st.columns(2)
                novo_usuario = c1.text_input("Usuário:")
                nova_senha = c2.text_input("Senha:", type="password")
                c3, c4 = st.columns(2)
                novo_nivel = c3.selectbox("Nível de Permissão:", ["Visualizador", "Operador", "Administrador"])
                nova_unid = c4.multiselect("Liberar acesso apenas para (Deixe vazio para todas):", UNIDADES_OFICIAIS)
                if st.form_submit_button("Criar"):
                    if novo_usuario and nova_senha:
                        if novo_usuario not in lista_usuarios:
                            str_unidades = ", ".join(nova_unid) if nova_unid else "Todas"
                            novo_registro = pd.DataFrame([{"Usuario": novo_usuario, "Senha": f"'{nova_senha}", "Nivel_Acesso": novo_nivel, "Unidades_Permitidas": str_unidades}])
                            salvar_novo_usuario(pd.concat([df_users_adm, novo_registro], ignore_index=True))
                            st.success("✅ Criado!"); time.sleep(1); st.rerun()
                        else: st.warning("Usuário já existe.")
                    else: st.warning("Preencha todos os campos.")

        with tab2:
            st.markdown("### Alterar Permissões")
            usr_editar = st.selectbox("Escolha o usuário:", [""] + lista_usuarios)
            if usr_editar:
                udata = df_users_adm[df_users_adm['Usuario'] == usr_editar].iloc[0]
                with st.form("form_edicao"):
                    n_senha = st.text_input("Nova Senha (vazio para manter a mesma):", type="password")
                    n_nivel = st.selectbox("Permissão:", ["Visualizador", "Operador", "Administrador"], index=["Visualizador", "Operador", "Administrador"].index(udata['Nivel_Acesso']))
                    if st.form_submit_button("Atualizar"):
                        idx = df_users_adm.index[df_users_adm['Usuario'] == usr_editar][0]
                        if n_senha: df_users_adm.at[idx, 'Senha'] = f"'{n_senha}"
                        df_users_adm.at[idx, 'Nivel_Acesso'] = n_nivel
                        salvar_novo_usuario(df_users_adm)
                        st.success("✅ Atualizado!"); time.sleep(1); st.rerun()
                    if st.form_submit_button("🗑️ Excluir Usuário"):
                        salvar_novo_usuario(df_users_adm[df_users_adm['Usuario'] != usr_editar])
                        st.success("✅ Excluído!"); time.sleep(1); st.rerun()
        
        with tab3: 
            st.markdown("### Tabela de Permissões")
            st.dataframe(df_users_adm, use_container_width=True)

        with tab4:
            st.markdown("### 🧪 Ferramenta de Demonstração Comercial")
            st.info("Isto criará 500 laudos fictícios em português para que os painéis fiquem cheios de informações bonitas durante uma apresentação de venda. Só clique se quiser testar os gráficos.")
            if st.button("🚀 INSERIR LAUDOS FALSOS PARA DEMONSTRAÇÃO", use_container_width=True):
                df_novos_mock = gerar_dados_teste_premium()
                df_atual = conn.read(worksheet="Página1", ttl=0).dropna(how="all")
                salvar_dados(pd.concat([df_atual, df_novos_mock]))
                st.success("✅ 500 registros falsos adicionados!")
                time.sleep(1.5); st.rerun()
