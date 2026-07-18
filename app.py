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
# 1. CONFIGURAÇÕES INICIAIS E TEMA
# ==========================================
st.set_page_config(page_title="Sistema BI - Laboratorial", layout="wide", initial_sidebar_state="expanded")

COR_AZUL_BIC = '#002395'
COR_CINZA = '#808080'
PALETA_CORES = ['#002395', '#4A69BD', '#708ad4', '#808080', '#A6A6A6', '#C0C0C0', '#d9d9d9']
UNIDADES_OFICIAIS = ["1 - Serra Negra", "3 - AME", "4 - Amparo Unidade 4", "5 - Monte Alegre", "6 - Lindóia", "9 - Cenam", "10 - Amparo Unidade BPA", "12 - Águas de Lindóia", "Sede / Sem Unidade"]

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

def get_base64_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

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
            "Data": data_mock,
            "Código_Paciente": str(random.randint(10000, 99999)),
            "Idade": random.randint(1, 90),
            "Sexo": random.choice(sexos_mock),
            "Material_Exame": random.choice(exames_mock),
            "Resultado": res,
            "Bactéria": bac,
            "Indicados (S)": "Amicacina, Cefepime" if res=="Positivo" else "",
            "Resistentes (R)": "Ampicilina, Penicilina" if res=="Positivo" else "",
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
# 5. TELA DE LOGIN (COM BACKUP BLINDADO)
# ==========================================
if not st.session_state['logado']:
    
    video_b64 = get_base64_file("video_apresentacao.mp4")
    
    # Se houver vídeo, mostra o vídeo. Se falhar, mostra a imagem fotográfica do laboratório.
    if video_b64:
        st.markdown(f'''
        <video autoplay loop muted playsinline style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -999; object-fit: cover; object-position: center; filter: brightness(0.85) contrast(1.15);">
            <source src="data:video/mp4;base64,{video_b64}" type="video/mp4">
        </video>
        ''', unsafe_allow_html=True)
    else:
        st.markdown('''
        <style>
        .stApp {
            background: linear-gradient(rgba(0, 15, 60, 0.7), rgba(0, 15, 60, 0.9)), url("https://images.unsplash.com/photo-1579154204601-01588f351e67?q=80&w=2000&auto=format&fit=crop") no-repeat center center fixed !important;
            background-size: cover !important;
        }
        </style>
        ''', unsafe_allow_html=True)

    st.markdown("""
    <style>
    @keyframes fadeInDown { 0% { opacity: 0; transform: translateY(-50px); } 100% { opacity: 1; transform: translateY(0); } }

    html, body, [data-testid="stAppViewContainer"], .block-container { 
        overflow: hidden !important; padding-top: 0rem !important; padding-bottom: 0rem !important; margin: 0 !important;
    }
    .stApp { background-color: transparent !important; }
    [data-testid="stHeader"] { background: transparent !important; display: none !important; }
    
    [data-testid="stForm"] {
        background: rgba(255, 255, 255, 0.15) !important;
        backdrop-filter: blur(15px) !important;
        -webkit-backdrop-filter: blur(15px) !important;
        border-radius: 20px !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        box-shadow: 0px 15px 35px rgba(0,0,0,0.6) !important;
        padding: 30px 25px 20px 25px !important;
        margin-top: 10vh !important; 
        z-index: 10; max-width: 360px; margin-left: auto; margin-right: auto;
        animation: fadeInDown 1.2s ease-out forwards;
    }
    
    [data-testid="stForm"] p, [data-testid="stForm"] label, [data-testid="stForm"] div { color: #FFFFFF !important; font-weight: 800; text-shadow: 0px 1px 3px rgba(0,0,0,0.8) !important; }
    
    input[type="text"], input[type="password"] {
        background-color: rgba(255, 255, 255, 0.95) !important; color: #111827 !important; -webkit-text-fill-color: #111827 !important;
        border: 1px solid rgba(255, 255, 255, 0.8) !important; border-radius: 8px !important; padding: 12px !important;
    }
    
    [data-testid="stFormSubmitButton"] button {
        background-color: #002395 !important; color: #FFFFFF !important; border: none !important; border-radius: 8px !important; 
        padding: 12px !important; margin-top: 10px !important; box-shadow: 0px 4px 15px rgba(0, 35, 149, 0.6) !important; width: 100%;
    }
    [data-testid="stFormSubmitButton"] button * { color: #FFFFFF !important; font-weight: 900 !important; font-size: 16px !important; text-shadow: none !important;}
    [data-testid="stFormSubmitButton"] button:hover { background-color: #4A69BD !important; transform: scale(1.02); }
    
    hr.custom-divider { border: 0; height: 1px; background: linear-gradient(to right, rgba(255,255,255,0), rgba(255,255,255,0.8), rgba(255,255,255,0)); margin: 20px 0 15px 0; }
    </style>
    """, unsafe_allow_html=True)

    col_vazia_esq, col_login, col_vazia_dir = st.columns([1, 1, 1]) 
    
    with col_login:
        with st.form(key="login_form"):
            st.markdown("<h2 style='text-align: center; color:#FFFFFF !important; font-weight: 900; margin-bottom: 25px; text-shadow: 0px 4px 15px rgba(0,0,0,0.8);'>Sistema BI - Laboratorial</h2>", unsafe_allow_html=True)
            
            usuario_input = st.text_input("👤 Nome de Usuário:")
            senha_input = st.text_input("🔑 Senha de Acesso:", type="password")
            
            submit_button = st.form_submit_button("Fazer Login 🚀", use_container_width=True)
            st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
            
            assinatura_b64 = get_base64_file("assinatura.png")
            if assinatura_b64:
                st.markdown(f'''
                    <div style="text-align: center; padding-bottom: 5px;">
                        <p style="color: #FFFFFF; font-size: 9px; font-weight: 900; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 2px;">Desenvolvido Por</p>
                        <img src="data:image/png;base64,{assinatura_b64}" style="max-height: 45px; max-width: 100%; object-fit: contain; margin: 0 auto; display: block; filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.8));">
                    </div>
                ''', unsafe_allow_html=True)

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
                    st.error("❌ Usuário ou senha incorretos. Acesso negado.")

    st.stop()

