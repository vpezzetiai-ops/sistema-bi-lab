import streamlit as st
import pandas as pd
import plotly.express as px
import re
import PyPDF2
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. CONFIGURAÇÕES INICIAIS
# ==========================================
st.set_page_config(page_title="Sistema BI - São Francisco", layout="wide", initial_sidebar_state="expanded")

COR_AZUL_BIC = '#002395'
COR_CINZA = '#808080' # CORREÇÃO: Variável definida globalmente
PALETA_CORES = ['#002395', '#4A69BD', '#708ad4', '#808080', '#A6A6A6', '#C0C0C0', '#d9d9d9']

UNIDADES_OFICIAIS = [
    "1 - Serra Negra", "3 - AME", "4 - Amparo Unidade 4", 
    "5 - Monte Alegre", "6 - Lindóia", "9 - Cenam", 
    "10 - Amparo Unidade BPA", "12 - Águas de Lindóia", "Sede / Sem Unidade"
]

# ==========================================
# 2. FUNÇÕES DE LIMPEZA E PADRONIZAÇÃO
# ==========================================
def padronizar_unidade(unidade):
    if pd.isna(unidade) or str(unidade).strip() == "" or "Não Informada" in str(unidade): return "Sede / Sem Unidade"
    numeros = re.findall(r'\d+', str(unidade))
    if not numeros: return "Sede / Sem Unidade"
    u_str = str(int(numeros[0]))
    mapa = {
        "1": "1 - Serra Negra", "3": "3 - AME", "4": "4 - Amparo Unidade 4",
        "5": "5 - Monte Alegre", "6": "6 - Lindóia", "9": "9 - Cenam",
        "10": "10 - Amparo Unidade BPA", "12": "12 - Águas de Lindóia"
    }
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
COLUNAS_DB = ["Data", "Código_Paciente", "Material_Exame", "Resultado", "Bactéria", "Indicados (S)", "Resistentes (R)", "Unidade", "Período_Arquivo"]

def carregar_dados_salvos():
    try:
        df = conn.read(worksheet="Página1", ttl=0).dropna(how="all")
        if df.empty: return pd.DataFrame(columns=COLUNAS_DB)
        df['Bactéria'] = df['Bactéria'].apply(padronizar_bacteria)
        df['Unidade'] = df['Unidade'].apply(padronizar_unidade)
        df['Material_Exame'] = df['Material_Exame'].apply(padronizar_material)
        df = df[df['Unidade'] != 'Excluir'] 
        return df
    except:
        return pd.DataFrame(columns=COLUNAS_DB)

def salvar_dados(df_final):
    conn.update(worksheet="Página1", data=df_final)

def carregar_usuarios():
    try:
        df_users = conn.read(worksheet="Usuarios", ttl=0).dropna(how="all")
        if df_users.empty: return pd.DataFrame(columns=["Usuario", "Senha", "Nivel_Acesso", "Unidades_Permitidas"])
        
        # Garante que as colunas existam mesmo em planilhas antigas
        if "Nivel_Acesso" not in df_users.columns: df_users["Nivel_Acesso"] = "Administrador"
        if "Unidades_Permitidas" not in df_users.columns: df_users["Unidades_Permitidas"] = "Todas"
            
        df_users['Usuario'] = df_users['Usuario'].astype(str).str.strip()
        df_users['Senha'] = df_users['Senha'].astype(str).str.replace(r'\.0$', '', regex=True).str.lstrip("'").str.strip()
        return df_users
    except:
        return pd.DataFrame(columns=["Usuario", "Senha", "Nivel_Acesso", "Unidades_Permitidas"])

def salvar_novo_usuario(df_users):
    conn.update(worksheet="Usuarios", data=df_users)

# ==========================================
# 4. TELA DE LOGIN COM IMAGEM MICROBIOLÓGICA REAL
# ==========================================
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'usuario' not in st.session_state: st.session_state['usuario'] = ""
if 'nivel_acesso' not in st.session_state: st.session_state['nivel_acesso'] = "Visualizador"
if 'unidades_permitidas' not in st.session_state: st.session_state['unidades_permitidas'] = "Todas"

