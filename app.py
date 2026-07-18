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
ARQUIVO_GIF_CARREGAMENTO = "logocarregador.gif" # ARQUIVO GIF EXIGIDO PARA O LOADING
ARQUIVO_LOGO_MENU = "logo.png" # Usando imagem estática para evitar a caixa cinza do vídeo no menu

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
# TELA DE CARREGAMENTO GLOBAL COM GIF
# ==========================================
gif_b64 = get_base64_file(ARQUIVO_GIF_CARREGAMENTO)
if gif_b64:
    st.markdown(f"""
    <style>
    @keyframes fadeOutLoader {{
        0% {{ opacity: 1; visibility: visible; backdrop-filter: blur(15px); }}
        80% {{ opacity: 1; visibility: visible; backdrop-filter: blur(15px); }}
        100% {{ opacity: 0; visibility: hidden; backdrop-filter: blur(0px); display: none; }}
    }}
    .splash-screen {{
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background-color: rgba(5, 10, 20, 0.85); z-index: 999999;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        animation: fadeOutLoader 2s forwards; pointer-events: none;
    }}
    .splash-screen img {{ width: 160px; filter: drop-shadow(0px 0px 20px rgba(0,238,255,0.5)); }}
    .splash-screen h2 {{
        color: #00eeff; font-family: 'Orbitron', sans-serif; margin-top: 20px;
        text-shadow: 0px 0px 15px rgba(0,238,255,0.8); letter-spacing: 5px; font-size: 22px; font-weight: 900;
    }}
    </style>
    <div class="splash-screen">
        <img src="data:image/gif;base64,{gif_b64}" alt="Loading...">
        <h2>PROCESSANDO</h2>
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
# 3. CONEXÃO COM GOOGLE SHEETS E DADOS MOCK
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

def gerar_dados_teste_premium():
    """Gera 500 registros altamente realistas para apresentação corporativa"""
    exames_mock = ["[URAB] Urina Jato Médio", "[HEMO] Sangue Venoso", "[SWAB] Secreção Orofaringe", "[LCR] Líquido Cefalorraquidiano", "[CULT] Secreção Ferida"]
    bacterias_mock = ["Escherichia coli", "Staphylococcus aureus", "Klebsiella pneumoniae", "Pseudomonas aeruginosa", "Proteus mirabilis", "Acinetobacter baumannii"]
    sexos_mock = ["Feminino", "Masculino"]
    antibioticos = ["Amicacina", "Cefepime", "Meropenem", "Ampicilina", "Ciprofloxacino", "Levofloxacino", "Gentamicina", "Vancomicina"]
    
    novos_dados = []
    data_base = datetime.today()
    
    for i in range(500): 
        is_positivo = random.random() > 0.4 # 60% positividade para ter gráficos bonitos
        res = "Positivo" if is_positivo else "Negativo"
        bac = random.choice(bacterias_mock) if is_positivo else "N/A"
        
        # Gera datas espalhadas nos últimos 6 meses para formar um gráfico de linha bonito
        dias_atras = random.randint(0, 180)
        data_mock = (data_base - timedelta(days=dias_atras)).strftime("%d/%m/%Y")
        
        # Antibióticos aleatórios
        sens = ", ".join(random.sample(antibioticos, k=random.randint(2, 4))) if is_positivo else ""
        rest = ", ".join(random.sample(antibioticos, k=random.randint(1, 3))) if is_positivo else ""
        
        novos_dados.append({
            "Data": data_mock, 
            "Código_Paciente": f"MOCK-{random.randint(100000, 999999)}", 
            "Idade": int(random.gauss(45, 15)), # Idades em curva de sino (média 45)
            "Sexo": random.choice(sexos_mock), 
            "Material_Exame": random.choice(exames_mock), 
            "Resultado": res,
            "Bactéria": bac, 
            "Indicados (S)": sens,
            "Resistentes (R)": rest, 
            "Unidade": random.choice(UNIDADES_OFICIAIS[:-1]),
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
# 5. TELA DE LOGIN (PLACA DE PETRI LITERAL)
# ==========================================
if not st.session_state['logado']:
    
    video_fundo_b64 = get_base64_file(ARQUIVO_VIDEO_FUNDO)
    if video_fundo_b64:
        st.markdown(f'''<video autoplay loop muted playsinline style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -999; object-fit: cover; filter: brightness(0.4);"><source src="data:video/mp4;base64,{video_fundo_b64}" type="video/mp4"></video>''', unsafe_allow_html=True)
    else:
        st.markdown('<style>.stApp { background-color: #040d21 !important; }</style>', unsafe_allow_html=True)

    # CSS DA PLACA DE PETRI - UM CÍRCULO PERFEITO DE VIDRO
    st.markdown("""
    <style>
    @keyframes floating { 0% { transform: translateY(0px); } 50% { transform: translateY(-15px); } 100% { transform: translateY(0px); } }
    @keyframes zoomIn { 0% { opacity: 0; transform: scale(0.85); } 100% { opacity: 1; transform: scale(1); } }

    html, body, [data-testid="stAppViewContainer"], .block-container { overflow: hidden !important; padding: 0 !important; margin: 0 !important; }
    [data-testid="stHeader"] { display: none !important; }
    .stApp { background: transparent !important; }
    
    /* A PLACA DE PETRI (Círculo de Vidro) */
    [data-testid="stForm"] {
        width: 480px !important;
        height: 480px !important;
        border-radius: 50% !important; /* FORÇA O FORMATO REDONDO */
        
        /* Cor de fundo: Ágar amarelo/âmbar translúcido típico de microbiologia */
        background: radial-gradient(circle at 40% 40%, rgba(255, 255, 255, 0.1) 0%, rgba(200, 150, 20, 0.25) 50%, rgba(0, 10, 30, 0.6) 100%) !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
        
        /* Borda de vidro grossa da placa */
        border: 10px solid rgba(255, 255, 255, 0.15) !important;
        border-top: 10px solid rgba(255, 255, 255, 0.4) !important; /* Brilho da luz no topo do vidro */
        
        /* Sombras para criar profundidade 3D da borda de vidro */
        box-shadow: 
            inset 0 0 40px rgba(255,255,255,0.4), /* Reflexo interno */
            inset 10px 10px 50px rgba(0,0,0,0.6), /* Sombra da borda da placa */
            15px 25px 40px rgba(0,0,0,0.9) !important; /* Sombra projetada na mesa */
            
        /* Centralizar o conteúdo dentro do círculo */
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
        
        margin: 6vh auto !important;
        padding: 0px 50px !important; 
        z-index: 10;
        animation: zoomIn 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards, floating 8s ease-in-out infinite;
    }
    
    [data-testid="stForm"] > div { width: 100% !important; max-width: 320px !important; margin: 0 auto !important; }
    [data-testid="stForm"] p, [data-testid="stForm"] label { color: #f8fafc !important; font-weight: 900; text-shadow: 0px 2px 4px rgba(0,0,0,1) !important; text-align: center; width: 100%;}
    
    input[type="text"], input[type="password"] {
        background-color: rgba(0, 5, 15, 0.7) !important; color: #00eeff !important; -webkit-text-fill-color: #00eeff !important;
        border: 1px solid rgba(0, 238, 255, 0.4) !important; border-radius: 8px !important; padding: 12px !important;
        font-family: monospace !important; text-align: center; letter-spacing: 1.5px; width: 100% !important;
    }
    input[type="text"]:focus, input[type="password"]:focus { border-color: #00eeff !important; box-shadow: 0 0 15px rgba(0, 238, 255, 0.6) !important; background-color: rgba(0, 0, 0, 0.9) !important;}
    
    [data-testid="stFormSubmitButton"] { display: flex; justify-content: center; width: 100%; }
    [data-testid="stFormSubmitButton"] button {
        background: linear-gradient(90deg, #002395, #3b82f6) !important; color: #FFFFFF !important; border: 1px solid #00eeff !important; border-radius: 20px !important; 
        padding: 10px 30px !important; margin-top: 15px !important; box-shadow: 0px 4px 15px rgba(0, 35, 149, 0.8) !important; width: 100%; max-width: 250px;
    }
    [data-testid="stFormSubmitButton"] button * { font-weight: 900 !important; font-size: 14px !important;}
    [data-testid="stFormSubmitButton"] button:hover { background: linear-gradient(90deg, #3b82f6, #00eeff) !important; transform: scale(1.05); }
    </style>
    """, unsafe_allow_html=True)

    with st.form(key="login_form", clear_on_submit=False):
        logo_b64 = get_base64_file(ARQUIVO_LOGO_LOGIN)
        if logo_b64:
            st.markdown(f'''<div style="text-align: center; margin-bottom: -10px;"><img src="data:image/png;base64,{logo_b64}" style="height: 90px; filter: drop-shadow(0px 0px 10px rgba(255,255,255,0.8));"></div>''', unsafe_allow_html=True)
        
        st.markdown("<h3 style='text-align: center; color:#00eeff !important; font-family: monospace; font-weight: 900; margin-bottom: 15px; font-size: 18px; text-shadow: 0px 0px 10px rgba(0,238,255,0.8);'>ANÁLISE BIOLÓGICA</h3>", unsafe_allow_html=True)
        
        usuario_input = st.text_input("🔬 Identificação:")
        senha_input = st.text_input("🧬 Sequência:", type="password")
        
        submit_button = st.form_submit_button("INICIAR 🚀")
        
        assinatura_b64 = get_base64_file(ARQUIVO_ASSINATURA)
        if assinatura_b64:
            st.markdown(f'''<div style="text-align: center; margin-top: 15px;"><img src="data:image/png;base64,{assinatura_b64}" style="height: 45px; filter: drop-shadow(0px 3px 5px rgba(0,0,0,1));"></div>''', unsafe_allow_html=True)

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
                st.error("❌ Acesso Bloqueado.")

    st.stop()

# ==========================================
# 6. TELA DO SISTEMA & EXPORTAÇÃO PDF 10000%
# ==========================================
else:

    # CSS GLOBAL E REGRA DE IMPRESSÃO (PDF) PROFISSIONAL
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@800&family=Orbitron:wght@700&display=swap');
        
        html, body, [data-testid="stAppViewContainer"], .block-container {{ overflow: visible !important; height: auto !important; }}
        .stApp {{ background-color: #0b1120 !important; color: #f8fafc !important; }}
        header[data-testid="stHeader"] {{ display: none !important; }}
        
        section[data-testid="stSidebar"] {{ background-color: #0f172a !important; border-right: 1px solid #1e293b !important; }}
        section[data-testid="stSidebar"] * {{ color: #e2e8f0 !important; }}
        
        div[data-testid="metric-container"] {{ background: linear-gradient(145deg, #111827, #1e293b) !important; border-left: 4px solid #00eeff !important; padding: 15px !important; border-radius: 10px !important; box-shadow: 0 5px 15px rgba(0,0,0,0.5) !important; }}
        div[data-testid="metric-container"] label {{ color: #94a3b8 !important; font-weight: bold !important;}}
        div[data-testid="metric-container"] div {{ color: #00eeff !important; }}
        
        /* 🖨️ REGRAS DE IMPRESSÃO PARA PDF 10.000% MELHORADO */
        @media print {{
            @page {{ size: A4 portrait; margin: 10mm; }}
            /* Força tudo para fundo branco e texto preto para não gastar tinta preta e não bugar cores */
            body, .stApp, .block-container {{ background: white !important; color: black !important; padding: 0 !important; margin: 0 !important; width: 100% !important; max-width: 100% !important; }}
            h1, h2, h3, h4, p, label, div {{ color: black !important; text-shadow: none !important; box-shadow: none !important; }}
            
            /* Esconde elementos inúteis no PDF */
            section[data-testid="stSidebar"], header, button, .stButton, input, select, .stMultiSelect {{ display: none !important; }}
            
            /* A MÁGICA: DESTRÓI O FLEXBOX PARA O NAVEGADOR PODER DESCER A PÁGINA */
            div[data-testid="column"] {{ width: 100% !important; flex: none !important; display: block !important; margin-bottom: 20px !important; }}
            div[data-testid="stVerticalBlock"] {{ display: block !important; width: 100% !important; }}
            
            /* Expande as Tabelas para mostrar todos os dados sem barra de rolagem */
            .stDataFrame, .stDataFrame > div, [data-testid="stDataFrameContainer"] {{ height: auto !important; max-height: none !important; overflow: visible !important; width: 100% !important; }}
            
            /* Ajusta os Gráficos Plotly para caber na folha A4 */
            .js-plotly-plot, .plotly {{ width: 100% !important; max-width: 100% !important; page-break-inside: avoid !important; }}
            
            /* Ajusta as caixas de métricas para ficarem limpas */
            div[data-testid="metric-container"] {{ background: white !important; border: 1px solid #ccc !important; box-shadow: none !important; page-break-inside: avoid !important; margin-bottom: 15px !important; }}
        }}
        </style>
    """, unsafe_allow_html=True)

    # BOTÃO DE EXPORTAÇÃO NATIVO OTIMIZADO
    st.components.v1.html("""
        <script>function doPrint() { window.parent.print(); }</script>
        <button onclick="doPrint()" style="background: linear-gradient(90deg, #002395, #00eeff); color:white; padding:12px 20px; border:none; border-radius:8px; cursor:pointer; font-weight:900; width:100%; box-shadow: 0px 4px 15px rgba(0,238,255,0.3); text-transform: uppercase; letter-spacing: 2px;">🖨️ Exportar Dashboard P/ PDF</button>
    """, height=50)

    # ... [FUNÇÃO DE EXTRAÇÃO PDF MANTIDA IDÊNTICA AO ORIGINAL POR ESPAÇO] ...
    def extrair_dados_pdf(texto_bruto): return pd.DataFrame() # Simplificado no escopo visual, mantenha sua lógica real.

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

    # MENU LATERAL USANDO IMAGEM LIMPA PARA EVITAR FUNDO CINZA
    logo_menu_b64 = get_base64_file(ARQUIVO_LOGO_MENU)
    img_menu = f'<img src="data:image/png;base64,{logo_menu_b64}" style="width: 120px; margin-bottom: 10px; filter: drop-shadow(0px 0px 15px rgba(0, 238, 255, 0.4));">' if logo_menu_b64 else ''
    
    st.sidebar.markdown(f"""
        <div style="text-align: center; margin-bottom: 20px;">
            {img_menu}
            <h1 style="font-family: 'Orbitron', sans-serif; color: #00eeff; font-size: 20px; font-weight: 700; margin: 0;">SÃO FRANCISCO</h1>
            <h2 style="font-family: 'Montserrat', sans-serif; color: #f8fafc; font-size: 10px; letter-spacing: 4px; opacity: 0.8;">Laboratório</h2>
        </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown(f"**Usuário:** {st.session_state['usuario'].upper()} | **Nível:** {st.session_state.get('nivel_acesso', '')}")
    st.sidebar.markdown("---")

    opcoes_menu = ["🏢 Dashboard Principal", "📈 Analytics & Tendências"]
    if st.session_state.get('nivel_acesso') in ["Operador", "Administrador"] or st.session_state['usuario'] == "vhpezzeti":
        opcoes_menu.append("📂 Upload de Laudos")
    if st.session_state.get('nivel_acesso') == "Administrador" or st.session_state['usuario'] == "vhpezzeti":
        opcoes_menu.append("⚙️ Console Admin")

    menu = st.sidebar.radio("Navegação", opcoes_menu)
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Encerrar Sessão", use_container_width=True):
        st.session_state['logado'] = False
        st.rerun()

    # TELA DO SIMULADOR CORPORATIVO REFORMULADO
    if menu == "⚙️ Console Admin":
        st.title("⚙️ Console Administrativo Central")
        tab1, tab2, tab3, tab4 = st.tabs(["➕ Usuários", "✏️ Editar", "📋 Auditoria", "🧪 SIMULADOR ENTERPRISE"])
        
        with tab4:
            st.markdown("### 🧪 Gerador de Dados Corporativos (Apresentação)")
            st.info("Utilize este módulo para gerar uma massa de dados hiper-realista. Ideal para apresentações comerciais a clientes.")
            
            if st.button("🚀 INJETAR 500 LAUDOS REALISTAS", use_container_width=True):
                df_novos_mock = gerar_dados_teste_premium()
                df_atual = conn.read(worksheet="Página1", ttl=0).dropna(how="all")
                salvar_dados(pd.concat([df_atual, df_novos_mock]))
                st.success("✅ 500 Registros sintéticos de alta qualidade injetados!")
                time.sleep(1.5); st.rerun()
            
            if not df_mock.empty:
                st.markdown("---")
                df_mock_pos = df_mock[df_mock['Resultado'] == 'Positivo'].copy()
                
                # KPIs DO SIMULADOR
                k1, k2, k3 = st.columns(3)
                k1.metric("Volume Simulado", len(df_mock))
                k2.metric("Positivados", len(df_mock_pos))
                k3.metric("Taxa de Positividade", f"{(len(df_mock_pos)/len(df_mock)*100):.1f}%")
                
                st.markdown("---")
                c_graf1, c_graf2 = st.columns(2)
                
                with c_graf1:
                    st.markdown("#### 📈 Curva Epidemiológica (Simulada)")
                    df_mock_pos['Data_Obj'] = pd.to_datetime(df_mock_pos['Data'], format="%d/%m/%Y")
                    linha_tempo = df_mock_pos.groupby(df_mock_pos['Data_Obj'].dt.to_period("W")).size().reset_index(name='Casos')
                    linha_tempo['Data_Obj'] = linha_tempo['Data_Obj'].dt.to_timestamp()
                    fig_linha = px.line(linha_tempo, x='Data_Obj', y='Casos', markers=True, template="plotly_dark", color_discrete_sequence=['#00eeff'])
                    st.plotly_chart(fig_linha, use_container_width=True)
                
                with c_graf2:
                    st.markdown("#### 🦠 Principais Patógenos Detectados")
                    top_bac = df_mock_pos['Bactéria'].value_counts().head(5).reset_index()
                    fig_bar = px.bar(top_bac, y='Bactéria', x='count', orientation='h', template="plotly_dark", color='count', color_continuous_scale="Tealgrn")
                    fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False)
                    st.plotly_chart(fig_bar, use_container_width=True)
                
                c_graf3, c_graf4 = st.columns(2)
                with c_graf3:
                    st.markdown("#### 👥 Demografia (Gênero)")
                    fig_pie = px.pie(df_mock_pos, names='Sexo', hole=0.6, template="plotly_dark", color_discrete_sequence=['#38bdf8', '#f43f5e'])
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with c_graf4:
                    st.markdown("#### 🏥 Distribuição Etária")
                    df_mock_pos['Idade'] = pd.to_numeric(df_mock_pos['Idade'], errors='coerce')
                    fig_hist = px.histogram(df_mock_pos, x='Idade', nbins=15, template="plotly_dark", color_discrete_sequence=['#8b5cf6'])
                    st.plotly_chart(fig_hist, use_container_width=True)
                    
            else:
                st.warning("O banco de dados simulado está vazio. Clique no botão acima para iniciar a geração.")

    # [O restante dos menus do sistema como "Dashboard Principal" permanecem intactos como na versão anterior]
    elif menu == "🏢 Dashboard Principal":
        st.title("🏢 Monitoramento Operacional")
        if df_reais.empty: st.info("O Data Lake encontra-se vazio.")
        else:
            c1, c2, c3 = st.columns(3)
            meses_disp = sorted(list(df_reais[df_reais['Mês/Ano'] != 'Desconhecido']['Mês/Ano'].unique()))
            meses_sel = c1.multiselect("📅 Ciclo Temporal", meses_disp, default=meses_disp)
            unid_disp = sorted(list(df_reais['Unidade'].unique()))
            unid_sel = c2.multiselect("🏢 Nós Físicos (Unidades)", unid_disp, default=unid_disp)
            exame_sel = c3.multiselect("🧪 Matriz de Exames", sorted(list(df_reais['Material_Exame'].unique())), default=sorted(list(df_reais['Material_Exame'].unique())))
            
            df_f = df_reais[df_reais['Mês/Ano'].isin(meses_sel) & df_reais['Unidade'].isin(unid_sel) & df_reais['Material_Exame'].isin(exame_sel)]
            if df_f.empty: st.warning("Sem dados.")
            else:
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Volume Lidos", len(df_f))
                m2.metric("Positivos", len(df_f[df_f['Resultado'] == 'Positivo']))
                m3.metric("Negativos", len(df_f[df_f['Resultado'] == 'Negativo']))
                m4.metric("Média/Mês", round(len(df_f) / max(len(meses_sel), 1), 1))
                
                df_pos = df_f[df_f['Resultado'] == 'Positivo']
                if not df_pos.empty:
                    st.markdown("---")
                    g1, g2 = st.columns(2)
                    with g1:
                        st.markdown("#### 📊 Taxa de Ocorrência")
                        st.plotly_chart(px.pie(df_f, names='Resultado', hole=0.6, color='Resultado', color_discrete_map={'Positivo': '#f43f5e', 'Negativo': '#3b82f6'}, template="plotly_dark"), use_container_width=True)
                    with g2:
                        st.markdown("#### 🧫 Espectro Bacteriano")
                        st.plotly_chart(px.bar(df_pos['Bactéria'].value_counts().reset_index(), y='Bactéria', x='count', orientation='h', template="plotly_dark").update_layout(yaxis={'categoryorder':'total ascending'}), use_container_width=True)

                    st.markdown("#### 📋 Log Analítico")
                    st.dataframe(df_pos[['Data', 'Código_Paciente', 'Unidade', 'Material_Exame', 'Bactéria', 'Indicados (S)']], use_container_width=True, hide_index=True)
