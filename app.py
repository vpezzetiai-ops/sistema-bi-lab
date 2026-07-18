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
# CONFIGURAÇÕES INICIAIS
# ==========================================
st.set_page_config(page_title="S.I.B.C.", layout="wide", initial_sidebar_state="expanded")

COR_POSITIVO = '#f43f5e'
COR_NEGATIVO = '#3b82f6'
UNIDADES_OFICIAIS = ["1 - Serra Negra", "3 - AME", "4 - Amparo Unidade 4", "5 - Monte Alegre", "6 - Lindóia", "9 - Cenam", "10 - Amparo Unidade BPA", "12 - Águas de Lindóia", "Sede / Sem Unidade"]

def get_base64_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f: return base64.b64encode(f.read()).decode()
    return None

# ==========================================
# OCULTAR ITENS DO STREAMLIT E RESETAR MARGENS
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    * { font-family: 'Inter', sans-serif !important; }
    
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden !important;}
    
    .block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; max-width: 100% !important; }
    
    /* TEMA GERAL */
    .stApp { background-color: #0b1120 !important; color: #f8fafc !important; }
    section[data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #1e293b !important; }
    section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MOTOR DE BANCO DE DADOS E REGEX (CORRIGIDO)
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
    if pd.isna(material): return "Não Informado"
    mat_limpo = re.sub(r'\[.*?\]\s*', '', str(material)) # Remove a sigla técnica
    mat_limpo = re.sub(r'[\.\d:]+$', '', mat_limpo) # Remove números perdidos no final
    if not mat_limpo.strip(): return "Não Informado"
    return mat_limpo.strip().title()

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
            linha = {"Data": data_pac, "Código_Paciente": cod_pac, "Idade": "Não Informada", "Sexo": "Não Informado", "Material_Exame": "Não Informado", "Resultado": "Negativo", "Bactéria": "N/A", "Indicados (S)": "", "Resistentes (R)": "", "Unidade": unidade_pac, "Período_Arquivo": periodo_doc}
            
            match_mat = re.search(r'(?:MAT(?:ERIAL)?):\s*(.*?)(?=RES|1:|\.1:|[A-Z]{3}2?:|\n|$)', sub)
            if match_mat: 
                linha["Material_Exame"] = padronizar_material(match_mat.group(1))
            
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

if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'usuario' not in st.session_state: st.session_state['usuario'] = ""
if 'nivel_acesso' not in st.session_state: st.session_state['nivel_acesso'] = "Visualizador"
if 'unidades_permitidas' not in st.session_state: st.session_state['unidades_permitidas'] = "Todas"

# ==========================================
# 5. TELA DE LOGIN (NOVO DESIGN: RETANGULAR E ELEGANTE)
# ==========================================
if not st.session_state['logado']:
    
    video_fundo_b64 = get_base64_file(ARQUIVO_VIDEO_FUNDO)
    if video_fundo_b64:
        st.markdown(f'''<video autoplay loop muted playsinline style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -999; object-fit: cover; filter: brightness(0.4) contrast(1.1);"><source src="data:video/mp4;base64,{video_fundo_b64}" type="video/mp4"></video>''', unsafe_allow_html=True)

    st.markdown("""
    <style>
    .login-container {
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        height: 100vh; width: 100%; position: absolute; top: 0; left: 0;
    }
    
    /* CARTÃO RETANGULAR MODERNO */
    [data-testid="stForm"] {
        width: 450px !important; border-radius: 12px !important; 
        background: rgba(11, 17, 32, 0.75) !important;
        backdrop-filter: blur(15px) !important; -webkit-backdrop-filter: blur(15px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.2) !important;
        box-shadow: 0px 20px 40px rgba(0,0,0,0.8) !important;
        padding: 40px !important; z-index: 10; margin: 0 auto;
    }
    
    [data-testid="stForm"] label, [data-testid="stForm"] p { color: #e2e8f0 !important; font-weight: 600; font-size: 14px;}
    
    input[type="text"], input[type="password"] {
        background-color: rgba(0, 0, 0, 0.5) !important; color: white !important; -webkit-text-fill-color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important; border-radius: 6px !important; padding: 12px !important;
        font-family: 'Inter', sans-serif !important; width: 100% !important; transition: 0.3s;
    }
    input[type="text"]:focus, input[type="password"]:focus { border-color: #3b82f6 !important; box-shadow: 0 0 10px rgba(59, 130, 246, 0.5) !important;}
    
    [data-testid="stFormSubmitButton"] button {
        background: #2563eb !important; color: white !important;
        border: none !important; border-radius: 6px !important; padding: 12px 0 !important;
        font-weight: 800 !important; font-size: 14px !important; letter-spacing: 1px;
        width: 100% !important; transition: 0.3s; margin-top: 20px;
    }
    [data-testid="stFormSubmitButton"] button:hover { background: #1d4ed8 !important; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-container">', unsafe_allow_html=True)

    # LOGO DO LABORATÓRIO (BEM MAIOR E VISÍVEL)
    logo_b64 = get_base64_file(ARQUIVO_LOGO_LOGIN)
    if logo_b64:
        st.markdown(f'''<div style="text-align: center; margin-bottom: 30px; z-index: 100;"><img src="data:image/png;base64,{logo_b64}" style="width: 250px; filter: drop-shadow(0px 4px 10px rgba(0,0,0,0.8));"></div>''', unsafe_allow_html=True)

    # FORMULÁRIO CENTRAL
    with st.form(key="login_form", clear_on_submit=False):
        st.markdown("""
        <h2 style='text-align: center; color:#ffffff !important; font-weight: 800; margin-bottom: 25px; font-size: 24px;'>
            S.I.B.C.<br>
            <span style="font-size: 12px; color: #94a3b8; font-weight: 400; letter-spacing: 1px;">SISTEMA INTEGRADO DE BIOLOGIA COMPUTACIONAL</span>
        </h2>
        """, unsafe_allow_html=True)
        
        usuario_input = st.text_input("Identificação do Usuário:")
        senha_input = st.text_input("Senha de Acesso:", type="password")
        submit_button = st.form_submit_button("Acessar Sistema")
        
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

    # ASSINATURA NA BASE (BEM MAIOR)
    assinatura_b64 = get_base64_file(ARQUIVO_ASSINATURA)
    if assinatura_b64:
        st.markdown(f'''<div style="text-align: center; margin-top: 40px; z-index: 100;"><img src="data:image/png;base64,{assinatura_b64}" style="height: 60px; filter: drop-shadow(0px 2px 5px rgba(0,0,0,0.8)); opacity: 0.9;"></div>''', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==========================================
# 6. SISTEMA INTERNO E PDF (CSS DE IMPRESSÃO CORRIGIDO)
# ==========================================
else:

    st.markdown(f"""
        <style>
        div[data-testid="metric-container"] {{ background: #1e293b !important; border-left: 4px solid #3b82f6 !important; padding: 20px !important; border-radius: 8px !important; box-shadow: 0 4px 6px rgba(0,0,0,0.3) !important; }}
        div[data-testid="metric-container"] label {{ color: #94a3b8 !important; font-size: 14px !important;}}
        div[data-testid="metric-container"] div {{ color: white !important; }}
        
        /* 🔥 PDF: FORÇA BRUTA DEFINITIVA PARA RELATÓRIO PROFISSIONAL 🔥 */
        @media print {{
            @page {{ size: A4 landscape !important; margin: 10mm !important; }}
            
            /* Remove fundos escuros e força branco para economizar tinta e ficar legível */
            body, html, .stApp, .main, .block-container, div[data-testid="stAppViewContainer"] {{ 
                background-color: white !important; background: white !important; 
                color: black !important; display: block !important; height: auto !important; max-height: none !important; position: relative !important; overflow: visible !important;
            }}
            
            h1, h2, h3, h4, p, label, div, span {{ color: black !important; text-shadow: none !important; box-shadow: none !important; }}
            
            /* Esconde menus e botões */
            [data-testid="stSidebar"], header, .stButton, [data-testid="stToolbar"], button, input, select, .stMultiSelect, form {{ display: none !important; }}
            
            /* Quebra de colunas ordenada */
            div[data-testid="column"] {{ width: 100% !important; max-width: 100% !important; flex: 0 0 100% !important; display: block !important; margin-bottom: 20px !important; page-break-inside: avoid !important; }}
            
            /* TRAVA O TAMANHO DOS GRÁFICOS PLOTLY (Evita barras gigantes) */
            .js-plotly-plot, .plotly, .user-select-none.svg-container {{ width: 100% !important; max-width: 800px !important; max-height: 400px !important; margin: 0 auto !important; page-break-inside: avoid !important; }}
            
            /* TABELA CLARA E LEGÍVEL NO PDF */
            .stDataFrame, .stDataFrame > div, .stDataFrame > div > div, table {{ height: auto !important; max-height: none !important; overflow: visible !important; width: 100% !important; display: table !important; }}
            th {{ background-color: #f1f5f9 !important; color: black !important; border: 1px solid #cbd5e1 !important; font-weight: bold !important; padding: 8px !important; }}
            td {{ border: 1px solid #cbd5e1 !important; padding: 8px !important; color: black !important; background-color: white !important; white-space: normal !important; word-wrap: break-word !important; }}
            
            /* Métricas adaptadas pro branco */
            div[data-testid="metric-container"] {{ background: white !important; border: 1px solid #cbd5e1 !important; border-left: 5px solid #3b82f6 !important; padding: 10px !important; page-break-inside: avoid !important; margin-bottom:10px !important;}}
            div[data-testid="metric-container"] div {{ color: black !important; }}
            div[data-testid="metric-container"] label {{ color: #475569 !important; font-weight: bold !important;}}
        }}
        </style>
    """, unsafe_allow_html=True)

    st.components.v1.html("""
        <script>function doPrint() { window.parent.print(); }</script>
        <button onclick="doPrint()" style="background: #2563eb; color:white; padding:12px 20px; border:none; border-radius:5px; cursor:pointer; font-weight:bold; width:100%; font-family: sans-serif; box-shadow: 0px 4px 6px rgba(0,0,0,0.2);">🖨️ Exportar Relatório em PDF</button>
    """, height=50)

    df_todos_dados = carregar_dados_salvos()
    df_reais = pd.DataFrame()

    if not df_todos_dados.empty:
        df_todos_dados['Data_Obj'] = pd.to_datetime(df_todos_dados['Data'], format="%d/%m/%Y", errors='coerce')
        df_todos_dados['Mês/Ano'] = df_todos_dados['Data_Obj'].dt.strftime('%m/%Y').fillna('Desconhecido')
        unid_perm = st.session_state.get('unidades_permitidas', 'Todas')
        if unid_perm != "Todas" and st.session_state['usuario'] != "vhpezzeti":
            df_todos_dados = df_todos_dados[df_todos_dados['Unidade'].isin([u.strip() for u in unid_perm.split(",")])]
        df_reais = df_todos_dados[df_todos_dados['Período_Arquivo'] != 'Gerado Demo']

    # ==========================================
    # LOGO LATERAL (LIMPO, SEM EFEITOS EXAGERADOS)
    # ==========================================
    logo_prog_b64 = get_base64_file(ARQUIVO_LOGO_PROGRAMA)
    if logo_prog_b64:
        st.sidebar.markdown(f'''
            <div style="display: flex; justify-content: center; margin-bottom: 20px;">
                <img src="data:image/png;base64,{logo_prog_b64}" style="width: 130px;">
            </div>
        ''', unsafe_allow_html=True)
    
    st.sidebar.markdown(f"👤 **{st.session_state['usuario'].upper()}**")
    st.sidebar.markdown(f"🛡️ Nível: {st.session_state.get('nivel_acesso', '')}")
    st.sidebar.markdown("---")

    opcoes_menu = ["📊 Painel Principal", "📈 Análise e Tendências"]
    if st.session_state.get('nivel_acesso') in ["Operador", "Administrador"] or st.session_state['usuario'] == "vhpezzeti":
        opcoes_menu.append("📂 Carregar Laudos")
    if st.session_state.get('nivel_acesso') == "Administrador" or st.session_state['usuario'] == "vhpezzeti":
        opcoes_menu.append("⚙️ Painel Administrativo")

    menu = st.sidebar.radio("Navegação do Sistema", opcoes_menu)
    
    # ========================================================
    # FILTROS SEM TRAVAMENTO (DENTRO DE UM FORMULÁRIO)
    # ========================================================
    df_f = pd.DataFrame()

    if menu in ["📊 Painel Principal", "📈 Análise e Tendências"] and not df_reais.empty:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🎛️ Filtros de Análise")
        
        meses_disp = sorted(list(df_reais[df_reais['Mês/Ano'] != 'Desconhecido']['Mês/Ano'].unique()))
        unid_disp = sorted(list(df_reais['Unidade'].unique()))
        exame_disp = sorted(list(df_reais['Material_Exame'].unique()))
        
        with st.sidebar.form("form_filtros"):
            meses_sel = st.multiselect("Mês/Ano", meses_disp, default=meses_disp)
            unid_sel = st.multiselect("Unidade", unid_disp, default=unid_disp)
            exame_sel = st.multiselect("Material", exame_disp, default=exame_disp)
            st.form_submit_button("Aplicar Filtros ✔️")
        
        df_f = df_reais[df_reais['Mês/Ano'].isin(meses_sel) & df_reais['Unidade'].isin(unid_sel) & df_reais['Material_Exame'].isin(exame_sel)]

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Encerrar Sessão", use_container_width=True):
        st.session_state['logado'] = False
        st.rerun()

    # ========================================================
    # TELA 1: PAINEL PRINCIPAL
    # ========================================================
    if menu == "📊 Painel Principal":
        st.title("Monitoramento Clínico Operacional")
        
        if df_reais.empty: 
            st.info("O sistema está vazio. Carregue laudos em PDF para gerar o relatório.")
        elif df_f.empty: 
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
        else:
            t_total = len(df_f)
            t_pos = len(df_f[df_f['Resultado'] == 'Positivo'])
            t_neg = len(df_f[df_f['Resultado'] == 'Negativo'])
            pct_pos = (t_pos / t_total * 100) if t_total > 0 else 0
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Volume Analisado", t_total)
            m2.metric("Laudos Positivos", t_pos, delta=f"{pct_pos:.1f}% Positividade", delta_color="inverse")
            m3.metric("Controle Negativo", t_neg, delta=f"{100-pct_pos:.1f}%", delta_color="normal")
            m4.metric("Média Mensal", round(t_total / max(len(meses_sel) if 'meses_sel' in locals() else 1, 1), 1))
            
            df_pos = df_f[df_f['Resultado'] == 'Positivo']
            if not df_pos.empty:
                st.markdown("---")
                g1, g2 = st.columns(2)
                with g1:
                    st.markdown("#### Proporção Diagnóstica")
                    fig1 = px.pie(df_f, names='Resultado', hole=0.5, color='Resultado', color_discrete_map={'Positivo': COR_POSITIVO, 'Negativo': COR_NEGATIVO}, template="plotly_dark")
                    fig1.update_traces(textposition='inside', textinfo='percent+label')
                    fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig1, use_container_width=True)
                with g2:
                    st.markdown("#### Patógenos Identificados")
                    df_bact = df_pos['Bactéria'].value_counts().reset_index()
                    fig2 = px.bar(df_bact, y='Bactéria', x='count', text='count', orientation='h', template="plotly_dark", color='count', color_continuous_scale="Blues")
                    fig2.update_traces(textposition='outside')
                    fig2.update_layout(yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=0, b=0, l=0, r=0), xaxis_title="")
                    st.plotly_chart(fig2, use_container_width=True)

                st.markdown("#### Base de Dados - Perfil Crítico de Pacientes")
                st.dataframe(df_pos[['Data', 'Código_Paciente', 'Unidade', 'Material_Exame', 'Bactéria', 'Indicados (S)', 'Resistentes (R)']], use_container_width=True, hide_index=True)

    # ========================================================
    # TELA 2: ANÁLISE E TENDÊNCIAS
    # ========================================================
    elif menu == "📈 Análise e Tendências":
        st.title("Análise e Tendências Hospitalares")
        
        if df_reais.empty:
            st.info("Sem dados suficientes para análise.")
        elif df_f.empty:
            st.warning("Nenhum dado encontrado.")
        else:
            df_pos_comp = df_f[df_f['Resultado'] == 'Positivo'].copy()
            if not df_pos_comp.empty:
                b_top = df_pos_comp['Bactéria'].value_counts().idxmax()
                exame_top = df_pos_comp['Material_Exame'].value_counts().idxmax()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Bactéria mais Frequente", b_top)
                c2.metric("Material mais Crítico", exame_top)
                c3.metric("Total de Infecções", f"{len(df_pos_comp):,}".replace(",", "."))
                
                st.markdown("---")
                
                col_g1, col_g2 = st.columns([1.5, 1])
                with col_g1:
                    st.markdown("#### Evolução de Casos Positivos")
                    df_pos_comp['Data_Obj'] = pd.to_datetime(df_pos_comp['Data'], format="%d/%m/%Y", errors='coerce')
                    linha_tempo = df_pos_comp.dropna(subset=['Data_Obj']).groupby(df_pos_comp['Data_Obj'].dt.to_period("W")).size().reset_index(name='Casos')
                    linha_tempo['Data_Obj'] = linha_tempo['Data_Obj'].dt.to_timestamp()
                    if not linha_tempo.empty:
                        fig_linha = px.line(linha_tempo, x='Data_Obj', y='Casos', markers=True, template="plotly_dark")
                        fig_linha.update_traces(line=dict(color='#3b82f6', width=3), marker=dict(size=8, color='#3b82f6'))
                        fig_linha.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis_title="", yaxis_title="")
                        st.plotly_chart(fig_linha, use_container_width=True)
                        
                with col_g2:
                    st.markdown("#### Concentração por Unidade")
                    top_unid = df_pos_comp['Unidade'].value_counts().reset_index()
                    fig_unid = px.bar(top_unid, x='count', y='Unidade', orientation='h', text='count', template="plotly_dark", color='count', color_continuous_scale="Reds")
                    fig_unid.update_traces(textposition='inside')
                    fig_unid.update_layout(yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis_title="")
                    st.plotly_chart(fig_unid, use_container_width=True)

    # ========================================================
    # TELA 3: CARREGAR LAUDOS
    # ========================================================
    elif menu == "📂 Carregar Laudos":
        st.title("Processamento de Laudos em PDF")
        
        arq = st.file_uploader("Arraste os documentos aqui", type=['pdf', 'txt'])
        if arq and st.button("Extrair e Salvar", use_container_width=True):
            texto_bruto = ""
            with st.spinner("Processando..."):
                if arq.name.endswith('.pdf'):
                    try:
                        leitor = PyPDF2.PdfReader(arq)
                        for p in leitor.pages: texto_bruto += p.extract_text() + "\n"
                    except Exception as e: st.error(f"Erro no arquivo: {e}")
                else: texto_bruto = arq.read().decode("utf-8")
                
                df_novo = extrair_dados_pdf(texto_bruto)
                if not df_novo.empty:
                    df_atual = conn.read(worksheet="Página1", ttl=0).dropna(how="all")
                    df_combinado = pd.concat([df_atual, df_novo]).drop_duplicates(subset=['Data', 'Código_Paciente', 'Material_Exame', 'Unidade'])
                    salvar_dados(df_combinado)
                    st.success(f"✅ {len(df_novo)} registros salvos.")
                    st.dataframe(df_novo, use_container_width=True)
                else: st.error("Nenhum laudo válido encontrado no texto.")

    # ========================================================
    # TELA 4: PAINEL ADMINISTRATIVO
    # ========================================================
    elif menu == "⚙️ Painel Administrativo":
        st.title("Gestão de Usuários")
        tab1, tab2 = st.tabs(["Usuários e Permissões", "Dados Brutos do Sistema"])
        
        df_users_adm = carregar_usuarios()
        lista_usuarios = df_users_adm['Usuario'].tolist() if not df_users_adm.empty else []

        with tab1:
            with st.form("form_cadastro"):
                st.markdown("#### Novo Acesso")
                c1, c2 = st.columns(2)
                novo_usuario = c1.text_input("Usuário:")
                nova_senha = c2.text_input("Senha:", type="password")
                c3, c4 = st.columns(2)
                novo_nivel = c3.selectbox("Permissão:", ["Visualizador", "Operador", "Administrador"])
                nova_unid = c4.multiselect("Unidades:", UNIDADES_OFICIAIS)
                if st.form_submit_button("Salvar Usuário"):
                    if novo_usuario and nova_senha:
                        if novo_usuario not in lista_usuarios:
                            str_unidades = ", ".join(nova_unid) if nova_unid else "Todas"
                            novo_registro = pd.DataFrame([{"Usuario": novo_usuario, "Senha": f"'{nova_senha}", "Nivel_Acesso": novo_nivel, "Unidades_Permitidas": str_unidades}])
                            salvar_novo_usuario(pd.concat([df_users_adm, novo_registro], ignore_index=True))
                            st.success("Salvo!"); time.sleep(1); st.rerun()

            st.markdown("---")
            usr_editar = st.selectbox("Excluir/Editar Usuário:", [""] + lista_usuarios)
            if usr_editar:
                if st.button("🗑️ Deletar"):
                    salvar_novo_usuario(df_users_adm[df_users_adm['Usuario'] != usr_editar])
                    st.success("Excluído!"); time.sleep(1); st.rerun()

        with tab2:
            st.dataframe(df_users_adm, use_container_width=True)
