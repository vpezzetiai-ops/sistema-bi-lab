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
ARQUIVO_LOGO_PROGRAMA = "logoprograma.png" # CORRIGIDO PARA PNG

# ==========================================
# CONFIGURAÇÕES INICIAIS DE TEMA
# ==========================================
st.set_page_config(page_title="S.I.B.C. - Sistema Integrado", layout="wide", initial_sidebar_state="expanded")

COR_NEON = '#00eeff'
COR_POSITIVO = '#f43f5e'
COR_NEGATIVO = '#3b82f6'
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
    .splash-screen-{loader_id} h2 {{ color: #00eeff; font-family: 'Orbitron', sans-serif; margin-top: 20px; text-shadow: 0px 0px 15px rgba(0,238,255,0.9); letter-spacing: 5px; font-size: 20px; font-weight: 900; }}
    </style>
    <div class="splash-screen-{loader_id}"><img src="data:image/gif;base64,{gif_b64}"><h2>PROCESSANDO...</h2></div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. MOTOR DE BANCO DE DADOS E REGEX
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
            match_tag = re.search(r'\[\s*([A-Z]+)\s*\]', sub)
            if not match_tag: continue
            tag = match_tag.group(1)
            linha = {"Data": data_pac, "Código_Paciente": cod_pac, "Idade": "Não Informada", "Sexo": "Não Informado", "Material_Exame": f"[{tag}]", "Resultado": "Negativo", "Bactéria": "N/A", "Indicados (S)": "", "Resistentes (R)": "", "Unidade": unidade_pac, "Período_Arquivo": periodo_doc}
            
            match_mat = re.search(r'(?:MAT(?:ERIAL)?):\s*(.*?)(?=RES|1:|\.1:|[A-Z]{3}2?:|\n|$)', sub)
            if match_mat: linha["Material_Exame"] = padronizar_material(f"[{tag}] {re.sub(r'[\.\d]+$', '', match_mat.group(1)).strip()}")
            else: linha["Material_Exame"] = padronizar_material(linha["Material_Exame"])
            
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
    exames_mock = ["[URAB] Urina Jato Médio", "[HEMO] Sangue Venoso", "[SWAB] Secreção", "[LCR] Líquido Cefalorraquidiano"]
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
            "Data": data_mock, "Código_Paciente": f"MOCK-{random.randint(100000, 999999)}", 
            "Idade": int(random.gauss(45, 15)), "Sexo": random.choice(sexos_mock), 
            "Material_Exame": random.choice(exames_mock), "Resultado": res, "Bactéria": bac, 
            "Indicados (S)": sens, "Resistentes (R)": rest, "Unidade": random.choice(UNIDADES_OFICIAIS[:-1]),
            "Período_Arquivo": "Gerado Demo"
        })
    return pd.DataFrame(novos_dados)

# ==========================================
# CONTROLE DE SESSÃO
# ==========================================
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'usuario' not in st.session_state: st.session_state['usuario'] = ""
if 'nivel_acesso' not in st.session_state: st.session_state['nivel_acesso'] = "Visualizador"
if 'unidades_permitidas' not in st.session_state: st.session_state['unidades_permitidas'] = "Todas"