# ==========================================
# 6. TELA DO SISTEMA (DASHBOARD) E MÓDULOS
# ==========================================
else:
    # CSS GLOBAL PARA ESTILIZAR O DASHBOARD E FORÇAR PDF PERFEITO
    st.markdown("""
        <style>
        video { display: none !important; }
        html, body, [data-testid="stAppViewContainer"], .block-container { 
            overflow: visible !important; height: auto !important; 
        }
        .stApp { background-image: none !important; background-color: #F4F6F9 !important; animation: none !important;}
        header[data-testid="stHeader"] { display: flex !important; background-color: #F4F6F9 !important;}
        
        /* Estilização Premium dos Cartões (Metrics) */
        div[data-testid="metric-container"] {
            background-color: #FFFFFF !important; border: 1px solid #E5E7EB !important;
            padding: 20px !important; border-radius: 12px !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important; border-left: 6px solid #002395 !important;
        }
        
        div.stButton > button { background-color: #002395 !important; border: none !important; border-radius: 8px !important;}
        div.stButton > button * { color: #FFFFFF !important; font-weight: bold !important; }
        div.stButton > button:hover { background-color: #4A69BD !important; }
        
        /* SOLUÇÃO DEFINITIVA PARA O PDF NÃO CORTAR */
        @media print {
            section[data-testid="stSidebar"] { display: none !important; }
            header[data-testid="stHeader"] { display: none !important; }
            .stApp { background: white !important; }
            div[data-testid="stAppViewBlockContainer"] { padding: 0 !important; max-width: 100% !important; margin: 0 !important; width: 100% !important;}
            iframe { display: none !important; } 
            .js-plotly-plot { page-break-inside: avoid !important; }
        }
        </style>
    """, unsafe_allow_html=True)

    # Botão Injetado via Javascript para imprimir em PDF
    st.components.v1.html("""
        <script>
        function printPDF() { window.parent.print(); }
        </script>
        <button onclick="printPDF()" style="background-color:#002395;color:white;padding:12px 20px;border:none;border-radius:8px;cursor:pointer;font-weight:bold;width:100%;box-shadow: 0px 4px 6px rgba(0,0,0,0.2);">🖨️ Exportar Tela para PDF</button>
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

    # =============== CARREGAR TODOS OS DADOS DA NUVEM ===============
    df_todos_dados = carregar_dados_salvos()
    
    # SEPARAÇÃO DE DADOS (CRÍTICO: PACIENTES MOCK NÃO MISTURAM COM OS REAIS)
    df_reais = pd.DataFrame()
    df_mock = pd.DataFrame()

    if not df_todos_dados.empty:
        df_todos_dados['Data_Obj'] = pd.to_datetime(df_todos_dados['Data'], format="%d/%m/%Y", errors='coerce')
        df_todos_dados['Mês/Ano'] = df_todos_dados['Data_Obj'].dt.strftime('%m/%Y').fillna('Desconhecido')
        
        # Filtra permissão de unidade do usuário logado
        unid_perm = st.session_state.get('unidades_permitidas', 'Todas')
        if unid_perm != "Todas" and st.session_state['usuario'] != "vhpezzeti":
            unidades_liberadas = [u.strip() for u in unid_perm.split(",")]
            df_todos_dados = df_todos_dados[df_todos_dados['Unidade'].isin(unidades_liberadas)]

        # Cria os dois dataframes (Real e Teste)
        df_reais = df_todos_dados[df_todos_dados['Período_Arquivo'] != 'Gerado Demo']
        df_mock = df_todos_dados[df_todos_dados['Período_Arquivo'] == 'Gerado Demo']

    # MENU LATERAL
    st.sidebar.markdown("<h3 style='text-align: center; color:#002395; font-weight: 900;'>Sistema BI</h3>", unsafe_allow_html=True)
    nivel_atual = st.session_state.get('nivel_acesso', 'Visualizador')

    st.sidebar.markdown(f"### 👋 Olá, **{st.session_state['usuario'].capitalize()}**")
    st.sidebar.markdown(f"<span style='color:#002395; font-weight:bold;'>• Nível: {nivel_atual}</span>", unsafe_allow_html=True)
    st.sidebar.markdown("---")

    opcoes_menu = ["🏢 Análise por Unidade", "📈 Relatório Comparativo Avançado"]
    if nivel_atual in ["Operador", "Administrador"] or st.session_state['usuario'] == "vhpezzeti":
        opcoes_menu.append("📂 Upload de Dados")
    if nivel_atual == "Administrador" or st.session_state['usuario'] == "vhpezzeti":
        opcoes_menu.append("⚙️ Painel do Administrador")

    menu = st.sidebar.radio("Navegação", opcoes_menu)
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair da Conta", use_container_width=True):
        st.session_state['logado'] = False
        st.rerun()

    # ========================== MÓDULOS ==========================
    
    if menu == "⚙️ Painel do Administrador":
        st.title("⚙️ Painel de Controle Administrativo")
        
        tab1, tab2, tab3, tab4 = st.tabs(["➕ Cadastrar Novo", "✏️ Editar / Excluir", "📋 Lista de Acessos", "📊 Ambiente de Teste (Gráficos)"])
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
                if st.form_submit_button("Salvar") and novo_usuario and nova_senha:
                    if novo_usuario not in lista_usuarios:
                        str_unidades = ", ".join(nova_unid) if nova_unid else "Todas"
                        novo_registro = pd.DataFrame([{"Usuario": novo_usuario, "Senha": f"'{nova_senha}", "Nivel_Acesso": novo_nivel, "Unidades_Permitidas": str_unidades}])
                        salvar_novo_usuario(pd.concat([df_users_adm, novo_registro], ignore_index=True))
                        st.success("✅ Salvo!")
                        time.sleep(1); st.rerun()

        with tab2:
            usr_editar = st.selectbox("Editar Usuário:", [""] + lista_usuarios)
            if usr_editar:
                udata = df_users_adm[df_users_adm['Usuario'] == usr_editar].iloc[0]
                with st.form("form_edicao"):
                    n_senha = st.text_input("Nova Senha (vazio mantém):", type="password")
                    n_nivel = st.selectbox("Nível:", ["Visualizador", "Operador", "Administrador"], index=["Visualizador", "Operador", "Administrador"].index(udata['Nivel_Acesso']))
                    if st.form_submit_button("Atualizar"):
                        idx = df_users_adm.index[df_users_adm['Usuario'] == usr_editar][0]
                        if n_senha: df_users_adm.at[idx, 'Senha'] = f"'{n_senha}"
                        df_users_adm.at[idx, 'Nivel_Acesso'] = n_nivel
                        salvar_novo_usuario(df_users_adm)
                        st.success("✅ Atualizado!"); time.sleep(1); st.rerun()
                    if st.form_submit_button("🗑️ Excluir"):
                        salvar_novo_usuario(df_users_adm[df_users_adm['Usuario'] != usr_editar])
                        st.success("✅ Excluído!"); time.sleep(1); st.rerun()
        
        with tab3: 
            st.dataframe(df_users_adm, use_container_width=True)

        with tab4:
            st.markdown("### 🧪 Laboratório de Teste de Gráficos")
            st.warning("Estes dados são gerados aleatoriamente pelo robô e não aparecem nos relatórios oficiais do laboratório. Servem apenas para testares a aparência dos gráficos.")
            
            if st.button("Gerar Novos 100 Dados de Teste", use_container_width=True):
                df_novos_mock = gerar_dados_teste()
                df_atual = conn.read(worksheet="Página1", ttl=0).dropna(how="all")
                salvar_dados(pd.concat([df_atual, df_novos_mock]))
                st.success("✅ Dados gerados com sucesso!")
                time.sleep(1); st.rerun()
            
            if not df_mock.empty:
                st.markdown("---")
                df_mock_pos = df_mock[df_mock['Resultado'] == 'Positivo']
                
                # Exemplo Gráficos Demo
                d1, d2 = st.columns(2)
                with d1:
                    st.markdown("#### 👥 Infecções por Sexo (DEMO)")
                    st.plotly_chart(px.pie(df_mock_pos, names='Sexo', hole=0.4, color_discrete_sequence=['#ff4b4b', '#002395']), use_container_width=True)
                with d2:
                    st.markdown("#### 📊 Faixa Etária (DEMO)")
                    df_mock_pos['Idade'] = pd.to_numeric(df_mock_pos['Idade'], errors='coerce')
                    st.plotly_chart(px.histogram(df_mock_pos, x='Idade', nbins=10, color_discrete_sequence=[COR_AZUL_BIC], text_auto=True), use_container_width=True)
            else:
                st.info("Clica no botão acima para gerar dados e veres os gráficos de teste.")

    elif menu == "📂 Upload de Dados":
        st.title("📂 Importação de PDF")
        arq = st.file_uploader("Arraste o PDF de Culturas", type=['pdf', 'txt'])
        if arq and st.button("Processar e Salvar", use_container_width=True):
            txt = ""
            if arq.name.endswith('.pdf'):
                for p in PyPDF2.PdfReader(arq).pages: txt += p.extract_text() + "\n"
            else: txt = arq.read().decode("utf-8")
            df_novo = extrair_dados_pdf(txt)
            if not df_novo.empty:
                df_puro = conn.read(worksheet="Página1", ttl=0).dropna(how="all")
                salvar_dados(pd.concat([df_puro, df_novo]).drop_duplicates(subset=['Data', 'Código_Paciente', 'Material_Exame', 'Unidade']))
                st.success(f"✅ {len(df_novo)} registros salvos na nuvem!")
                st.balloons()
            else: st.error("Falha ao ler dados do PDF.")

    elif menu == "🏢 Análise por Unidade":
        st.title("🏢 Análise Geral de Culturas")
        if df_reais.empty: st.info("Não existem laudos reais registados no momento.")
        else:
            c1, c2, c3 = st.columns(3)
            meses_disp = sorted(list(df_reais[df_reais['Mês/Ano'] != 'Desconhecido']['Mês/Ano'].unique()))
            meses_sel = c1.multiselect("📅 Meses Analisados", meses_disp, default=meses_disp)
            
            unid_disp = sorted(list(df_reais['Unidade'].unique()))
            unid_sel = c2.multiselect("🏢 Unidades", unid_disp, default=unid_disp)
            
            exame_disp = sorted(list(df_reais['Material_Exame'].unique()))
            exame_sel = c3.multiselect("🧪 Exames", exame_disp, default=exame_disp)
            
            df_f = df_reais[df_reais['Mês/Ano'].isin(meses_sel) & df_reais['Unidade'].isin(unid_sel) & df_reais['Material_Exame'].isin(exame_sel)]
            
            if df_f.empty: st.warning("Nenhum dado encontrado com os filtros selecionados.")
            else:
                t_pos = len(df_f[df_f['Resultado'] == 'Positivo'])
                t_neg = len(df_f[df_f['Resultado'] == 'Negativo'])
                qtd_meses = len(meses_sel) if len(meses_sel) > 0 else 1
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total de Exames Lidos", len(df_f))
                m2.metric("Positivos Confirmados", f"🦠 {t_pos}")
                m3.metric("Resultados Negativos", f"🛡️ {t_neg}")
                m4.metric("Média / Mês Selecionado", round(len(df_f) / qtd_meses, 1))

                if t_pos > 0:
                    df_pos = df_f[df_f['Resultado'] == 'Positivo']
                    st.markdown("---")
                    g1, g2 = st.columns(2)
                    with g1:
                        st.markdown("#### 📊 Distribuição Positivos x Negativos")
                        st.plotly_chart(px.pie(df_f, names='Resultado', hole=0.5, color='Resultado', color_discrete_map={'Positivo': COR_AZUL_BIC, 'Negativo': COR_CINZA}), use_container_width=True)
                    with g2:
                        st.markdown("#### 🧫 Frequência Bacteriana Global")
                        df_pct = df_pos['Bactéria'].value_counts(normalize=True).mul(100).round(2).reset_index()
                        df_pct.columns = ['Bactéria', '%']
                        st.plotly_chart(px.bar(df_pct, x='%', y='Bactéria', orientation='h', text_auto=True, color='Bactéria', color_discrete_sequence=PALETA_CORES).update_layout(yaxis={'categoryorder':'total ascending'}), use_container_width=True)

                    st.markdown("#### 📋 Listagem de Pacientes Positivados")
                    st.dataframe(df_pos[['Data', 'Código_Paciente', 'Unidade', 'Material_Exame', 'Bactéria', 'Indicados (S)', 'Resistentes (R)']], use_container_width=True, hide_index=True)

    elif menu == "📈 Relatório Comparativo Avançado":
        st.title("📈 Tendências, Campeões e Demografia")
        if df_reais.empty:
            st.info("Aguardando o upload de laudos reais para gerar os relatórios.")
        else:
            df_pos_comp = df_reais[df_reais['Resultado'] == 'Positivo']
            if not df_pos_comp.empty:
                b_top = df_pos_comp['Bactéria'].value_counts().idxmax()
                exame_top = df_pos_comp['Material_Exame'].value_counts().idxmax()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Bactéria de Maior Risco", b_top)
                c2.metric("Exame com Mais Positivos", exame_top)
                c3.metric("Mês com Mais Casos Acumulados", df_pos_comp['Mês/Ano'].value_counts().idxmax())
                
                st.markdown("---")
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    st.markdown("#### 📉 Curva Epidemiológica (Positivos)")
                    agrupado = df_pos_comp.groupby('Mês/Ano').size().reset_index(name='Casos')
                    st.plotly_chart(px.area(agrupado, x='Mês/Ano', y='Casos', markers=True, color_discrete_sequence=[COR_AZUL_BIC]), use_container_width=True)
                with col_g2:
                    st.markdown("#### 🏆 Top Bactérias por Tipo de Exame")
                    top_b_exame = df_pos_comp.groupby(['Material_Exame', 'Bactéria']).size().reset_index(name='Casos Registados').sort_values(['Material_Exame', 'Casos Registados'], ascending=[True, False])
                    st.dataframe(top_b_exame.groupby('Material_Exame').head(2), use_container_width=True, hide_index=True)

                st.markdown("---")
                st.markdown("### 🧬 Análise Demográfica dos Pacientes Positivos")
                df_demo = df_pos_comp[df_pos_comp['Idade'] != 'Não Informada'].copy()
                
                if df_demo.empty:
                    st.info("⚠️ Nenhum dos laudos REAIS submetidos contém a idade e sexo do paciente extraídos (ou a função do PDF ainda não lê este padrão laboratorial específico). O painel demográfico foi recolhido.")
                else:
                    df_demo['Idade'] = pd.to_numeric(df_demo['Idade'], errors='coerce')
                    
                    d1, d2 = st.columns(2)
                    with d1:
                        st.markdown("#### 👥 Infecções por Sexo")
                        st.plotly_chart(px.pie(df_demo, names='Sexo', hole=0.4, color_discrete_sequence=['#ff4b4b', '#002395']), use_container_width=True)
                    with d2:
                        st.markdown("#### 📊 Faixa Etária dos Positivos")
                        st.plotly_chart(px.histogram(df_demo, x='Idade', nbins=10, color_discrete_sequence=[COR_AZUL_BIC], text_auto=True), use_container_width=True)

            else:
                st.info("Não existem casos positivos registados na base de dados para desenhar gráficos de tendência.")
