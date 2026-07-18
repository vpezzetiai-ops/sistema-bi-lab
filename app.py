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
from datetime import datetime, timedelta

# ==========================================
# 1. PAINEL DE CONTROLE DE ARQUIVOS
# ==========================================
ARQUIVO_VIDEO_FUNDO = "video.mp4"
ARQUIVO_LOGO_LOGIN = "logo.png"
ARQUIVO_ASSINATURA = "Gemini_Generated_Image_s8ldfcs8ldfcs8ld-removebg-preview.png" 
ARQUIVO_LOGO_ANIMADO_MENU = "logo_animado.mp4" # NOME ATUALIZADO CONFORME SEU PEDIDO

# ==========================================
# CONFIGURAÇÕES INICIAIS DE TEMA
# ==========================================
st.set_page_config(page_title="Sistema BI - Laboratorial", layout="wide", initial_sidebar_state="expanded")

COR_NEON = '#00eeff'
COR_AZUL_ESCURO = '#002395'
PALETA_CORES = ['#00eeff', '#3b82f6', '#002395', '#8b5cf6', '#6366f1', '#a855f7']
UNIDADES_OFICIAIS = ["1 - Serra Negra", "3 - AME", "4 - Amparo Unidade 4", "5 - Monte Alegre", "6 - Lindóia", "9 - Cenam", "10 - Amparo Unidade BPA", "12 - Águas de Lindóia", "Sede / Sem Unidade"]

# ==========================================
# FUNÇÃO AUXILIAR DE BASE64
# ==========================================
def get_base64_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f: return base64.b64encode(f.read()).decode()
    return None

