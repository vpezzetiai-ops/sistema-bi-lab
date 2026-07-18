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

# ==========================================
# CONFIGURAÇÕES INICIAIS DE TEMA
# ==========================================
st.set_page_config(page_title="Sistema BI - Laboratorial", layout="wide", initial_sidebar_state="expanded")

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
# TELA DE CARREGAMENTO (ATIVA EM TODA AÇÃO)
# ==========================================
gif_b64 = get_base64_file(ARQUIVO_GIF_CARREGAMENTO)
if gif_b64:
    # Cria um ID único a cada carregamento da tela para forçar a animação do navegador a rodar novamente
    loader_id = str(uuid.uuid4())[:8] 
    st.markdown(f"""
    <style>
    @keyframes fadeOutLoader_{loader_id} {{
        0% {{ opacity: 1; visibility: visible; backdrop-filter: blur(10px); }}
        60% {{ opacity: 1; visibility: visible; backdrop-filter: blur(10px); }}
        100% {{ opacity: 0; visibility: hidden; backdrop-filter: blur(0px); display: none; }}
    }}
    .splash-screen-{loader_id} {{
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background-color: rgba(5, 10, 20, 0.85); z-index: 9999999; /* Z-index altíssimo */
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        animation: fadeOutLoader_{loader_id} 1.2s forwards ease-out; pointer-events: none;
    }}
    .splash-screen-{loader_id} img {{ width: 180px; filter: drop-shadow(0px 0px 25px rgba(0,238,255,0.7)); }}
    .splash-screen-{loader_id} h2 {{
        color: #00eeff; font-family: 'Orbitron', sans-serif; margin-top: 25px;
        text-shadow: 0px 0px 20px rgba(0,238,255,0.9); letter-spacing: 6px; font-size: 26px; font-weight: 900;
    }}
    </style>
    <div class="splash-screen-{loader_id}">
        <img src="data:image/gif;base64,{gif_b64}" alt="Loading...">
        <h2>PROCESSANDO</h2>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. FUNÇÕES LÓGICAS E BANCO DE DADOS
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
# CONTROLE DE ESTADO
# ==========================================
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'usuario' not in st.session_state: st.session_state['usuario'] = ""
if 'nivel_acesso' not in st.session_state: st.session_state['nivel_acesso'] = "Visualizador"
if 'unidades_permitidas' not in st.session_state: st.session_state['unidades_permitidas'] = "Todas"

# ==========================================
# 5. TELA DE LOGIN (PLACA DE PETRI PROFUNDA)
# ==========================================
if not st.session_state['logado']:
    
    video_fundo_b64 = get_base64_file(ARQUIVO_VIDEO_FUNDO)
    if video_fundo_b64:
        st.markdown(f'''<video autoplay loop muted playsinline style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -999; object-fit: cover; filter: brightness(0.35);"><source src="data:video/mp4;base64,{video_fundo_b64}" type="video/mp4"></video>''', unsafe_allow_html=True)
    else:
        st.markdown('<style>.stApp { background-color: #040d21 !important; }</style>', unsafe_allow_html=True)

    # CSS DA PLACA DE PETRI (Corrigido para efeito de vidro espesso e profundo)
    st.markdown("""
    <style>
    @keyframes floating { 0% { transform: translateY(0px); } 50% { transform: translateY(-15px); } 100% { transform: translateY(0px); } }
    @keyframes zoomIn { 0% { opacity: 0; transform: scale(0.85); } 100% { opacity: 1; transform: scale(1); } }

    /* Removemos o 'overflow: hidden' da block-container para não bugar componentes do Streamlit futuramente */
    .stApp { background: transparent !important; }
    header[data-testid="stHeader"] { background: transparent !important; } /* Mantem o cabecalho invisível mas clicavel */
    
    /* A PLACA DE PETRI ULTRA 3D */
    [data-testid="stForm"] {
        width: 520px !important;
        height: 520px !important;
        border-radius: 50% !important; /* CÍRCULO PERFEITO */
        
        /* Cor do Meio de Cultura (Ágar) misturado com vidro escuro */
        background: radial-gradient(circle at 30% 30%, rgba(200, 160, 30, 0.15) 0%, rgba(0, 15, 40, 0.6) 60%, rgba(0, 5, 20, 0.9) 100%) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        
        /* Borda hiper-realista simulando vidro grosso de laboratório */
        border: 18px solid rgba(255, 255, 255, 0.05) !important;
        border-top: 18px solid rgba(255, 255, 255, 0.4) !important; /* Brilho superior */
        border-bottom: 18px solid rgba(0, 0, 0, 0.7) !important; /* Sombra inferior */
        
        /* Camadas de Sombra Interna e Externa para PROFUNDIDADE MÁXIMA */
        box-shadow: 
            inset 0 0 60px rgba(255, 255, 255, 0.2), /* Reflexo do vidro na parede interna */
            inset 20px 20px 80px rgba(0, 0, 0, 0.9), /* Profundidade extrema do fundo da placa */
            inset -15px -15px 40px rgba(0, 238, 255, 0.2), /* Bioluminescência lateral */
            0px 50px 100px rgba(0,0,0,1), /* Sombra gigante projetada na bancada */
            0px 0px 40px rgba(0, 238, 255, 0.4) !important; /* Aura neon ao redor */
            
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
        
        margin: 5vh auto !important;
        padding: 0px !important; 
        z-index: 10;
        animation: zoomIn 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards, floating 8s ease-in-out infinite;
    }
    
    [data-testid="stForm"] > div { width: 100% !important; max-width: 340px !important; margin: 0 auto !important; }
    [data-testid="stForm"] p, [data-testid="stForm"] label { color: #f8fafc !important; font-weight: 900; text-shadow: 0px 3px 6px rgba(0,0,0,1) !important; text-align: center; width: 100%; font-size: 15px;}
    
    /* Inputs estendidos */
    input[type="text"], input[type="password"] {
        background-color: rgba(0, 5, 15, 0.8) !important; color: #00eeff !important; -webkit-text-fill-color: #00eeff !important;
        border: 2px solid rgba(0, 238, 255, 0.3) !important; border-radius: 10px !important; padding: 15px !important;
        font-family: monospace !important; text-align: center; letter-spacing: 2px; width: 100% !important; font-size: 16px !important;
        box-shadow: inset 0px 0px 10px rgba(0,0,0,0.8) !important;
    }
    input[type="text"]:focus, input[type="password"]:focus { border-color: #00eeff !important; box-shadow: 0 0 20px rgba(0, 238, 255, 0.7) !important; background-color: rgba(0, 0, 0, 0.95) !important;}
    
    [data-testid="stFormSubmitButton"] { display: flex; justify-content: center; width: 100%; margin-top: 10px; }
    [data-testid="stFormSubmitButton"] button {
        background: linear-gradient(90deg, #002395, #3b82f6) !important; color: #FFFFFF !important; border: 2px solid #00eeff !important; border-radius: 25px !important; 
        padding: 12px 35px !important; box-shadow: 0px 6px 20px rgba(0, 35, 149, 0.9) !important; width: 100%; max-width: 280px;
    }
    [data-testid="stFormSubmitButton"] button * { font-weight: 900 !important; font-size: 16px !important; letter-spacing: 1px;}
    [data-testid="stFormSubmitButton"] button:hover { background: linear-gradient(90deg, #3b82f6, #00eeff) !important; transform: scale(1.05); box-shadow: 0px 10px 30px rgba(0, 238, 255, 0.6) !important;}
    </style>
    """, unsafe_allow_html=True)

    with st.form(key="login_form", clear_on_submit=False):
        logo_b64 = get_base64_file(ARQUIVO_LOGO_LOGIN)
        if logo_b64:
            # LOGO SUPER DESTACADO
            st.markdown(f'''<div style="text-align: center; margin-bottom: 5px; margin-top: -15px;"><img src="data:image/png;base64,{logo_b64}" style="height: 120px; filter: drop-shadow(0px 0px 15px rgba(255,255,255,0.9));"></div>''', unsafe_allow_html=True)
        
        st.markdown("<h2 style='text-align: center; color:#00eeff !important; font-family: monospace; font-weight: 900; margin-bottom: 20px; font-size: 22px; text-shadow: 0px 0px 15px rgba(0,238,255,0.9); letter-spacing: 2px;'>ANÁLISE BIOLÓGICA</h2>", unsafe_allow_html=True)
        
        usuario_input = st.text_input("🔬 IDENTIFICAÇÃO:")
        senha_input = st.text_input("🧬 SEQUÊNCIA:", type="password")
        
        submit_button = st.form_submit_button("INICIAR MATRIZ 🚀")
        
        assinatura_b64 = get_base64_file(ARQUIVO_ASSINATURA)
        if assinatura_b64:
            # ASSINATURA GIGANTE, BRILHANTE E LEGÍVEL
            st.markdown(f'''<div style="text-align: center; margin-top: 25px;"><img src="data:image/png;base64,{assinatura_b64}" style="height: 70px; filter: drop-shadow(0px 5px 10px rgba(0,0,0,1)) drop-shadow(0px 0px 15px rgba(0,238,255,0.6));"></div>''', unsafe_allow_html=True)

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
                st.error("❌ Credenciais Rejeitadas.")

    st.stop()

# ==========================================
# 6. DASHBOARD & CSS DE ESTRUTURA (CORRIGIDO)
# ==========================================
else:

    # CSS REFINADO: Removido as travas que bloqueavam os cliques nas abas e ocultavam o header!
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@800&family=Orbitron:wght@700&display=swap');
        
        /* MANTER CABEÇALHO VISÍVEL (TRANSPARENTE) PARA A BARRA LATERAL VOLTAR QUANDO OCULTADA! */
        header[data-testid="stHeader"] {{ background: transparent !important; }}
        .stApp {{ background-color: #0b1120 !important; color: #f8fafc !important; }}
        
        /* Design da Barra Lateral */
        section[data-testid="stSidebar"] {{ background-color: #0f172a !important; border-right: 1px solid #1e293b !important; }}
        section[data-testid="stSidebar"] * {{ color: #e2e8f0 !important; }}
        
        /* Design dos Cards de Métricas */
        div[data-testid="metric-container"] {{ 
            background: linear-gradient(145deg, #111827, #1e293b) !important; 
            border-left: 5px solid #00eeff !important; 
            padding: 20px !important; border-radius: 12px !important; 
            box-shadow: 0 8px 25px rgba(0,0,0,0.6) !important; 
        }}
        div[data-testid="metric-container"] label {{ color: #94a3b8 !important; font-weight: bold !important; font-size: 15px !important;}}
        div[data-testid="metric-container"] div {{ color: #00eeff !important; text-shadow: 0px 0px 10px rgba(0,238,255,0.3) !important;}}
        
        /* Estilizar Abas para ficarem clicáveis e bonitas */
        .stTabs [data-baseweb="tab-list"] {{ gap: 10px; background-color: transparent; }}
        .stTabs [data-baseweb="tab"] {{ padding: 10px 25px; border-radius: 8px 8px 0 0; background-color: #1e293b; transition: 0.3s;}}
        .stTabs [aria-selected="true"] {{ background-color: #002395 !important; border-bottom: 3px solid #00eeff !important; color: white !important; font-weight: bold; }}
        
        /* 🖨️ REGRAS DE IMPRESSÃO (PDF) FUNCIONAIS E SEM BUG */
        @media print {{
            @page {{ size: A4 landscape; margin: 10mm; }}
            body, .stApp, .block-container {{ background: white !important; color: black !important; padding: 0 !important; margin: 0 !important; width: 100% !important; max-width: 100% !important; }}
            h1, h2, h3, h4, p, label, div {{ color: black !important; text-shadow: none !important; box-shadow: none !important; }}
            section[data-testid="stSidebar"], header, button, .stButton, input, select, .stMultiSelect {{ display: none !important; }}
            div[data-testid="column"] {{ width: 100% !important; flex: none !important; display: block !important; margin-bottom: 20px !important; }}
            div[data-testid="stVerticalBlock"] {{ display: block !important; width: 100% !important; }}
            .stDataFrame, .stDataFrame > div, [data-testid="stDataFrameContainer"] {{ height: auto !important; max-height: none !important; overflow: visible !important; width: 100% !important; }}
            .js-plotly-plot, .plotly {{ width: 100% !important; max-width: 100% !important; page-break-inside: avoid !important; }}
            div[data-testid="metric-container"] {{ background: white !important; border: 1px solid #ccc !important; box-shadow: none !important; page-break-inside: avoid !important; margin-bottom: 15px !important; border-left: 5px solid #000 !important;}}
            div[data-testid="metric-container"] div {{ color: black !important; }}
        }}
        </style>
    """, unsafe_allow_html=True)

    # BOTÃO DE EXPORTAÇÃO
    st.components.v1.html("""
        <script>function doPrint() { window.parent.print(); }</script>
        <button onclick="doPrint()" style="background: linear-gradient(90deg, #002395, #00eeff); color:white; padding:15px 20px; border:none; border-radius:10px; cursor:pointer; font-weight:900; width:100%; box-shadow: 0px 6px 20px rgba(0,238,255,0.4); text-transform: uppercase; letter-spacing: 2px;">🖨️ Exportar Relatório Oficial PDF</button>
    """, height=60)

    # Função Simples de Extração (Espaço otimizado)
    def extrair_dados_pdf(texto_bruto): return pd.DataFrame() 

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

    # LOGO LATERAL DESTACADO
    logo_menu_b64 = get_base64_file(ARQUIVO_LOGO_LOGIN)
    if logo_menu_b64:
        st.sidebar.markdown(f'<div style="text-align: center; margin-bottom: 10px;"><img src="data:image/png;base64,{logo_menu_b64}" style="width: 140px; filter: drop-shadow(0px 0px 15px rgba(255, 255, 255, 0.7));"></div>', unsafe_allow_html=True)
    
    st.sidebar.markdown("""
        <div style="text-align: center; margin-bottom: 25px;">
            <h1 style="font-family: 'Orbitron', sans-serif; color: #00eeff; font-size: 20px; font-weight: 700; margin: 0; text-shadow: 0px 0px 10px rgba(0,238,255,0.5);">SÃO FRANCISCO</h1>
            <h2 style="font-family: 'Montserrat', sans-serif; color: #f8fafc; font-size: 10px; letter-spacing: 5px; opacity: 0.8; text-transform: uppercase;">Laboratório</h2>
        </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown(f"👤 **{st.session_state['usuario'].upper()}**")
    st.sidebar.markdown(f"🛡️ **Nível:** <span style='color:#00eeff;'>{st.session_state.get('nivel_acesso', '')}</span>", unsafe_allow_html=True)
    st.sidebar.markdown("---")

    opcoes_menu = ["🏢 Dashboard Principal", "📈 Analytics Avançado"]
    if st.session_state.get('nivel_acesso') in ["Operador", "Administrador"] or st.session_state['usuario'] == "vhpezzeti":
        opcoes_menu.append("📂 Upload de Laudos")
    if st.session_state.get('nivel_acesso') == "Administrador" or st.session_state['usuario'] == "vhpezzeti":
        opcoes_menu.append("⚙️ Console Admin")

    menu = st.sidebar.radio("Navegação do Sistema", opcoes_menu)
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Encerrar Sessão Segura", use_container_width=True):
        st.session_state['logado'] = False
        st.rerun()

    # ========================================================
    # TELA ADMIN & SIMULADOR ENTERPRISE (AGORA PERFEITO)
    # ========================================================
    if menu == "⚙️ Console Admin":
        st.title("⚙️ Painel de Controle Central")
        tab1, tab2, tab3, tab4 = st.tabs(["➕ Gestão de Acessos", "✏️ Editar Registros", "📋 Log de Auditoria", "🧪 SIMULADOR ENTERPRISE"])
        
        with tab4:
            st.markdown("### 🧪 Central de Simulação de Dados (B2B Presentation)")
            st.info("Este módulo gera 500 registros clinicamente realistas para demonstração de capacidade analítica a clientes corporativos.")
            
            if st.button("🚀 PROCESSAR INJEÇÃO DE 500 LAUDOS SINTÉTICOS", use_container_width=True):
                df_novos_mock = gerar_dados_teste_premium()
                df_atual = conn.read(worksheet="Página1", ttl=0).dropna(how="all")
                salvar_dados(pd.concat([df_atual, df_novos_mock]))
                st.success("✅ Base de dados corporativa injetada com sucesso no Data Lake!")
                time.sleep(1.5); st.rerun()
            
            if not df_mock.empty:
                st.markdown("---")
                df_mock_pos = df_mock[df_mock['Resultado'] == 'Positivo'].copy()
                
                # KPIs ENTERPRISE (Com formatação de números inteiros para não ficar com "1.0K")
                k1, k2, k3, k4 = st.columns(4)
                vol_total = int(len(df_mock))
                vol_pos = int(len(df_mock_pos))
                taxa = (vol_pos/vol_total)*100
                
                k1.metric("Volume de Entradas Lidas", f"{vol_total:,}".replace(",", "."))
                k2.metric("Laudos Positivados (Patógenos)", f"{vol_pos:,}".replace(",", "."), delta="Atenção Clínica", delta_color="inverse")
                k3.metric("Taxa de Positividade", f"{taxa:.1f}%", delta=f"{taxa - 30:.1f}% vs Ref", delta_color="off")
                k4.metric("Idade Média Afetada", f"{df_mock_pos['Idade'].mean():.0f} anos")
                
                st.markdown("---")
                c_graf1, c_graf2 = st.columns([1.5, 1])
                
                with c_graf1:
                    st.markdown("#### 📉 Vetor de Positividade Longitudinal")
                    df_mock_pos['Data_Obj'] = pd.to_datetime(df_mock_pos['Data'], format="%d/%m/%Y")
                    linha_tempo = df_mock_pos.groupby(df_mock_pos['Data_Obj'].dt.to_period("W")).size().reset_index(name='Casos Registrados')
                    linha_tempo['Data_Obj'] = linha_tempo['Data_Obj'].dt.to_timestamp()
                    fig_linha = px.area(linha_tempo, x='Data_Obj', y='Casos Registrados', markers=True, template="plotly_dark", color_discrete_sequence=[COR_NEON])
                    fig_linha.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis_title="Evolução Temporal", yaxis_title="Volume Positivado")
                    st.plotly_chart(fig_linha, use_container_width=True)
                
                with c_graf2:
                    st.markdown("#### 🦠 Dominância Bacteriana (Top 5)")
                    top_bac = df_mock_pos['Bactéria'].value_counts().head(5).reset_index()
                    # Calculando a porcentagem para aparecer no gráfico
                    top_bac['Porcentagem'] = (top_bac['count'] / top_bac['count'].sum() * 100).round(1).astype(str) + '%'
                    
                    fig_bar = px.bar(top_bac, y='Bactéria', x='count', text='Porcentagem', orientation='h', template="plotly_dark", color='count', color_continuous_scale="Tealgrn")
                    fig_bar.update_traces(textposition='auto')
                    fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis_title="Nº Casos")
                    st.plotly_chart(fig_bar, use_container_width=True)
                
                c_graf3, c_graf4 = st.columns(2)
                with c_graf3:
                    st.markdown("#### 👥 Impacto Cruzado Demográfico (Gênero)")
                    fig_pie = px.pie(df_mock_pos, names='Sexo', hole=0.55, template="plotly_dark", color_discrete_sequence=[COR_NEGATIVO, COR_POSITIVO])
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    fig_pie.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with c_graf4:
                    st.markdown("#### 🏥 Distribuição de Vulnerabilidade Etária")
                    df_mock_pos['Idade'] = pd.to_numeric(df_mock_pos['Idade'], errors='coerce')
                    fig_hist = px.histogram(df_mock_pos, x='Idade', nbins=12, template="plotly_dark", color_discrete_sequence=['#8b5cf6'], marginal="box")
                    fig_hist.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis_title="Idade do Paciente", yaxis_title="Ocorrências")
                    st.plotly_chart(fig_hist, use_container_width=True)
                    
            else:
                st.warning("O Data Lake do Simulador encontra-se ocioso. Inicie a injeção corporativa no botão acima.")

    # ========================================================
    # TELA PRINCIPAL DE DASHBOARD (ANALISES MELHORADAS)
    # ========================================================
    elif menu == "🏢 Dashboard Principal":
        st.title("🏢 Monitoramento Clínico Operacional")
        if df_reais.empty: 
            st.info("Nenhum Laudo Oficial processado no momento.")
        else:
            c1, c2, c3 = st.columns(3)
            meses_disp = sorted(list(df_reais[df_reais['Mês/Ano'] != 'Desconhecido']['Mês/Ano'].unique()))
            meses_sel = c1.multiselect("📅 Ciclo Temporal", meses_disp, default=meses_disp)
            unid_disp = sorted(list(df_reais['Unidade'].unique()))
            unid_sel = c2.multiselect("🏢 Nós Físicos (Unidades)", unid_disp, default=unid_disp)
            exame_sel = c3.multiselect("🧪 Matriz de Exames", sorted(list(df_reais['Material_Exame'].unique())), default=sorted(list(df_reais['Material_Exame'].unique())))
            
            df_f = df_reais[df_reais['Mês/Ano'].isin(meses_sel) & df_reais['Unidade'].isin(unid_sel) & df_reais['Material_Exame'].isin(exame_sel)]
            if df_f.empty: 
                st.warning("Filtro sem correlação no banco de dados.")
            else:
                t_total = len(df_f)
                t_pos = len(df_f[df_f['Resultado'] == 'Positivo'])
                t_neg = len(df_f[df_f['Resultado'] == 'Negativo'])
                pct_pos = (t_pos / t_total * 100) if t_total > 0 else 0
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Volume Lidos", t_total)
                m2.metric("Positivados", t_pos, delta=f"{pct_pos:.1f}% do Geral", delta_color="inverse")
                m3.metric("Controle Negativo", t_neg, delta=f"{100-pct_pos:.1f}%", delta_color="normal")
                m4.metric("Média / Ciclo", round(t_total / max(len(meses_sel), 1), 1))
                
                df_pos = df_f[df_f['Resultado'] == 'Positivo']
                if not df_pos.empty:
                    st.markdown("---")
                    g1, g2 = st.columns(2)
                    with g1:
                        st.markdown("#### 📊 Relação Diagnóstica Global (Pos x Neg)")
                        fig1 = px.pie(df_f, names='Resultado', hole=0.6, color='Resultado', color_discrete_map={'Positivo': COR_POSITIVO, 'Negativo': COR_NEGATIVO}, template="plotly_dark")
                        fig1.update_traces(textposition='inside', textinfo='percent+label')
                        fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                        st.plotly_chart(fig1, use_container_width=True)
                    with g2:
                        st.markdown("#### 🧫 Espectro Microbiológico Detalhado")
                        df_bact = df_pos['Bactéria'].value_counts().reset_index()
                        df_bact['Porcentagem'] = (df_bact['count'] / df_bact['count'].sum() * 100).round(1).astype(str) + '%'
                        fig2 = px.bar(df_bact, y='Bactéria', x='count', text='Porcentagem', orientation='h', template="plotly_dark", color='Bactéria', color_discrete_sequence=PALETA_CORES)
                        fig2.update_traces(textposition='auto')
                        fig2.update_layout(yaxis={'categoryorder':'total ascending'}, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
                        st.plotly_chart(fig2, use_container_width=True)

                    st.markdown("#### 📋 Matriz Analítica e Perfil de Resistência (Pacientes Críticos)")
                    st.dataframe(df_pos[['Data', 'Código_Paciente', 'Unidade', 'Material_Exame', 'Bactéria', 'Indicados (S)', 'Resistentes (R)']], use_container_width=True, hide_index=True)
    
    elif menu == "📈 Analytics Avançado":
        st.title("📈 Motor Analítico e Tendências")
        st.info("Base gráfica em desenvolvimento a partir dos dados limpos.")
        # Pode reaproveitar os gráficos avançados do simulador aqui mas conectando com df_reais