if not st.session_state['logado']:
    st.markdown("""
    <style>
    /* Imagem Profissional de Fundo (Células/Microbiologia) */
    .stApp {
        background-image: url("https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?q=80&w=2000&auto=format&fit=crop");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    
    /* Overlay para escurecer a imagem e dar contraste */
    .stApp::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background-color: rgba(0, 35, 149, 0.4); /* Azul escuro semi-transparente */
        z-index: 0;
    }
    
    [data-testid="stHeader"] { background-color: transparent !important; }
    
    /* Card de Login Branco Flutuante (Independente do Tema) */
    [data-testid="stForm"] {
        background-color: #FFFFFF !important;
        border-radius: 12px !important;
        border: none !important;
        box-shadow: 0 20px 40px rgba(0,0,0,0.5) !important;
        padding: 40px !important;
        margin-top: 5vh;
        position: relative;
        z-index: 1;
    }
    
    /* Força os textos do login a serem escuros, ignorando o dark mode do celular */
    [data-testid="stForm"] p, [data-testid="stForm"] label, [data-testid="stForm"] div {
        color: #333333 !important;
    }
    
    /* Caixas de input no login */
    [data-testid="stForm"] input {
        background-color: #F8F9FA !important;
        color: #333333 !important;
        -webkit-text-fill-color: #333333 !important;
        border: 1px solid #E5E7EB !important;
    }
    
    div.stButton > button[kind="primary"] {
        background-color: #002395 !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: bold !important;
        transition: all 0.3s ease !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #4A69BD !important;
    }
    </style>
    """, unsafe_allow_html=True)

    col_vazia_esq, col_login, col_vazia_dir = st.columns([1, 1.2, 1])
    with col_login:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.form(key="login_form"):
            col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
            with col_logo2:
                try: st.image("logo.png", use_container_width=True)
                except: st.markdown("<h2 style='text-align: center; color:#002395 !important;'>SÃO FRANCISCO</h2>", unsafe_allow_html=True)
            
            st.markdown("<h4 style='text-align: center; color:#333333 !important; margin-bottom:30px;'>Acesso ao Sistema Analítico</h4>", unsafe_allow_html=True)
            
            usuario_input = st.text_input("👤 Nome de Usuário:")
            senha_input = st.text_input("🔑 Senha de Acesso:", type="password")
            st.markdown("<br>", unsafe_allow_html=True)
            submit_button = st.form_submit_button("Fazer Login 🚀", type="primary", use_container_width=True)
            
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
# CSS DO SISTEMA INTERNO (LIMPO E ADAPTÁVEL)
# ==========================================
st.markdown("""
    <style>
    /* Remove a imagem de fundo pesada quando entra no sistema */
    .stApp { background-image: none !important; background-color: var(--background-color) !important;}
    .stApp::before { display: none !important; }
    
    div[data-testid="metric-container"] {
        background-color: var(--secondary-background-color) !important;
        border: 1px solid var(--border-color) !important;
        padding: 20px !important; border-radius: 12px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important; 
        border-left: 5px solid #002395 !important;
    }
    .stTabs [aria-selected="true"] { border-bottom-color: #002395 !important; color: #002395 !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 5. EXTRAÇÃO DO PDF 
# ==========================================
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
                "Data": data_pac, "Código_Paciente": cod_pac, "Material_Exame": f"[{tag}]", 
                "Resultado": "Negativo", "Bactéria": "N/A", "Indicados (S)": "", 
                "Resistentes (R)": "", "Unidade": unidade_pac, "Período_Arquivo": periodo_doc
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
                    if "Não houve" not in bac_str and "Aplic" not in bac_str:
                        linha["Bactéria"] = padronizar_bacteria(bac_str)
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

# ==========================================
# 6. MENU LATERAL E DADOS
# ==========================================
try: st.sidebar.image("logo.png", use_container_width=True)
except: st.sidebar.empty() 

nivel_atual = st.session_state.get('nivel_acesso', 'Visualizador')
unid_perm = st.session_state.get('unidades_permitidas', 'Todas')

st.sidebar.markdown(f"### 👋 Olá, **{st.session_state['usuario'].capitalize()}**")
st.sidebar.markdown(f"<span style='color:#002395; font-weight:bold;'>• {nivel_atual}</span>", unsafe_allow_html=True)
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

df_historico = carregar_dados_salvos()
if not df_historico.empty:
    df_historico['Data_Obj'] = pd.to_datetime(df_historico['Data'], format="%d/%m/%Y", errors='coerce')
    df_historico['Mês/Ano'] = df_historico['Data_Obj'].dt.strftime('%m/%Y').fillna('Desconhecido')
    
    # APLICAÇÃO DO FILTRO DE PERMISSÃO DE UNIDADES (Apenas visualizadores sofrem restrição)
    if unid_perm != "Todas" and st.session_state['usuario'] != "vhpezzeti":
        unidades_liberadas = [u.strip() for u in unid_perm.split(",")]
        df_historico = df_historico[df_historico['Unidade'].isin(unidades_liberadas)]

# ==========================================
# 7. TELAS DO SISTEMA
# ==========================================

# ----- TELA ADMIN -----
if menu == "⚙️ Painel do Administrador":
    st.title("⚙️ Painel de Controle Administrativo")
    st.markdown("Gerencie acessos e defina **quais unidades** cada funcionário pode visualizar.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["➕ Cadastrar Novo", "✏️ Editar / Excluir", "📋 Lista de Acessos"])
    
    df_users_adm = carregar_usuarios()
    lista_usuarios = df_users_adm['Usuario'].tolist() if not df_users_adm.empty else []

    with tab1:
        st.markdown("#### Criar Nova Credencial")
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1: novo_usuario = st.text_input("Login do Funcionário:")
            with col2: nova_senha = st.text_input("Senha de Acesso:", type="password")
            
            st.markdown("---")
            col3, col4 = st.columns(2)
            with col3: 
                novo_nivel = st.selectbox("Nível de Permissão:", ["Visualizador (Apenas Gráficos)", "Operador (Gráficos + Upload)", "Administrador (Acesso Total)"])
            with col4:
                nova_unid_perm = st.multiselect("Unidades Permitidas (Deixe vazio para dar acesso a TODAS):", UNIDADES_OFICIAIS)
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Salvar Cadastro ✔️", type="primary", use_container_width=True):
                if novo_usuario and nova_senha:
                    if novo_usuario in lista_usuarios:
                        st.error("❌ Este login já existe no sistema.")
                    else:
                        senha_salva = f"'{nova_senha}" if nova_senha.isdigit() else nova_senha
                        nivel_salvo = novo_nivel.split(" ")[0]
                        str_unidades = ", ".join(nova_unid_perm) if nova_unid_perm else "Todas"
                        
                        novo_registro = pd.DataFrame([{"Usuario": novo_usuario, "Senha": senha_salva, "Nivel_Acesso": nivel_salvo, "Unidades_Permitidas": str_unidades}])
                        df_users_atualizado = pd.concat([df_users_adm, novo_registro], ignore_index=True)
                        salvar_novo_usuario(df_users_atualizado)
                        st.success(f"✅ Funcionário cadastrado com sucesso!")
                        st.rerun()
                else:
                    st.warning("Preencha Login e Senha antes de salvar.")
                    
    with tab2:
        st.markdown("#### Atualizar Credencial Existente")
        with st.container(border=True):
            if not lista_usuarios:
                st.info("Nenhum usuário cadastrado no momento.")
            else:
                usuario_editar = st.selectbox("Selecione o Usuário para Editar:", [""] + lista_usuarios)
                
                if usuario_editar:
                    user_data = df_users_adm[df_users_adm['Usuario'] == usuario_editar].iloc[0]
                    nivel_atual_ed = user_data.get('Nivel_Acesso', 'Visualizador')
                    unid_atual_ed = user_data.get('Unidades_Permitidas', 'Todas')
                    
                    opcoes_niveis = ["Visualizador", "Operador", "Administrador"]
                    idx_nivel = opcoes_niveis.index(nivel_atual_ed) if nivel_atual_ed in opcoes_niveis else 0
                    
                    vetor_unid_atual = [] if unid_atual_ed == "Todas" else [u.strip() for u in str(unid_atual_ed).split(",")]
                    
                    col_e1, col_e2 = st.columns(2)
                    with col_e1: nova_senha_ed = st.text_input("Nova Senha (deixe em branco para manter a atual):", type="password")
                    with col_e2: novo_nivel_ed = st.selectbox("Novo Nível:", opcoes_niveis, index=idx_nivel)
                    
                    novo_vetor_unid = st.multiselect("Alterar Unidades Permitidas (Vazio = Todas):", UNIDADES_OFICIAIS, default=[u for u in vetor_unid_atual if u in UNIDADES_OFICIAIS])
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    col_btn1, col_btn2 = st.columns(2)
                    
                    with col_btn1:
                        if st.button("Atualizar Usuário 🔄", use_container_width=True):
                            idx_row = df_users_adm.index[df_users_adm['Usuario'] == usuario_editar][0]
                            if nova_senha_ed:
                                df_users_adm.at[idx_row, 'Senha'] = f"'{nova_senha_ed}" if nova_senha_ed.isdigit() else nova_senha_ed
                            df_users_adm.at[idx_row, 'Nivel_Acesso'] = novo_nivel_ed
                            df_users_adm.at[idx_row, 'Unidades_Permitidas'] = ", ".join(novo_vetor_unid) if novo_vetor_unid else "Todas"
                            salvar_novo_usuario(df_users_adm)
                            st.success(f"✅ Conta de {usuario_editar} atualizada!")
                            st.rerun()
                            
                    with col_btn2:
                        if st.button("🗑️ Excluir Usuário", use_container_width=True):
                            if usuario_editar == st.session_state['usuario']:
                                st.error("Você não pode excluir sua própria conta enquanto está logado!")
                            else:
                                df_users_adm = df_users_adm[df_users_adm['Usuario'] != usuario_editar]
                                salvar_novo_usuario(df_users_adm)
                                st.success("✅ Conta excluída com sucesso!")
                                st.rerun()

    with tab3:
        st.markdown("#### Tabela de Permissões")
        st.dataframe(df_users_adm, use_container_width=True, hide_index=True)

# ----- TELA DE UPLOAD -----
elif menu == "📂 Upload de Dados":
    st.title("📂 Importação de Resultados PDF")
    st.markdown("Faça o upload dos arquivos gerados pelo sistema do laboratório. O robô irá higienizar e organizar os dados na Nuvem.")
    
    with st.container(border=True):
        arquivo_upload = st.file_uploader("Arraste seu arquivo PDF aqui 👇", type=['pdf', 'txt'])
        
        if arquivo_upload is not None:
            if st.button("Processar e Salvar no Banco de Dados ☁️", type="primary", use_container_width=True):
                with st.spinner('Lendo arquivo, aplicando filtros de inteligência e salvando...'):
                    texto_dados = ""
                    if arquivo_upload.name.endswith('.pdf'):
                        leitor_pdf = PyPDF2.PdfReader(arquivo_upload)
                        for pagina in leitor_pdf.pages:
                            texto = pagina.extract_text()
                            if texto: texto_dados += texto + "\n"
                    else:
                        texto_dados = arquivo_upload.read().decode("utf-8")
                        
                    df_novo = extrair_dados_pdf(texto_dados)
                    if not df_novo.empty:
                        df_puro = conn.read(worksheet="Página1", ttl=0).dropna(how="all") if not df_historico.empty else pd.DataFrame(columns=COLUNAS_DB)
                        df_final = pd.concat([df_puro, df_novo]).drop_duplicates(subset=['Data', 'Código_Paciente', 'Material_Exame', 'Unidade'])
                        salvar_dados(df_final)
                        st.success(f"✅ Extração Concluída! {len(df_novo)} registros limpos e salvos na Nuvem.")
                        st.balloons()
                    else:
                        st.error("Não foi possível encontrar dados válidos neste PDF.")

# ----- TELA DASHBOARD BÁSICO -----
elif menu == "🏢 Análise por Unidade":
    st.title("🏢 Análise Geral de Culturas")
    
    if df_historico.empty:
        st.info("⚠️ Não há dados disponíveis para as unidades que você tem permissão.")
    else:
        with st.container(border=True):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                periodos = ["Todos os Meses"] + sorted(list(df_historico[df_historico['Mês/Ano'] != 'Desconhecido']['Mês/Ano'].unique()))
                periodo_sel = st.selectbox("📅 Selecione o Mês:", periodos)
            with col_f2:
                unidades = ["Todas as Unidades"] + sorted(list(df_historico['Unidade'].unique()))
                unidade_sel = st.selectbox("🏢 Selecione a Unidade:", unidades)
        
        df_f = df_historico.copy()
        if periodo_sel != "Todos os Meses": df_f = df_f[df_f['Mês/Ano'] == periodo_sel]
        if unidade_sel != "Todas as Unidades": df_f = df_f[df_f['Unidade'] == unidade_sel]
            
        t_pos = len(df_f[df_f['Resultado'] == 'Positivo'])
        
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total de Exames Lidos", len(df_f))
        c2.metric("Resultados Positivos 🦠", t_pos)
        c3.metric("Resultados Negativos 🛡️", len(df_f[df_f['Resultado'] == 'Negativo']))
        
        if t_pos > 0:
            df_pos = df_f[df_f['Resultado'] == 'Positivo']
            st.markdown("<br>", unsafe_allow_html=True)
            
            c_graf1, c_graf2 = st.columns(2)
            
            with c_graf1:
                st.markdown("#### 📊 Distribuição Positivos x Negativos")
                fig_pizza = px.pie(df_f, names='Resultado', hole=0.5, color='Resultado', color_discrete_map={'Positivo': COR_AZUL_BIC, 'Negativo': COR_CINZA})
                st.plotly_chart(fig_pizza, use_container_width=True, theme="streamlit")
                
            with c_graf2:
                st.markdown("#### 🧫 Frequência Bacteriana")
                df_percent = df_pos['Bactéria'].value_counts(normalize=True).mul(100).round(2).reset_index()
                df_percent.columns = ['Bactéria', '%']
                fig_bac = px.bar(df_percent, x='%', y='Bactéria', orientation='h', text_auto=True, color='Bactéria', color_discrete_sequence=PALETA_CORES)
                fig_bac.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_bac, use_container_width=True, theme="streamlit")

            st.markdown("#### 📋 Detalhamento dos Pacientes (Positivos)")
            st.dataframe(df_pos[['Data', 'Unidade', 'Material_Exame', 'Bactéria', 'Indicados (S)', 'Resistentes (R)']], use_container_width=True, hide_index=True)

# ----- TELA COMPARATIVO AVANÇADO -----
elif menu == "📈 Relatório Comparativo Avançado":
    st.title("📈 Inteligência Analítica e Tendências")
    
    if df_historico.empty:
        st.info("⚠️ Não há dados disponíveis para as unidades que você tem permissão.")
    else:
        with st.container(border=True):
            col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
            with col_filtro1:
                opcoes_mes = ["Todos os Meses"] + sorted(list(df_historico[df_historico['Mês/Ano'] != 'Desconhecido']['Mês/Ano'].unique()))
                mes_comparativo = st.selectbox("📅 Filtrar Mês:", opcoes_mes)
            with col_filtro2:
                opcoes_unidade = ["Todas as Unidades"] + sorted(list(df_historico['Unidade'].unique()))
                unidade_comparativo = st.selectbox("🏢 Filtrar Unidade:", opcoes_unidade)
            with col_filtro3:
                opcoes_exame = ["Todos os Exames"] + sorted(list(df_historico['Material_Exame'].unique()))
                exame_comparativo = st.selectbox("🧪 Filtrar Material:", opcoes_exame)

        df_comp = df_historico.copy()
        if mes_comparativo != "Todos os Meses": df_comp = df_comp[df_comp['Mês/Ano'] == mes_comparativo]
        if unidade_comparativo != "Todas as Unidades": df_comp = df_comp[df_comp['Unidade'] == unidade_comparativo]
        if exame_comparativo != "Todos os Exames": df_comp = df_comp[df_comp['Material_Exame'] == exame_comparativo]

        df_pos_comp = df_comp[df_comp['Resultado'] == 'Positivo']

        if not df_pos_comp.empty:
            bacteria_top = df_pos_comp['Bactéria'].value_counts().idxmax()
            if mes_comparativo == "Todos os Meses":
                mes_pico = df_pos_comp['Mês/Ano'].value_counts().idxmax()
                texto_mes_pico = f"Mês de Pico: {mes_pico}"
            else:
                texto_mes_pico = f"Mês Analisado: {mes_comparativo}"
                
            st.markdown("<br>", unsafe_allow_html=True)
            c_m1, c_m2, c_m3 = st.columns(3)
            c_m1.metric("Total de Positivos Filtrados", len(df_pos_comp))
            c_m2.metric("Bactéria Mais Detectada 🦠", bacteria_top)
            c_m3.metric("Indicador de Volume 📈", texto_mes_pico)

            st.markdown("---")
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.markdown("#### 📊 Crescimento de Positivos")
                agrupado_tempo = df_pos_comp.groupby('Mês/Ano').size().reset_index(name='Casos')
                fig_linha = px.area(agrupado_tempo, x='Mês/Ano', y='Casos', markers=True, color_discrete_sequence=[COR_AZUL_BIC])
                st.plotly_chart(fig_linha, use_container_width=True, theme="streamlit")
                
            with col_g2:
                st.markdown("#### 🎯 Top 5 Incidências")
                agrupado_bac = df_pos_comp['Bactéria'].value_counts(normalize=True).mul(100).round(2).reset_index()
                agrupado_bac.columns = ['Bactéria', '%']
                fig_bar_bac = px.bar(agrupado_bac.head(5), x='%', y='Bactéria', orientation='h', text_auto=True, color='Bactéria', color_discrete_sequence=PALETA_CORES)
                fig_bar_bac.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_bar_bac, use_container_width=True, theme="streamlit")

            st.markdown("#### 📌 Detalhamento Estratégico (% Do Total Filtrado)")
            df_percent_final = df_pos_comp.groupby(['Unidade', 'Material_Exame', 'Bactéria']).size().reset_index(name='Casos')
            df_percent_final['%'] = (df_percent_final['Casos'] / len(df_pos_comp) * 100).round(2)
            df_percent_final = df_percent_final.sort_values(by='%', ascending=False)
            st.dataframe(df_percent_final, use_container_width=True, hide_index=True)

        else:
            st.info("Não houve nenhum registro positivo encontrado com os filtros selecionados acima.")