# ==========================================
# TELA DE CARREGAMENTO GLOBAL (SPLASH SCREEN 3D)
# ==========================================
video_logo_b64 = get_base64_file(ARQUIVO_LOGO_ANIMADO_MENU)
if video_logo_b64:
    st.markdown(f"""
    <style>
    @keyframes fadeOutLoader {{
        0% {{ opacity: 1; visibility: visible; backdrop-filter: blur(10px); }}
        70% {{ opacity: 1; visibility: visible; backdrop-filter: blur(10px); }}
        100% {{ opacity: 0; visibility: hidden; backdrop-filter: blur(0px); }}
    }}
    .splash-screen {{
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background-color: rgba(11, 17, 32, 0.9); z-index: 999999;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        animation: fadeOutLoader 2.5s forwards; pointer-events: none;
    }}
    .splash-screen video {{
        width: 180px; mix-blend-mode: screen; filter: drop-shadow(0px 0px 25px rgba(0,238,255,0.8));
    }}
    .splash-screen h2 {{
        color: #00eeff; font-family: 'Orbitron', sans-serif; margin-top: 15px;
        text-shadow: 0px 0px 15px rgba(0,238,255,0.8); letter-spacing: 4px; font-size: 24px; font-weight: 900;
    }}
    </style>
    <div class="splash-screen">
        <video autoplay loop muted playsinline>
            <source src="data:video/mp4;base64,{video_logo_b64}" type="video/mp4">
        </video>
        <h2>PROCESSANDO...</h2>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. FUNÇÕES DE LIMPEZA E PADRONIZAÇÃO
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

# ==========================================
# 3. CONEXÃO COM GOOGLE SHEETS
# ==========================================
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

def gerar_dados_teste():
    exames_mock = ["[URAB] Urina", "[HEMO] Sangue", "[SWAB] Secreção", "[LCR] Líquido"]
    bacterias_mock = ["Escherichia coli", "Staphylococcus aureus", "Klebsiella sp.", "Pseudomonas sp.", "Proteus sp."]
    sexos_mock = ["Feminino", "Masculino"]
    novos_dados = []
    for _ in range(100): 
        res = random.choice(["Positivo", "Positivo", "Negativo"])
        bac = random.choice(bacterias_mock) if res == "Positivo" else "N/A"
        data_mock = (datetime.today() - timedelta(days=random.randint(0, 180))).strftime("%d/%m/%Y")
        novos_dados.append({
            "Data": data_mock, "Código_Paciente": str(random.randint(10000, 99999)), "Idade": random.randint(1, 90),
            "Sexo": random.choice(sexos_mock), "Material_Exame": random.choice(exames_mock), "Resultado": res,
            "Bactéria": bac, "Indicados (S)": "Amicacina, Cefepime" if res=="Positivo" else "",
            "Resistentes (R)": "Ampicilina, Penicilina" if res=="Positivo" else "", "Unidade": random.choice(UNIDADES_OFICIAIS[:-1]),
            "Período_Arquivo": "Gerado Demo"
        })
    return pd.DataFrame(novos_dados)

# ==========================================
# 4. CONTROLE DE ESTADO (SESSÃO)
# ==========================================
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'usuario' not in st.session_state: st.session_state['usuario'] = ""
if 'nivel_acesso' not in st.session_state: st.session_state['nivel_acesso'] = "Visualizador"
if 'unidades_permitidas' not in st.session_state: st.session_state['unidades_permitidas'] = "Todas"

# ==========================================
# 5. TELA DE LOGIN PREMIUM (PLACA DE PETRI)
# ==========================================
if not st.session_state['logado']:
    
    video_fundo_b64 = get_base64_file(ARQUIVO_VIDEO_FUNDO)
    
    if video_fundo_b64:
        st.markdown(f'''
        <video autoplay loop muted playsinline style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -999; object-fit: cover; filter: brightness(0.5) contrast(1.2);">
            <source src="data:video/mp4;base64,{video_fundo_b64}" type="video/mp4">
        </video>
        ''', unsafe_allow_html=True)
    else:
        st.error(f"🚨 Vídeo '{ARQUIVO_VIDEO_FUNDO}' não encontrado.")
        st.markdown('<style>.stApp { background-color: #040d21 !important; }</style>', unsafe_allow_html=True)

    # CSS DA PLACA DE PETRI E DESTAQUES
    st.markdown("""
    <style>
    @keyframes floating { 0% { transform: translateY(0px); } 50% { transform: translateY(-12px); } 100% { transform: translateY(0px); } }
    @keyframes zoomIn { 0% { opacity: 0; transform: scale(0.85); } 100% { opacity: 1; transform: scale(1); } }

    html, body, [data-testid="stAppViewContainer"], .block-container { overflow: hidden !important; padding: 0 !important; margin: 0 !important; }
    .stApp { background: transparent !important; }
    [data-testid="stHeader"] { display: none !important; }
    
    /* CAIXA DE LOGIN: EFEITO PLACA DE PETRI 3D */
    [data-testid="stForm"] {
        /* Fundo simulando meio de cultura / ágar */
        background: radial-gradient(circle at 50% 50%, rgba(0, 238, 255, 0.08) 0%, rgba(0, 35, 149, 0.2) 70%, rgba(255, 255, 255, 0.05) 100%) !important;
        backdrop-filter: blur(15px) saturate(160%) !important;
        -webkit-backdrop-filter: blur(15px) saturate(160%) !important;
        border-radius: 65px !important; /* Bordas extremamente arredondadas simulando a placa circular */
        border: 3px solid rgba(255, 255, 255, 0.25) !important; /* Borda de vidro */
        box-shadow: 
            inset 0px 0px 25px rgba(255, 255, 255, 0.4), /* Brilho interno do vidro */
            inset 0px 0px 60px rgba(0, 238, 255, 0.2), /* Líquido brilhante */
            inset -15px -15px 30px rgba(0, 0, 0, 0.6), /* Profundidade da placa */
            0px 30px 60px rgba(0,0,0,0.9), /* Sombra projetada na bancada */
            0px 0px 35px rgba(0, 238, 255, 0.35) !important; /* Brilho neon emitido pela placa */
        padding: 50px 40px 35px 40px !important;
        margin-top: 5vh !important; 
        z-index: 10; max-width: 440px; margin-left: auto; margin-right: auto;
        animation: zoomIn 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards, floating 7s ease-in-out infinite;
    }
    
    [data-testid="stForm"] p, [data-testid="stForm"] label { 
        color: #e2e8f0 !important; font-weight: 800; text-shadow: 0px 2px 5px rgba(0,0,0,1) !important; letter-spacing: 0.5px;
    }
    
    /* INPUTS SIMULANDO LÂMINAS DE MICROSCÓPIO */
    input[type="text"], input[type="password"] {
        background-color: rgba(0, 10, 20, 0.6) !important; color: #00eeff !important; -webkit-text-fill-color: #00eeff !important;
        border: 1px solid rgba(0, 238, 255, 0.3) !important; 
        border-left: 6px solid #00eeff !important; /* Marcação lateral da lâmina */
        border-radius: 6px !important; padding: 14px !important;
        transition: all 0.3s ease;
        font-family: monospace !important; letter-spacing: 1px; font-size: 15px !important;
    }
    input[type="text"]:focus, input[type="password"]:focus { 
        border-color: #00eeff !important; box-shadow: 0 0 20px rgba(0, 238, 255, 0.5) !important; background-color: rgba(0, 0, 0, 0.8) !important;
    }
    
    [data-testid="stFormSubmitButton"] button {
        background: linear-gradient(90deg, #002395, #3b82f6) !important; color: #FFFFFF !important; border: 1px solid rgba(0,238,255,0.4) !important; border-radius: 30px !important; 
        padding: 14px !important; margin-top: 20px !important; box-shadow: 0px 6px 20px rgba(0, 35, 149, 0.7) !important; width: 100%;
        transition: all 0.3s ease; text-transform: uppercase; letter-spacing: 1.5px;
    }
    [data-testid="stFormSubmitButton"] button * { color: #FFFFFF !important; font-weight: 900 !important; font-size: 16px !important; text-shadow: none !important;}
    [data-testid="stFormSubmitButton"] button:hover { 
        background: linear-gradient(90deg, #3b82f6, #00eeff) !important; transform: translateY(-3px); box-shadow: 0px 10px 25px rgba(0, 238, 255, 0.6) !important;
    }
    
    hr.custom-divider { border: 0; height: 1px; background: linear-gradient(to right, rgba(0,238,255,0), rgba(0,238,255,0.7), rgba(0,238,255,0)); margin: 30px 0 25px 0; }
    </style>
    """, unsafe_allow_html=True)

    col_vazia_esq, col_login, col_vazia_dir = st.columns([1, 1.2, 1]) 
    
    with col_login:
        with st.form(key="login_form"):
            
            logo_b64 = get_base64_file(ARQUIVO_LOGO_LOGIN)
            if logo_b64:
                # LOGO MAIS DESTACADO E MAIOR
                st.markdown(f'''<div style="display: flex; justify-content: center; margin-bottom: 10px;"><img src="data:image/png;base64,{logo_b64}" style="max-height: 130px; filter: drop-shadow(0px 0px 20px rgba(255,255,255,0.6));"></div>''', unsafe_allow_html=True)
            
            st.markdown("<h2 style='text-align: center; color:#00eeff !important; font-family: monospace; font-weight: 900; margin-bottom: 25px; text-shadow: 0px 0px 15px rgba(0,238,255,0.6);'>🧫 CULTURA DE DADOS BI</h2>", unsafe_allow_html=True)
            
            usuario_input = st.text_input("🔬 Identificação (Usuário):")
            senha_input = st.text_input("🧬 Sequência (Senha):", type="password")
            
            submit_button = st.form_submit_button("INICIAR ANÁLISE 🚀", use_container_width=True)
            st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
            
            assinatura_b64 = get_base64_file(ARQUIVO_ASSINATURA)
            if assinatura_b64:
                # ASSINATURA MAIOR, SEM OPACIDADE E COM SOMBRA FORTE
                st.markdown(f'''
                    <div style="text-align: center; padding-top: 5px;">
                        <img src="data:image/png;base64,{assinatura_b64}" style="max-height: 95px; max-width: 100%; object-fit: contain; margin: 0 auto; display: block; filter: drop-shadow(0px 5px 15px rgba(0,0,0,1)) drop-shadow(0px 0px 5px rgba(0,238,255,0.4));">
                    </div>
                ''', unsafe_allow_html=True)
            else:
                st.error(f"⚠️ Imagem de Assinatura '{ARQUIVO_ASSINATURA}' não encontrada.")

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
                    st.error("❌ Identificação rejeitada pela matriz. Tente novamente.")

    st.stop()

# ==========================================
# 6. TELA DO SISTEMA (DASHBOARD)
# ==========================================
else:

    # CSS GLOBAL (FONTES E ESTILOS CYBER PREMIUM)
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@800&family=Orbitron:wght@700&display=swap');
        
        video.escondido {{ display: none !important; }}
        html, body, [data-testid="stAppViewContainer"], .block-container {{ overflow: visible !important; height: auto !important; }}
        
        .stApp {{ background-color: #0b1120 !important; color: #f8fafc !important; animation: none !important; }}
        header[data-testid="stHeader"] {{ background: transparent !important; }}
        
        section[data-testid="stSidebar"] {{
            background-color: #0f172a !important; 
            border-right: 1px solid #1e293b !important;
        }}
        section[data-testid="stSidebar"] * {{ color: #e2e8f0 !important; }}
        
        div[data-testid="metric-container"] {{
            background: linear-gradient(145deg, #111827, #1e293b) !important; 
            border: 1px solid rgba(0, 238, 255, 0.15) !important;
            border-left: 4px solid #00eeff !important;
            padding: 20px !important; border-radius: 12px !important;
            box-shadow: 0 8px 20px rgba(0,0,0,0.5) !important; 
            transition: transform 0.3s ease, box-shadow 0.3s ease !important;
        }}
        div[data-testid="metric-container"]:hover {{
            transform: translateY(-6px) !important;
            box-shadow: 0 12px 25px rgba(0, 238, 255, 0.2) !important;
            border-color: rgba(0, 238, 255, 0.4) !important;
        }}
        div[data-testid="metric-container"] label {{ color: #94a3b8 !important; font-weight: bold !important;}}
        div[data-testid="metric-container"] div {{ color: #00eeff !important; text-shadow: 0px 0px 10px rgba(0, 238, 255, 0.3) !important; }}
        
        .stDataFrame {{ border-radius: 10px; border: 1px solid #1e293b !important; }}
        h1, h2, h3, h4, p, label {{ color: #f8fafc !important; }}
        
        div.stButton > button {{ background: #1e3a8a !important; border: 1px solid #3b82f6 !important; border-radius: 8px !important; transition: 0.3s; }}
        div.stButton > button * {{ color: #FFFFFF !important; font-weight: bold !important; }}
        div.stButton > button:hover {{ background: #3b82f6 !important; box-shadow: 0 0 15px rgba(59, 130, 246, 0.5) !important;}}
        
        /* OTIMIZAÇÃO DO PDF */
        @media print {{
            @page {{ size: A4 landscape; margin: 10mm; }} 
            body, .stApp {{ background: white !important; color: black !important; -webkit-print-color-adjust: exact !important; }}
            h1, h2, h3, h4, p, label {{ color: black !important; text-shadow: none !important;}}
            section[data-testid="stSidebar"], header[data-testid="stHeader"], iframe, button {{ display: none !important; }}
            div[data-testid="stAppViewBlockContainer"] {{ padding: 0 !important; margin: 0 !important; max-width: 100% !important; width: 100% !important;}}
            .js-plotly-plot {{ max-width: 100% !important; page-break-inside: avoid !important; }}
            div[data-testid="metric-container"] {{ background: #f1f5f9 !important; border: 1px solid #cbd5e1 !important; box-shadow: none !important; transform: none !important;}}
            div[data-testid="metric-container"] label, div[data-testid="metric-container"] div {{ color: black !important; text-shadow: none !important; }}
        }}
        </style>
    """, unsafe_allow_html=True)

    st.components.v1.html("""
        <script>function printPDF() { window.parent.print(); }</script>
        <button onclick="printPDF()" style="background: linear-gradient(90deg, #002395, #00eeff);color:white;padding:12px 20px;border:none;border-radius:8px;cursor:pointer;font-weight:900;width:100%;box-shadow: 0px 4px 15px rgba(0,238,255,0.3); text-transform: uppercase;">🖨️ Exportar Relatório (PDF)</button>
    """, height=60)

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
                match_tag = re.search(r'\[\s*([A-Z]+)\s*\]', sub)
                if not match_tag: continue
                tag = match_tag.group(1)
                
                linha = {
                    "Data": data_pac, "Código_Paciente": cod_pac, "Idade": "Não Informada", "Sexo": "Não Informado",
                    "Material_Exame": f"[{tag}]", "Resultado": "Negativo", "Bactéria": "N/A", 
                    "Indicados (S)": "", "Resistentes (R)": "", "Unidade": unidade_pac, "Período_Arquivo": periodo_doc
                }
                
                match_mat = re.search(r'(?:MAT(?:ERIAL)?):\s*(.*?)(?=RES|1:|\.1:|[A-Z]{3}2?:|\n|$)', sub)
                if match_mat:
                    mat_text = re.sub(r'[\.\d]+$', '', match_mat.group(1)).strip()
                    linha["Material_Exame"] = padronizar_material(f"[{tag}] {mat_text}")
                else:
                    linha["Material_Exame"] = padronizar_material(linha["Material_Exame"])
                
                if "Não houve desenvolvimento" in sub or "Não houve crescimento" in sub:
                    linha["Resultado"] = "Negativo"
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

    df_todos_dados = carregar_dados_salvos()
    
    df_reais = pd.DataFrame()
    df_mock = pd.DataFrame()

    if not df_todos_dados.empty:
        df_todos_dados['Data_Obj'] = pd.to_datetime(df_todos_dados['Data'], format="%d/%m/%Y", errors='coerce')
        df_todos_dados['Mês/Ano'] = df_todos_dados['Data_Obj'].dt.strftime('%m/%Y').fillna('Desconhecido')
        
        unid_perm = st.session_state.get('unidades_permitidas', 'Todas')
        if unid_perm != "Todas" and st.session_state['usuario'] != "vhpezzeti":
            unidades_liberadas = [u.strip() for u in unid_perm.split(",")]
            df_todos_dados = df_todos_dados[df_todos_dados['Unidade'].isin(unidades_liberadas)]

        df_reais = df_todos_dados[df_todos_dados['Período_Arquivo'] != 'Gerado Demo']
        df_mock = df_todos_dados[df_todos_dados['Período_Arquivo'] == 'Gerado Demo']

    # ==========================
    # LOGOTIPO ANIMADO 3D (MENU LATERAL)
    # ==========================
    html_animacao = ""
    if video_logo_b64:
        html_animacao = f'<video autoplay loop muted playsinline style="width: 140px; margin-bottom: 5px; filter: drop-shadow(0px 0px 20px rgba(0, 238, 255, 0.4)); mix-blend-mode: screen;"><source src="data:video/mp4;base64,{video_logo_b64}" type="video/mp4"></video>'
    else:
        st.sidebar.error(f"⚠️ Vídeo '{ARQUIVO_LOGO_ANIMADO_MENU}' não encontrado.")

    html_menu = f"""<div style="text-align: center; margin-top: 0px; margin-bottom: 30px;">
{html_animacao}
<h1 style="font-family: 'Orbitron', sans-serif; color: #00eeff; font-size: 22px; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; text-shadow: 0px 0px 15px rgba(0, 238, 255, 0.6); margin: 0; padding-top: 5px;">SÃO FRANCISCO</h1>
<h2 style="font-family: 'Montserrat', sans-serif; color: #f8fafc; font-size: 11px; font-weight: 800; letter-spacing: 5px; text-transform: uppercase; margin: 5px 0 0 0; opacity: 0.8;">Laboratório</h2>
</div>"""
    st.sidebar.markdown(html_menu, unsafe_allow_html=True)

    nivel_atual = st.session_state.get('nivel_acesso', 'Visualizador')

    st.sidebar.markdown(f"### 🚀 **{st.session_state['usuario'].capitalize()}**")
    st.sidebar.markdown(f"<span style='color:#00eeff; font-weight:bold;'>• Nível: {nivel_atual}</span>", unsafe_allow_html=True)
    st.sidebar.markdown("---")

    opcoes_menu = ["🏢 Dashboard Principal", "📈 Analytics & Tendências"]
    if nivel_atual in ["Operador", "Administrador"] or st.session_state['usuario'] == "vhpezzeti":
        opcoes_menu.append("📂 Upload de Laudos")
    if nivel_atual == "Administrador" or st.session_state['usuario'] == "vhpezzeti":
        opcoes_menu.append("⚙️ Console Admin")

    menu = st.sidebar.radio("Navegação", opcoes_menu)
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Encerrar Sessão", use_container_width=True):
        st.session_state['logado'] = False
        st.rerun()

    if menu == "⚙️ Console Admin":
        st.title("⚙️ Console Administrativo Central")
        
        tab1, tab2, tab3, tab4 = st.tabs(["➕ Novo Usuário", "✏️ Editar/Excluir", "📋 Auditoria", "🧪 Simulador BI (Mock)"])
        df_users_adm = carregar_usuarios()
        lista_usuarios = df_users_adm['Usuario'].tolist() if not df_users_adm.empty else []

        with tab1:
            with st.form("form_cadastro"):
                c1, c2 = st.columns(2)
                novo_usuario = c1.text_input("Login:")
                nova_senha = c2.text_input("Senha:", type="password")
                c3, c4 = st.columns(2)
                novo_nivel = c3.selectbox("Nível:", ["Visualizador", "Operador", "Administrador"])
                nova_unid = c4.multiselect("Unidades (Vazio = Todas):", UNIDADES_OFICIAIS)
                if st.form_submit_button("Criar Acesso") and novo_usuario and nova_senha:
                    if novo_usuario not in lista_usuarios:
                        str_unidades = ", ".join(nova_unid) if nova_unid else "Todas"
                        novo_registro = pd.DataFrame([{"Usuario": novo_usuario, "Senha": f"'{nova_senha}", "Nivel_Acesso": novo_nivel, "Unidades_Permitidas": str_unidades}])
                        salvar_novo_usuario(pd.concat([df_users_adm, novo_registro], ignore_index=True))
                        st.success("✅ Acesso Liberado!")
                        time.sleep(1); st.rerun()

        with tab2:
            usr_editar = st.selectbox("Selecionar Credencial:", [""] + lista_usuarios)
            if usr_editar:
                udata = df_users_adm[df_users_adm['Usuario'] == usr_editar].iloc[0]
                with st.form("form_edicao"):
                    n_senha = st.text_input("Nova Senha (vazio mantém):", type="password")
                    n_nivel = st.selectbox("Nível:", ["Visualizador", "Operador", "Administrador"], index=["Visualizador", "Operador", "Administrador"].index(udata['Nivel_Acesso']))
                    if st.form_submit_button("Atualizar Matriz"):
                        idx = df_users_adm.index[df_users_adm['Usuario'] == usr_editar][0]
                        if n_senha: df_users_adm.at[idx, 'Senha'] = f"'{n_senha}"
                        df_users_adm.at[idx, 'Nivel_Acesso'] = n_nivel
                        salvar_novo_usuario(df_users_adm)
                        st.success("✅ Matriz Atualizada!"); time.sleep(1); st.rerun()
                    if st.form_submit_button("🗑️ Revogar Acesso"):
                        salvar_novo_usuario(df_users_adm[df_users_adm['Usuario'] != usr_editar])
                        st.success("✅ Acesso Revogado!"); time.sleep(1); st.rerun()
        
        with tab3: 
            st.dataframe(df_users_adm, use_container_width=True)

        with tab4:
            st.markdown("### 🧪 Simulador de Alta Densidade (Dados Falsos)")
            st.info("O robô injeta dados biométricos aleatórios para teste de estresse dos gráficos. Estes dados são invisíveis nas outras abas.")
            
            if st.button("Injetar 100 Laudos Sintéticos", use_container_width=True):
                df_novos_mock = gerar_dados_teste()
                df_atual = conn.read(worksheet="Página1", ttl=0).dropna(how="all")
                salvar_dados(pd.concat([df_atual, df_novos_mock]))
                st.success("✅ Injeção concluída com sucesso!")
                time.sleep(1); st.rerun()
            
            if not df_mock.empty:
                st.markdown("---")
                df_mock_pos = df_mock[df_mock['Resultado'] == 'Positivo']
                
                d1, d2 = st.columns(2)
                with d1:
                    st.markdown("#### 👥 Impacto por Sexo Biológico")
                    st.plotly_chart(px.pie(df_mock_pos, names='Sexo', hole=0.5, color_discrete_sequence=['#f43f5e', '#38bdf8'], template="plotly_dark"), use_container_width=True)
                with d2:
                    st.markdown("#### 📊 Distribuição Etária")
                    df_mock_pos['Idade'] = pd.to_numeric(df_mock_pos['Idade'], errors='coerce')
                    st.plotly_chart(px.histogram(df_mock_pos, x='Idade', nbins=10, color_discrete_sequence=[COR_NEON], text_auto=True, template="plotly_dark"), use_container_width=True)
            else:
                st.warning("Banco de testes vazio. Inicie a injeção sintética.")

    elif menu == "📂 Upload de Laudos":
        st.title("📂 Processamento Lógico de PDFs")
        st.info("Motor de regex ativo. Arraste os laudos laboratoriais para higienização e integração ao banco central.")
        arq = st.file_uploader("Dropzone do Sistema", type=['pdf', 'txt'])
        if arq and st.button("Processar Carga de Dados", use_container_width=True):
            txt = ""
            if arq.name.endswith('.pdf'):
                for p in PyPDF2.PdfReader(arq).pages: txt += p.extract_text() + "\n"
            else: txt = arq.read().decode("utf-8")
            df_novo = extrair_dados_pdf(txt)
            if not df_novo.empty:
                df_puro = conn.read(worksheet="Página1", ttl=0).dropna(how="all")
                salvar_dados(pd.concat([df_puro, df_novo]).drop_duplicates(subset=['Data', 'Código_Paciente', 'Material_Exame', 'Unidade']))
                st.success(f"✅ Extrato completo. {len(df_novo)} registros consolidados.")
                st.balloons()
            else: st.error("Erro na varredura. Padrão não reconhecido.")

    elif menu == "🏢 Dashboard Principal":
        st.title("🏢 Monitoramento Operacional")
        if df_reais.empty: st.info("O Data Lake encontra-se vazio. Aguardando ingestão de PDFs.")
        else:
            c1, c2, c3 = st.columns(3)
            meses_disp = sorted(list(df_reais[df_reais['Mês/Ano'] != 'Desconhecido']['Mês/Ano'].unique()))
            meses_sel = c1.multiselect("📅 Ciclo Temporal", meses_disp, default=meses_disp)
            
            unid_disp = sorted(list(df_reais['Unidade'].unique()))
            unid_sel = c2.multiselect("🏢 Nós Físicos (Unidades)", unid_disp, default=unid_disp)
            
            exame_disp = sorted(list(df_reais['Material_Exame'].unique()))
            exame_sel = c3.multiselect("🧪 Matriz de Exames", exame_disp, default=exame_disp)
            
            df_f = df_reais[df_reais['Mês/Ano'].isin(meses_sel) & df_reais['Unidade'].isin(unid_sel) & df_reais['Material_Exame'].isin(exame_sel)]
            
            if df_f.empty: st.warning("Matriz de dados zerada para estes parâmetros.")
            else:
                t_pos = len(df_f[df_f['Resultado'] == 'Positivo'])
                t_neg = len(df_f[df_f['Resultado'] == 'Negativo'])
                qtd_meses = len(meses_sel) if len(meses_sel) > 0 else 1
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Volume Absoluto Lidos", len(df_f))
                m2.metric("Positivados Isolados", f"🔴 {t_pos}")
                m3.metric("Controle Negativo", f"🔵 {t_neg}")
                m4.metric("Média / Ciclo", round(len(df_f) / qtd_meses, 1))

                if t_pos > 0:
                    df_pos = df_f[df_f['Resultado'] == 'Positivo']
                    st.markdown("---")
                    g1, g2 = st.columns(2)
                    with g1:
                        st.markdown("#### 📊 Taxa de Ocorrência (Pos x Neg)")
                        st.plotly_chart(px.pie(df_f, names='Resultado', hole=0.6, color='Resultado', color_discrete_map={'Positivo': '#f43f5e', 'Negativo': '#3b82f6'}, template="plotly_dark"), use_container_width=True)
                    with g2:
                        st.markdown("#### 🧫 Espectro Bacteriano Global")
                        df_pct = df_pos['Bactéria'].value_counts(normalize=True).mul(100).round(2).reset_index()
                        df_pct.columns = ['Bactéria', '%']
                        st.plotly_chart(px.bar(df_pct, x='%', y='Bactéria', orientation='h', text_auto=True, color='Bactéria', color_discrete_sequence=PALETA_CORES, template="plotly_dark").update_layout(yaxis={'categoryorder':'total ascending'}), use_container_width=True)

                    st.markdown("#### 📋 Log de Pacientes Criticos")
                    st.dataframe(df_pos[['Data', 'Código_Paciente', 'Unidade', 'Material_Exame', 'Bactéria', 'Indicados (S)', 'Resistentes (R)']], use_container_width=True, hide_index=True)

    elif menu == "📈 Analytics & Tendências":
        st.title("📈 Motor Analítico e Demográfico")
        if df_reais.empty:
            st.info("Necessária base de dados para projeções analíticas.")
        else:
            df_pos_comp = df_reais[df_reais['Resultado'] == 'Positivo']
            if not df_pos_comp.empty:
                b_top = df_pos_comp['Bactéria'].value_counts().idxmax()
                exame_top = df_pos_comp['Material_Exame'].value_counts().idxmax()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Patógeno Dominante", b_top)
                c2.metric("Vetor Material", exame_top)
                c3.metric("Pico Sazonal", df_pos_comp['Mês/Ano'].value_counts().idxmax())
                
                st.markdown("---")
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    st.markdown("#### 📉 Traçado Epidemiológico Histórico")
                    agrupado = df_pos_comp.groupby('Mês/Ano').size().reset_index(name='Casos Registados')
                    st.plotly_chart(px.area(agrupado, x='Mês/Ano', y='Casos Registados', markers=True, color_discrete_sequence=[COR_NEON], template="plotly_dark"), use_container_width=True)
                with col_g2:
                    st.markdown("#### 🏆 Top Patógenos por Vetor")
                    top_b_exame = df_pos_comp.groupby(['Material_Exame', 'Bactéria']).size().reset_index(name='Volume').sort_values(['Material_Exame', 'Volume'], ascending=[True, False])
                    st.dataframe(top_b_exame.groupby('Material_Exame').head(2), use_container_width=True, hide_index=True)

                st.markdown("---")
                st.markdown("### 🧬 Vetor Demográfico (População Atingida)")
                df_demo = df_pos_comp[df_pos_comp['Idade'] != 'Não Informada'].copy()
                
                if df_demo.empty:
                    st.info("⚠️ Extração biométrica (Idade/Sexo) não encontrada nos blocos reais. Painel silenciado.")
                else:
                    df_demo['Idade'] = pd.to_numeric(df_demo['Idade'], errors='coerce')
                    
                    d1, d2 = st.columns(2)
                    with d1:
                        st.markdown("#### 👥 Infecção Cruzada por Sexo")
                        st.plotly_chart(px.pie(df_demo, names='Sexo', hole=0.5, color_discrete_sequence=['#f43f5e', '#38bdf8'], template="plotly_dark"), use_container_width=True)
                    with d2:
                        st.markdown("#### 📊 Pirâmide Etária Infecciosa")
                        st.plotly_chart(px.histogram(df_demo, x='Idade', nbins=10, color_discrete_sequence=[COR_NEON], text_auto=True, template="plotly_dark"), use_container_width=True)

            else:
                st.warning("Variáveis insuficientes para construção de gráficos.")