# ==========================================
# 5. TELA DE LOGIN (PLACA DE PETRI CLÁSSICA E CENTRALIZADA)
# ==========================================
if not st.session_state['logado']:
    
    video_fundo_b64 = get_base64_file(ARQUIVO_VIDEO_FUNDO)
    if video_fundo_b64:
        st.markdown(f'''<video autoplay loop muted playsinline style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -999; object-fit: cover; filter: brightness(0.4) contrast(1.1);"><source src="data:video/mp4;base64,{video_fundo_b64}" type="video/mp4"></video>''', unsafe_allow_html=True)
    else:
        st.markdown('<style>.stApp { background-color: #040d21 !important; }</style>', unsafe_allow_html=True)

    # CSS DA PLACA DE PETRI ORIGINAL MELHORADA E CENTRALIZADA
    st.markdown("""
    <style>
    @keyframes floating { 0% { transform: translateY(0px); } 50% { transform: translateY(-12px); } 100% { transform: translateY(0px); } }
    .stApp { background: transparent !important; }
    header[data-testid="stHeader"] { display: none !important; } 
    
    [data-testid="stForm"] {
        width: 480px !important; height: 480px !important; border-radius: 50% !important; 
        background: radial-gradient(circle at 40% 40%, rgba(200, 180, 50, 0.15) 0%, rgba(0, 30, 40, 0.4) 60%, rgba(0, 0, 0, 0.8) 100%) !important;
        backdrop-filter: blur(12px) !important; -webkit-backdrop-filter: blur(12px) !important;
        border: 8px solid rgba(255, 255, 255, 0.1) !important;
        border-top: 8px solid rgba(255, 255, 255, 0.3) !important;
        border-bottom: 8px solid rgba(0, 0, 0, 0.8) !important;
        box-shadow: inset 0px 0px 40px rgba(0, 238, 255, 0.1), 0px 30px 50px rgba(0,0,0,0.9), 0px 0px 30px rgba(0, 238, 255, 0.2) !important;
        display: flex !important; flex-direction: column !important; justify-content: center !important; align-items: center !important;
        margin: 5vh auto !important; padding: 0px !important; z-index: 10;
        animation: floating 6s ease-in-out infinite;
    }
    
    [data-testid="stForm"] > div { width: 100% !important; max-width: 320px !important; margin: 0 auto !important; }
    [data-testid="stForm"] label, [data-testid="stForm"] p { color: #f8fafc !important; font-weight: 800; text-shadow: 0px 2px 4px rgba(0,0,0,1) !important; font-size: 14px;}
    
    input[type="text"], input[type="password"] {
        background-color: rgba(0, 10, 20, 0.7) !important; color: #00eeff !important; -webkit-text-fill-color: #00eeff !important;
        border: 1px solid rgba(0, 238, 255, 0.3) !important; border-radius: 8px !important; padding: 12px !important;
        font-family: monospace !important; text-align: center; letter-spacing: 1px; width: 100% !important;
    }
    input[type="text"]:focus, input[type="password"]:focus { border-color: #00eeff !important; box-shadow: 0 0 15px rgba(0, 238, 255, 0.5) !important; background-color: rgba(0, 0, 0, 0.9) !important;}
    
    /* BOTÃO TOTALMENTE CENTRALIZADO */
    [data-testid="stFormSubmitButton"] { 
        display: flex !important; justify-content: center !important; align-items: center !important; 
        width: 100% !important; margin-top: 15px !important; 
    }
    [data-testid="stFormSubmitButton"] button {
        background: linear-gradient(90deg, #002395, #00eeff) !important; color: white !important;
        border: none !important; border-radius: 25px !important; padding: 12px 30px !important;
        font-weight: 800 !important; font-size: 14px !important; letter-spacing: 1.5px;
        box-shadow: 0px 5px 15px rgba(0,0,0,0.6) !important; width: auto !important; transition: 0.3s;
    }
    [data-testid="stFormSubmitButton"] button:hover { transform: scale(1.05); box-shadow: 0px 5px 20px rgba(0, 238, 255, 0.6) !important; }
    </style>
    """, unsafe_allow_html=True)

    with st.form(key="login_form", clear_on_submit=False):
        logo_b64 = get_base64_file(ARQUIVO_LOGO_LOGIN)
        if logo_b64:
            st.markdown(f'''<div style="text-align: center; margin-bottom: 5px; margin-top: -10px;"><img src="data:image/png;base64,{logo_b64}" style="height: 70px; filter: drop-shadow(0px 0px 10px rgba(255,255,255,0.7));"></div>''', unsafe_allow_html=True)
        
        # EMOTICONS DE VOLTA!
        st.markdown("<h2 style='text-align: center; color:#00eeff !important; font-family: monospace; font-weight: 900; margin-bottom: 20px; font-size: 16px; text-shadow: 0px 0px 10px rgba(0,238,255,0.8);'>🧫 SISTEMA INTEGRADO DE BIOLOGIA COMPUTACIONAL 🦠</h2>", unsafe_allow_html=True)
        
        usuario_input = st.text_input("🔬 Identificação:")
        senha_input = st.text_input("🧬 Sequência Genética:", type="password")
        
        submit_button = st.form_submit_button("INICIAR PROTOCOLO")
        
        assinatura_b64 = get_base64_file(ARQUIVO_ASSINATURA)
        if assinatura_b64:
            st.markdown(f'''<div style="text-align: center; margin-top: 15px;"><img src="data:image/png;base64,{assinatura_b64}" style="height: 45px; filter: drop-shadow(0px 2px 5px rgba(0,0,0,1));"></div>''', unsafe_allow_html=True)

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

    st.stop()

