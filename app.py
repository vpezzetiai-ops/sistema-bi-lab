import streamlit as st
import pandas as pd
import plotly.express as px
import re
import PyPDF2
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. CONFIGURAÇÕES INICIAIS E TEMA
# ==========================================
st.set_page_config(page_title="Sistema BI - Laboratório", layout="wide")

st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #002395 !important;
        color: white !important;
        border: none;
        border-radius: 5px;
        font-weight: bold;
    }
    div.stButton > button:first-child:hover {
        background-color: #00155f !important;
        border: 1px solid #808080;
    }
    [data-testid="stSidebar"] {
        background-color: #F0F2F6 !important;
    }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] div {
        color: #333333 !important;
    }
    h1, h2, h3, [data-testid="stSidebar"] h1 {
        color: #002395 !important;
    }
    [data-testid="stSidebar"] button * {
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

COR_AZUL_BIC = '#002395'
COR_CINZA = '#808080'
PALETA_CORES = ['#002395', '#4A69BD', '#808080', '#A6A6A6', '#C0C0C0']

# ==========================================
# 2. CONEXÃO COM GOOGLE SHEETS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)
COLUNAS_DB = ["Data", "Código_Paciente", "Material_Exame", "Resultado", "Bactéria", "Indicados (S)", "Resistentes (R)", "Unidade", "Período_Arquivo"]

def carregar_dados_salvos():
    try:
        df = conn.read(worksheet="Página1", ttl=0)
        df = df.dropna(how="all")
        if df.empty: return pd.DataFrame(columns=COLUNAS_DB)
        return df
    except:
        return pd.DataFrame(columns=COLUNAS_DB)

def salvar_dados(df_final):
    conn.update(worksheet="Página1", data=df_final)

def carregar_usuarios():
    try:
        df_users = conn.read(worksheet="Usuarios", ttl=0)
        df_users = df_users.dropna(how="all")
        if df_users.empty: return pd.DataFrame(columns=["Usuario", "Senha"])
        return df_users
    except:
        return pd.DataFrame(columns=["Usuario", "Senha"])

def salvar_novo_usuario(df_users):
    conn.update(worksheet="Usuarios", data=df_users)

# ==========================================
# 3. TELA DE LOGIN PREMIUM E CENTRALIZADA
# ==========================================
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'usuario' not in st.session_state:
    st.session_state['usuario'] = ""

if not st.session_state['logado']:
    col_vazia_esq, col_login, col_vazia_dir = st.columns([1, 1.2, 1])
    
    with col_login:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
            with col_logo2:
                try:
                    st.image("logo.png", use_container_width=True)
                except:
                    st.markdown("<h2 style='text-align: center;'>SÃO FRANCISCO</h2>", unsafe_allow_html=True)
            
            st.markdown("<h4 style='text-align: center; color: #808080;'>Acesso ao Painel Analítico</h4>", unsafe_allow_html=True)
            st.markdown("---")
            
            usuario_input = st.text_input("👤 Nome de Usuário:")
            senha_input = st.text_input("🔑 Senha de Acesso:", type="password")
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("Fazer Login 🚀", use_container_width=True):
                df_usuarios = carregar_usuarios()
                usuario_encontrado = df_usuarios[df_usuarios['Usuario'] == usuario_input]
                
                if not usuario_encontrado.empty and str(usuario_encontrado.iloc[0]['Senha']) == senha_input:
                    st.session_state['logado'] = True
                    st.session_state['usuario'] = usuario_input
                    st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos. Acesso negado.")
    st.stop()

# ==========================================
# 4. EXTRAÇÃO DO PDF ULTRA-RESISTENTE
# ==========================================
def extrair_dados_pdf(texto_bruto):
    dados = []
    
    # Extrai o período (mantido apenas como backup, não mais como filtro principal)
    periodo_doc = "Período Indefinido"
    match_per = re.search(r'Per[íi]odo de (\d{2}/\d{2}/\d{4}) [àa] (\d{2}/\d{2}/\d{4})', texto_bruto, re.IGNORECASE)
    if match_per: periodo_doc = f"{match_per.group(1)} a {match_per.group(2)}"

    blocos = re.split(r'(?=\b\d{2}/\d{2}/\d{4}\s+\d{4,}\b)', texto_bruto)
    
    for bloco in blocos:
        if not bloco.strip(): continue
        linha = {"Data": None, "Código_Paciente": None, "Material_Exame": "Desconhecido", "Resultado": "Negativo", "Bactéria": "N/A", "Indicados (S)": "", "Resistentes (R)": "", "Unidade": "Não Informada", "Período_Arquivo": periodo_doc}
        
        match_header = re.search(r'(\d{2}/\d{2}/\d{4})\s+(\d{4,})', bloco)
        if match_header: 
            linha["Data"], linha["Código_Paciente"] = match_header.group(1), match_header.group(2)
        else:
            continue
        
        match_exame = re.search(r'\[([A-Z]+)\]', bloco)
        if match_exame: linha["Material_Exame"] = match_exame.group(1)
            
        match_unidade = re.search(r'Unidade Sigla:\s*(\d+)', bloco)
        if match_unidade: linha["Unidade"] = match_unidade.group(1)
            
        if "Micro-organismo identificado" in bloco or "MIC:" in bloco:
            linha["Resultado"] = "Positivo"
            match_mic = re.search(r'MIC:\s*(.*?)(?=SERIE|AMI)', bloco, re.IGNORECASE)
            if match_mic:
                bac = match_mic.group(1).replace(":", "").strip()
                if "Não houve" not in bac and "Aplic" not in bac:
                    linha["Bactéria"] = bac
            
            if linha["Bactéria"] == "N/A":
                match_bac = re.search(r'identificado:\s*(.*?)(?=URO|Determ|:)', bloco)
                if match_bac:
                    linha["Bactéria"] = match_bac.group(1).strip()
            
            linha["Indicados (S)"] = ", ".join(re.findall(r'\b([A-Z]{2,})[\s:]*S\b', bloco))
            linha["Resistentes (R)"] = ", ".join(re.findall(r'\b([A-Z]{2,})[\s:]*R\b', bloco))
            
            if "Não houve" in linha["Bactéria"] or linha["Bactéria"] == "N/A":
                linha["Resultado"] = "Negativo"
                linha["Bactéria"] = "N/A"
                linha["Indicados (S)"] = ""
                linha["Resistentes (R)"] = ""
        
        if linha["Data"]: dados.append(linha)
    return pd.DataFrame(dados)

# ==========================================
# 5. PREPARAÇÃO DO BANCO DE DADOS (COM DATAS INTELIGENTES)
# ==========================================
df_historico = carregar_dados_salvos()

# Se existir dados, o sistema força a leitura da coluna 'Data' para separar o Mês/Ano automaticamente
if not df_historico.empty:
    df_historico['Data_Obj'] = pd.to_datetime(df_historico['Data'], format="%d/%m/%Y", errors='coerce')
    df_historico['Mês/Ano'] = df_historico['Data_Obj'].dt.strftime('%m/%Y').fillna('Desconhecido')

# ==========================================
# 6. MENU LATERAL INTELIGENTE
# ==========================================
try:
    st.sidebar.image("logo.png", use_container_width=True)
except:
    st.sidebar.empty() 

st.sidebar.title(f"Usuário: {st.session_state['usuario']}")

opcoes_menu = ["📂 Upload de Dados", "🏢 Dashboard por Unidade", "📈 Comparativo Mensal"]
if st.session_state['usuario'] == "vhpezzeti":  
    opcoes_menu.append("⚙️ Painel do Administrador")

menu = st.sidebar.radio("Navegação", opcoes_menu)

st.sidebar.markdown("---")
if st.sidebar.button("Sair da Conta"):
    st.session_state['logado'] = False
    st.rerun()
st.sidebar.markdown("---")

try:
    st.sidebar.image("assinatura.png", use_container_width=True)
except:
    st.sidebar.caption("Desenvolvido por: Seu Nome")

# ==========================================
# TELAS DO SISTEMA
# ==========================================

# ----- TELA ADMIN -----
if menu == "⚙️ Painel do Administrador":
    st.title("Painel de Controle - Acesso Restrito")
    st.write("Gerencie os acessos da sua equipe. Apenas usuários listados aqui poderão acessar o sistema.")
    
    st.markdown("### Cadastrar Novo Funcionário")
    col1, col2 = st.columns(2)
    with col1:
        novo_usuario = st.text_input("Login do Funcionário:")
    with col2:
        nova_senha = st.text_input("Senha de Acesso:", type="password")
        
    if st.button("Salvar Cadastro"):
        if novo_usuario and nova_senha:
            df_users = carregar_usuarios()
            if novo_usuario in df_users['Usuario'].values:
                st.error("❌ Este login já existe no sistema.")
            else:
                novo_registro = pd.DataFrame([{"Usuario": novo_usuario, "Senha": nova_senha}])
                df_users_atualizado = pd.concat([df_users, novo_registro], ignore_index=True)
                salvar_novo_usuario(df_users_atualizado)
                st.success(f"✅ Funcionário cadastrado!")
        else:
            st.warning("Preencha todos os campos.")
            
    st.markdown("---")
    st.markdown("### Funcionários Cadastrados")
    st.dataframe(carregar_usuarios(), use_container_width=True)

# ----- TELA DE UPLOAD -----
elif menu == "📂 Upload de Dados":
    st.title("Importação de Resultados PDF")
    st.write("Suba o arquivo do sistema. Os dados serão lidos e salvos na Nuvem.")
    arquivo_upload = st.file_uploader("Arraste seu arquivo PDF aqui", type=['pdf', 'txt'])
    
    if arquivo_upload is not None:
        if st.button("Processar e Salvar no Banco de Dados"):
            with st.spinner('Lendo arquivo e enviando para o Google Sheets...'):
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
                    # Garantindo que o df_historico base venha puro (sem as colunas extras que criamos temporariamente)
                    df_puro = carregar_dados_salvos()
                    df_final = pd.concat([df_puro, df_novo]).drop_duplicates(subset=['Data', 'Código_Paciente', 'Material_Exame', 'Unidade'])
                    salvar_dados(df_final)
                    st.success(f"✅ Sucesso! {len(df_novo)} registros processados e salvos na Nuvem.")
                else:
                    st.warning("Não foi possível encontrar dados válidos neste arquivo.")

# ----- TELA DASHBOARD -----
elif menu == "🏢 Dashboard por Unidade":
    st.title("Análise de Cultura por Unidade e Mês")
    
    if df_historico.empty:
        st.warning("⚠️ Não há dados no sistema. Vá na aba 'Upload de Dados' primeiro.")
    else:
        st.markdown("### Filtros de Análise")
        col_filtro1, col_filtro2 = st.columns(2)
        
        with col_filtro1:
            # AGORA LÊ A DATA EXATA EXTRAIDA (Mês/Ano) DO EXAME
            periodos = ["Todos"] + sorted(list(df_historico[df_historico['Mês/Ano'] != 'Desconhecido']['Mês/Ano'].unique()))
            periodo_sel = st.selectbox("📅 Escolha o Mês/Ano (Automático):", periodos)
            
        with col_filtro2:
            unidades = ["Todas"] + sorted(list(df_historico['Unidade'].dropna().astype(str).unique()))
            unidade_sel = st.selectbox("🏢 Escolha a Unidade:", unidades)
        
        df_filtrado = df_historico.copy()
        
        if periodo_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado['Mês/Ano'] == periodo_sel]
            
        if unidade_sel != "Todas":
            df_filtrado = df_filtrado[df_filtrado['Unidade'].astype(str) == str(unidade_sel)]
            
        t_exames = len(df_filtrado)
        t_pos = len(df_filtrado[df_filtrado['Resultado'] == 'Positivo'])
        t_neg = len(df_filtrado[df_filtrado['Resultado'] == 'Negativo'])
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Exames Encontrados", t_exames)
        col2.metric("Positivos", t_pos)
        col3.metric("Negativos", t_neg)
        
        st.markdown("---")
        if t_pos > 0:
            df_pos = df_filtrado[df_filtrado['Resultado'] == 'Positivo']
            cA, cB = st.columns(2)
            with cA:
                st.subheader("Positivos x Negativos (Geral)")
                fig_pizza = px.pie(df_filtrado, names='Resultado', hole=0.4, color='Resultado', color_discrete_map={'Positivo': COR_AZUL_BIC, 'Negativo': COR_CINZA})
                st.plotly_chart(fig_pizza, use_container_width=True)
            with cB:
                st.subheader("Gráfico de Bactérias (Positivos)")
                fig_bac = px.histogram(df_pos, x='Bactéria', color='Bactéria', color_discrete_sequence=PALETA_CORES)
                st.plotly_chart(fig_bac, use_container_width=True)
                
            st.markdown("### Porcentagem de Cada Bactéria")
            df_percent = df_pos['Bactéria'].value_counts(normalize=True).mul(100).round(2).reset_index()
            df_percent.columns = ['Microrganismo (Bactéria)', 'Porcentagem (%)']
            st.dataframe(df_percent, use_container_width=True)
            
            st.markdown("### Detalhamento: Resistência e Indicação")
            st.dataframe(df_pos[['Data', 'Unidade', 'Material_Exame', 'Bactéria', 'Indicados (S)', 'Resistentes (R)']], use_container_width=True)
        else:
            if t_exames == 0:
                st.info("Nenhum exame encontrado para estes filtros.")
            else:
                st.info("Nenhum exame positivo registrado com estes filtros.")

# ----- TELA COMPARATIVO -----
elif menu == "📈 Comparativo Mensal":
    st.title("Evolução Histórica e Comparativo")
    
    if df_historico.empty:
        st.warning("⚠️ Não há dados salvos no sistema.")
    else:
        df_pos_hist = df_historico[df_historico['Resultado'] == 'Positivo']
        
        if not df_pos_hist.empty:
            agrupado = df_pos_hist.groupby(['Mês/Ano', 'Unidade']).size().reset_index(name='Casos Positivos')
            fig_evolucao = px.bar(agrupado, x='Mês/Ano', y='Casos Positivos', color='Unidade', barmode='group', title="Comparativo Mensal de Exames Positivos por Unidade", color_discrete_sequence=PALETA_CORES)
            st.plotly_chart(fig_evolucao, use_container_width=True)
        else:
            st.info("Nenhum caso positivo no histórico para gerar evolução mensal.")