# ==========================================
# 6. DASHBOARD & CSS DE IMPRESSÃO (PDF FORÇA BRUTA)
# ==========================================
else:

    # CSS REFINADO E PDF RESOLVIDO POR COMPLETO
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@800&family=Orbitron:wght@700&display=swap');
        
        header[data-testid="stHeader"] {{ background: transparent !important; }}
        .stApp {{ background-color: #0b1120 !important; color: #f8fafc !important; }}
        
        section[data-testid="stSidebar"] {{ background-color: #0f172a !important; border-right: 1px solid #1e293b !important; }}
        section[data-testid="stSidebar"] * {{ color: #e2e8f0 !important; }}
        
        div[data-testid="metric-container"] {{ background: linear-gradient(145deg, #111827, #1e293b) !important; border-left: 3px solid #00eeff !important; padding: 20px !important; border-radius: 8px !important; box-shadow: 0 5px 15px rgba(0,0,0,0.5) !important; }}
        div[data-testid="metric-container"] label {{ color: #94a3b8 !important; font-size: 14px !important;}}
        div[data-testid="metric-container"] div {{ color: #00eeff !important; text-shadow: 0px 0px 10px rgba(0,238,255,0.3) !important;}}
        
        /* 🔥 PDF - MODO FORÇA BRUTA 🔥 */
        @media print {{
            @page {{ size: A4 landscape !important; margin: 5mm !important; }}
            
            /* Remove fundos e força tudo para branco/preto */
            html, body, .stApp, .block-container, [data-testid="stAppViewContainer"] {{ 
                background: white !important; background-color: white !important; color: black !important; 
                padding: 0 !important; margin: 0 !important; max-width: 100% !important; width: 100% !important; overflow: visible !important;
            }}
            h1, h2, h3, h4, p, label, div, span {{ color: black !important; text-shadow: none !important; box-shadow: none !important; }}
            
            /* Esconde itens de interface */
            section[data-testid="stSidebar"], header, button, .stButton, input, select, .stMultiSelect, div[data-testid="stFileUploader"] {{ display: none !important; }}
            
            /* QUEBRA DE COLUNAS - ESSENCIAL PARA IMPRESSÃO DO STREAMLIT */
            div[data-testid="column"] {{ width: 100% !important; max-width: 100% !important; flex: 0 0 100% !important; display: block !important; margin-bottom: 20px !important; }}
            div[data-testid="stVerticalBlock"] {{ display: block !important; width: 100% !important; flex: none !important; }}
            
            /* EXPANSÃO DE TABELAS SEM BARRA DE ROLAGEM */
            .stDataFrame, [data-testid="stDataFrameContainer"], [data-testid="stDataFrameContainer"] > div, .stDataFrame > div {{ 
                height: auto !important; max-height: 9999px !important; overflow: visible !important; width: 100% !important; display: table !important; position: static !important;
            }}
            table {{ width: 100% !important; border-collapse: collapse !important; table-layout: auto !important; }}
            th, td {{ border: 1px solid #000 !important; padding: 8px !important; color: black !important; background: white !important; white-space: normal !important; word-wrap: break-word !important; }}
            
            /* Gráficos Plotly */
            .js-plotly-plot, .plotly {{ width: 100% !important; max-width: 100% !important; page-break-inside: avoid !important; }}
            
            /* Ajuste de Métricas para impressão */
            div[data-testid="metric-container"] {{ background: white !important; border: 1px solid #000 !important; margin-bottom: 15px !important; border-left: 5px solid #000 !important; padding: 10px !important; page-break-inside: avoid !important;}}
            div[data-testid="metric-container"] div {{ color: black !important; }}
        }}
        </style>
    """, unsafe_allow_html=True)

    # BOTÃO DE PDF
    st.components.v1.html("""
        <script>function doPrint() { window.parent.print(); }</script>
        <button onclick="doPrint()" style="background: linear-gradient(90deg, #002395, #3b82f6); color:white; padding:12px 20px; border:none; border-radius:5px; cursor:pointer; font-weight:bold; width:100%; text-transform: uppercase; letter-spacing: 1px; box-shadow: 0px 4px 10px rgba(0,0,0,0.5);">🖨️ Exportar Documento PDF Oficial</button>
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
    # LOGO DO PROGRAMA NO MENU LATERAL COM EFEITO
    # ==========================================
    logo_prog_b64 = get_base64_file(ARQUIVO_LOGO_PROGRAMA)
    if logo_prog_b64:
        st.sidebar.markdown(f'''
            <div style="display: flex; justify-content: center; margin-bottom: 20px;">
                <img src="data:image/png;base64,{logo_prog_b64}" 
                     style="width: 150px; filter: drop-shadow(0px 0px 20px rgba(0, 238, 255, 0.5));">
            </div>
        ''', unsafe_allow_html=True)
    else:
        st.sidebar.markdown("<h2 style='text-align:center; color:#00eeff;'>S.I.B.C.</h2>", unsafe_allow_html=True)
    
    st.sidebar.markdown(f"👤 **{st.session_state['usuario'].upper()}**")
    st.sidebar.markdown(f"🛡️ **Nível:** <span style='color:#00eeff;'>{st.session_state.get('nivel_acesso', '')}</span>", unsafe_allow_html=True)
    st.sidebar.markdown("---")

    opcoes_menu = ["🏢 Dashboard Principal", "📈 Analytics & Tendências"] # Analytics Restaurado
    if st.session_state.get('nivel_acesso') in ["Operador", "Administrador"] or st.session_state['usuario'] == "vhpezzeti":
        opcoes_menu.append("📂 Upload de Laudos")
    if st.session_state.get('nivel_acesso') == "Administrador" or st.session_state['usuario'] == "vhpezzeti":
        opcoes_menu.append("⚙️ Console Admin")

    menu = st.sidebar.radio("Navegação do Sistema", opcoes_menu)
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Encerrar Sessão", use_container_width=True):
        st.session_state['logado'] = False
        st.rerun()

    # ========================================================
    # TELA 1: DASHBOARD PRINCIPAL
    # ========================================================
    if menu == "🏢 Dashboard Principal":
        st.title("🏢 Monitoramento Clínico Operacional")
        if df_reais.empty: 
            st.info("Nenhum Laudo Oficial processado. Vá em 'Upload de Laudos' para iniciar.")
        else:
            c1, c2, c3 = st.columns(3)
            meses_disp = sorted(list(df_reais[df_reais['Mês/Ano'] != 'Desconhecido']['Mês/Ano'].unique()))
            meses_sel = c1.multiselect("📅 Ciclo Temporal", meses_disp, default=meses_disp)
            unid_disp = sorted(list(df_reais['Unidade'].unique()))
            unid_sel = c2.multiselect("🏢 Nós Físicos (Unidades)", unid_disp, default=unid_disp)
            exame_sel = c3.multiselect("🧪 Matriz de Exames", sorted(list(df_reais['Material_Exame'].unique())), default=sorted(list(df_reais['Material_Exame'].unique())))
            
            df_f = df_reais[df_reais['Mês/Ano'].isin(meses_sel) & df_reais['Unidade'].isin(unid_sel) & df_reais['Material_Exame'].isin(exame_sel)]
            if df_f.empty: 
                st.warning("Nenhum dado corresponde aos filtros selecionados.")
            else:
                t_total = len(df_f)
                t_pos = len(df_f[df_f['Resultado'] == 'Positivo'])
                t_neg = len(df_f[df_f['Resultado'] == 'Negativo'])
                pct_pos = (t_pos / t_total * 100) if t_total > 0 else 0
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Volume Total Lidos", t_total)
                m2.metric("Positivados", t_pos, delta=f"{pct_pos:.1f}% Positividade", delta_color="inverse")
                m3.metric("Controle Negativo", t_neg, delta=f"{100-pct_pos:.1f}%", delta_color="normal")
                m4.metric("Média de Laudos / Mês", round(t_total / max(len(meses_sel), 1), 1))
                
                df_pos = df_f[df_f['Resultado'] == 'Positivo']
                if not df_pos.empty:
                    st.markdown("---")
                    g1, g2 = st.columns(2)
                    with g1:
                        st.markdown("#### 📊 Relação Diagnóstica Global (Pos x Neg)")
                        fig1 = px.pie(df_f, names='Resultado', hole=0.5, color='Resultado', color_discrete_map={'Positivo': COR_POSITIVO, 'Negativo': COR_NEGATIVO}, template="plotly_dark")
                        fig1.update_traces(textposition='inside', textinfo='percent+label')
                        fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                        st.plotly_chart(fig1, use_container_width=True)
                    with g2:
                        st.markdown("#### 🧫 Espectro Microbiológico Detalhado")
                        df_bact = df_pos['Bactéria'].value_counts().reset_index()
                        df_bact['Pct'] = (df_bact['count'] / df_bact['count'].sum() * 100).round(1).astype(str) + '%'
                        fig2 = px.bar(df_bact, y='Bactéria', x='count', text='Pct', orientation='h', template="plotly_dark", color='Bactéria', color_discrete_sequence=PALETA_CORES)
                        fig2.update_traces(textposition='auto')
                        fig2.update_layout(yaxis={'categoryorder':'total ascending'}, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
                        st.plotly_chart(fig2, use_container_width=True)

                    st.markdown("#### 📋 Matriz Analítica e Perfil de Resistência (Pacientes Críticos)")
                    st.dataframe(df_pos[['Data', 'Código_Paciente', 'Unidade', 'Material_Exame', 'Bactéria', 'Indicados (S)', 'Resistentes (R)']], use_container_width=True, hide_index=True)

    # ========================================================
    # TELA 2: ANALYTICS E TENDÊNCIAS (RESTAURADO E MELHORADO)
    # ========================================================
    elif menu == "📈 Analytics & Tendências":
        st.title("📈 Motor Analítico e Tendências Demográficas")
        
        # Usa os dados reais para Analytics, se existirem e tiverem Idade/Sexo extraídos, senão mostra aviso.
        # Caso o cliente queira demonstrar isso, ele usa os dados do Mock injetado no admin.
        df_base = df_reais if not df_reais.empty else df_mock
        
        if df_base.empty:
            st.info("Nenhuma base de dados (Real ou Simulada) encontrada para gerar tendências.")
        else:
            df_pos_comp = df_base[df_base['Resultado'] == 'Positivo'].copy()
            if not df_pos_comp.empty:
                b_top = df_pos_comp['Bactéria'].value_counts().idxmax()
                exame_top = df_pos_comp['Material_Exame'].value_counts().idxmax()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Patógeno Dominante", b_top)
                c2.metric("Vetor Material Crítico", exame_top)
                c3.metric("Volume Crítico Analisado", len(df_pos_comp))
                
                st.markdown("---")
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    st.markdown("#### 📉 Traçado Epidemiológico Histórico")
                    # Tenta converter data real ou mock
                    df_pos_comp['Data_Obj'] = pd.to_datetime(df_pos_comp['Data'], format="%d/%m/%Y", errors='coerce')
                    linha_tempo = df_pos_comp.dropna(subset=['Data_Obj']).groupby(df_pos_comp['Data_Obj'].dt.to_period("W")).size().reset_index(name='Casos Registrados')
                    linha_tempo['Data_Obj'] = linha_tempo['Data_Obj'].dt.to_timestamp()
                    if not linha_tempo.empty:
                        fig_linha = px.area(linha_tempo, x='Data_Obj', y='Casos Registrados', markers=True, color_discrete_sequence=[COR_NEON], template="plotly_dark")
                        fig_linha.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis_title="Evolução Temporal")
                        st.plotly_chart(fig_linha, use_container_width=True)
                    else:
                        st.warning("Datas em formato inválido para linha do tempo.")
                        
                with col_g2:
                    st.markdown("#### 🏆 Top Patógenos por Unidade")
                    top_b_unidade = df_pos_comp.groupby(['Unidade', 'Bactéria']).size().reset_index(name='Volume').sort_values(['Unidade', 'Volume'], ascending=[True, False])
                    st.dataframe(top_b_unidade.groupby('Unidade').head(2), use_container_width=True, hide_index=True)

                st.markdown("---")
                st.markdown("### 🧬 Vetor Demográfico (População Atingida)")
                df_demo = df_pos_comp[df_pos_comp['Idade'] != 'Não Informada'].copy()
                
                if df_demo.empty:
                    st.info("⚠️ Extração biométrica (Idade/Sexo) não encontrada nos laudos reais. Use o Simulador no Console Admin para ver estes gráficos.")
                else:
                    df_demo['Idade'] = pd.to_numeric(df_demo['Idade'], errors='coerce')
                    
                    d1, d2 = st.columns(2)
                    with d1:
                        st.markdown("#### 👥 Impacto Cruzado por Gênero")
                        fig_sexo = px.pie(df_demo, names='Sexo', hole=0.5, color_discrete_sequence=['#f43f5e', '#38bdf8'], template="plotly_dark")
                        fig_sexo.update_traces(textposition='inside', textinfo='percent+label')
                        fig_sexo.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                        st.plotly_chart(fig_sexo, use_container_width=True)
                    with d2:
                        st.markdown("#### 📊 Pirâmide Etária Infecciosa")
                        fig_idade = px.histogram(df_demo, x='Idade', nbins=12, color_discrete_sequence=[COR_NEON], text_auto=True, template="plotly_dark")
                        fig_idade.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis_title="Idade do Paciente", yaxis_title="Quantidade")
                        st.plotly_chart(fig_idade, use_container_width=True)
            else:
                st.warning("Variáveis insuficientes para construção de gráficos analíticos.")

    # ========================================================
    # TELA 3: UPLOAD DE LAUDOS
    # ========================================================
    elif menu == "📂 Upload de Laudos":
        st.title("📂 Processamento Lógico de Laudos (PDF)")
        st.info("O algoritmo de extração irá varrer os arquivos em busca de cultura positiva/negativa, antibiograma e dados do paciente.")
        
        arq = st.file_uploader("Arraste os laudos laboratoriais aqui", type=['pdf', 'txt'])
        if arq and st.button("Executar Varredura e Salvar no Banco", use_container_width=True):
            texto_bruto = ""
            with st.spinner("Decodificando documento..."):
                if arq.name.endswith('.pdf'):
                    try:
                        leitor = PyPDF2.PdfReader(arq)
                        for p in leitor.pages: texto_bruto += p.extract_text() + "\n"
                    except Exception as e: st.error(f"Erro ao ler PDF: {e}")
                else: texto_bruto = arq.read().decode("utf-8")
                
                df_novo = extrair_dados_pdf(texto_bruto)
                if not df_novo.empty:
                    df_atual = conn.read(worksheet="Página1", ttl=0).dropna(how="all")
                    df_combinado = pd.concat([df_atual, df_novo]).drop_duplicates(subset=['Data', 'Código_Paciente', 'Material_Exame', 'Unidade'])
                    salvar_dados(df_combinado)
                    st.success(f"✅ Sucesso! {len(df_novo)} registros foram extraídos e integrados ao banco central.")
                    st.balloons()
                    st.dataframe(df_novo, use_container_width=True)
                else: st.error("❌ O sistema não conseguiu localizar padrões microbiológicos reconhecidos neste arquivo.")

    # ========================================================
    # TELA 4: CONSOLE ADMIN
    # ========================================================
    elif menu == "⚙️ Console Admin":
        st.title("⚙️ Painel Administrativo")
        tab1, tab2, tab3, tab4 = st.tabs(["➕ Criar Acesso", "✏️ Gerenciar Usuários", "📋 Dados Brutos", "🧪 Simulador"])
        
        df_users_adm = carregar_usuarios()
        lista_usuarios = df_users_adm['Usuario'].tolist() if not df_users_adm.empty else []

        with tab1:
            st.markdown("### Criar Nova Credencial")
            with st.form("form_cadastro"):
                c1, c2 = st.columns(2)
                novo_usuario = c1.text_input("Nome de Usuário:")
                nova_senha = c2.text_input("Senha Segura:", type="password")
                c3, c4 = st.columns(2)
                novo_nivel = c3.selectbox("Nível de Privilégio:", ["Visualizador", "Operador", "Administrador"])
                nova_unid = c4.multiselect("Unidades Visíveis (Deixe vazio para ver todas):", UNIDADES_OFICIAIS)
                if st.form_submit_button("Gerar Credencial"):
                    if novo_usuario and nova_senha:
                        if novo_usuario not in lista_usuarios:
                            str_unidades = ", ".join(nova_unid) if nova_unid else "Todas"
                            novo_registro = pd.DataFrame([{"Usuario": novo_usuario, "Senha": f"'{nova_senha}", "Nivel_Acesso": novo_nivel, "Unidades_Permitidas": str_unidades}])
                            salvar_novo_usuario(pd.concat([df_users_adm, novo_registro], ignore_index=True))
                            st.success("✅ Usuário criado com sucesso!"); time.sleep(1); st.rerun()
                        else: st.warning("Usuário já existe no banco.")
                    else: st.warning("Preencha usuário e senha.")

        with tab2:
            st.markdown("### Editar ou Revogar Credenciais")
            usr_editar = st.selectbox("Selecione o Usuário:", [""] + lista_usuarios)
            if usr_editar:
                udata = df_users_adm[df_users_adm['Usuario'] == usr_editar].iloc[0]
                with st.form("form_edicao"):
                    n_senha = st.text_input("Nova Senha (Deixe em branco para não alterar):", type="password")
                    n_nivel = st.selectbox("Nível de Privilégio:", ["Visualizador", "Operador", "Administrador"], index=["Visualizador", "Operador", "Administrador"].index(udata['Nivel_Acesso']))
                    if st.form_submit_button("Atualizar Permissões"):
                        idx = df_users_adm.index[df_users_adm['Usuario'] == usr_editar][0]
                        if n_senha: df_users_adm.at[idx, 'Senha'] = f"'{n_senha}"
                        df_users_adm.at[idx, 'Nivel_Acesso'] = n_nivel
                        salvar_novo_usuario(df_users_adm)
                        st.success("✅ Credencial atualizada!"); time.sleep(1); st.rerun()
                    if st.form_submit_button("🗑️ Revogar Acesso Permanentemente"):
                        salvar_novo_usuario(df_users_adm[df_users_adm['Usuario'] != usr_editar])
                        st.success("✅ Acesso excluído!"); time.sleep(1); st.rerun()
        
        with tab3: 
            st.markdown("### Log de Usuários do Sistema")
            st.dataframe(df_users_adm, use_container_width=True)

        with tab4:
            st.markdown("### 🧪 Central de Simulação B2B")
            st.info("Gera 500 registros clinicamente realistas para preencher o Dashboard e a aba Analytics (ideal para demonstrar o sistema a clientes sem usar dados reais).")
            if st.button("🚀 INJETAR 500 LAUDOS SINTÉTICOS", use_container_width=True):
                df_novos_mock = gerar_dados_teste_premium()
                df_atual = conn.read(worksheet="Página1", ttl=0).dropna(how="all")
                salvar_dados(pd.concat([df_atual, df_novos_mock]))
                st.success("✅ Base corporativa injetada no Data Lake!")
                time.sleep(1.5); st.rerun()
            
            if not df_mock.empty:
                st.markdown("---")
                df_mock_pos = df_mock[df_mock['Resultado'] == 'Positivo'].copy()
                k1, k2, k3 = st.columns(3)
                vol_total = int(len(df_mock))
                vol_pos = int(len(df_mock_pos))
                k1.metric("Volume Simulado", f"{vol_total:,}".replace(",", "."))
                k2.metric("Positivados", f"{vol_pos:,}".replace(",", "."))
                k3.metric("Taxa de Positividade", f"{(vol_pos/vol_total)*100:.1f}%")
            else:
                st.warning("Banco simulado ocioso. Inicie a injeção.")
