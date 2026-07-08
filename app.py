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
    
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

COR_AZUL_BIC = '#002395'
COR_CINZA = '#808080'
PALETA_CORES = ['#002395', '#4A69BD', '#708ad4', '#808080', '#A6A6A6', '#C0C0C0', '#d9d9d9']

# ==========================================
# 2. FUNÇÕES DE LIMPEZA E PADRONIZAÇÃO
# ==========================================
def padronizar_unidade(unidade):
    if pd.isna(unidade) or unidade == "Não Informada": return "Não Informada"
    u_str = str(unidade).strip().lstrip('0')
    mapa = {
        "1": "1 - Serra Negra",
        "3": "3 - AME",
        "4": "4 - Amparo Unidade 4",
        "5": "5 - Monte Alegre",
        "6": "6 - Lindóia",
        "9": "9 - Cenam",
        "10": "10 - Amparo Unidade BPA",
        "12": "12 - Águas de Lindóia"
    }
    return mapa.get(u_str, f"Unidade {u_str}")

def padronizar_bacteria(nome):
    if pd.isna(nome) or nome == "N/A": return "N/A"
    n = str(nome).strip().lower()
    
    if "coli" in n or "escherichia" in n: return "Escherichia coli"
    if "proteus" in n: return "Proteus sp."
    if "enterobacter" in n: return "Enterobacter sp."
    if "pseudomonas" in n: return "Pseudomonas sp."
    if "klebsiella" in n: return "Klebsiella sp."
    if "staphylococcu" in n: return "Staphylococcus sp."
    if "streptococcu" in n: return "Streptococcus sp."
    if "enterococcu" in n: return "Enterococcus sp."
    
    return str(nome).strip().title()

# ==========================================
# 3. CONEXÃO COM GOOGLE SHEETS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)
COLUNAS_DB = ["Data", "Código_Paciente", "Material_Exame", "Resultado", "Bactéria", "Indicados (S)", "Resistentes (R)", "Unidade", "Período_Arquivo"]

def carregar_dados_salvos():
    try:
        df = conn.read(worksheet="Página1", ttl=0)
        df = df.dropna(how="all")
        if df.empty: return pd.DataFrame(columns=COLUNAS_DB)
        
        df['Bactéria'] = df['Bactéria'].apply(padronizar_bacteria)
        df['Unidade'] = df['Unidade'].apply(padronizar_unidade)
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
        
        df_users['Usuario'] = df_users['Usuario'].astype(str).str.strip()
        df_users['Senha'] = df_users['Senha'].astype(str).str.replace(r'\.0$', '', regex=True).str.lstrip("'").str.strip()
        return df_users
    except:
        return pd.DataFrame(columns=["Usuario", "Senha"])

def salvar_novo_usuario(df_users):
    conn.update(worksheet="Usuarios", data=df_users)

# ==========================================
# 4. TELA DE LOGIN 
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
            
            with st.form(key="login_form"):
                usuario_input = st.text_input("👤 Nome de Usuário:")
                senha_input = st.text_input("🔑 Senha de Acesso:", type="password")
                st.markdown("<br>", unsafe_allow_html=True)
                submit_button = st.form_submit_button("Fazer Login 🚀", use_container_width=True)
                
                if submit_button:
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
# 5. EXTRAÇÃO DO PDF (UNIVERSAL - SANGUE E URINA)
# ==========================================
def extrair_dados_pdf(texto_bruto):
    dados = []
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
        if match_unidade: 
            linha["Unidade"] = padronizar_unidade(match_unidade.group(1))
            
        # Nova Lógica Universal: Procura por "Não houve crescimento" (Sangue) ou "Não houve desenvolvimento" (Urina)
        if "Não houve crescimento" in bloco or "Não houve desenvolvimento" in bloco:
            linha["Resultado"] = "Negativo"
            linha["Bactéria"] = "N/A"
        else:
            # Padrão Científico: Procura por algo classificado (ex: 1: Staphylococcus) ignorando o resto colado
            match_bac = re.search(r'(?:identificado|1):\s*([A-Z][a-z]+(?:\s+[a-z]+)?(?:\s+sp\.?)?)', bloco)
            if match_bac:
                linha["Resultado"] = "Positivo"
                linha["Bactéria"] = padronizar_bacteria(match_bac.group(1).strip())
                
                # Extrai siglas de antibióticos, ignorando números no meio como 'MOX2' e agrupando
                sensiveis = re.findall(r'\b([A-Z]{2,})\d*[\s:]+S\b', bloco)
                resistentes = re.findall(r'\b([A-Z]{2,})\d*[\s:]+R\b', bloco)
                
                linha["Indicados (S)"] = ", ".join(sorted(list(set(sensiveis))))
                linha["Resistentes (R)"] = ", ".join(sorted(list(set(resistentes))))
                
            elif "MIC:" in bloco: # Fallback de segurança
                linha["Resultado"] = "Positivo"
                match_mic = re.search(r'MIC:\s*([A-Z][a-z]+(?:\s+[a-z]+)?(?:\s+sp\.?)?)', bloco)
                if match_mic:
                    linha["Bactéria"] = padronizar_bacteria(match_mic.group(1).strip())
                    sensiveis = re.findall(r'\b([A-Z]{2,})\d*[\s:]+S\b', bloco)
                    resistentes = re.findall(r'\b([A-Z]{2,})\d*[\s:]+R\b', bloco)
                    linha["Indicados (S)"] = ", ".join(sorted(list(set(sensiveis))))
                    linha["Resistentes (R)"] = ", ".join(sorted(list(set(resistentes))))

        if linha["Data"]: dados.append(linha)
    return pd.DataFrame(dados)

# ==========================================
# 6. MENU LATERAL E PREPARAÇÃO DO BD
# ==========================================
try:
    st.sidebar.image("logo.png", use_container_width=True)
except:
    st.sidebar.empty() 

st.sidebar.title(f"Usuário: {st.session_state['usuario']}")

opcoes_menu = ["📂 Upload de Dados", "🏢 Análise por Unidade", "📈 Relatório Comparativo Avançado"]
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

df_historico = carregar_dados_salvos()
if not df_historico.empty:
    df_historico['Data_Obj'] = pd.to_datetime(df_historico['Data'], format="%d/%m/%Y", errors='coerce')
    df_historico['Mês/Ano'] = df_historico['Data_Obj'].dt.strftime('%m/%Y').fillna('Desconhecido')

# ==========================================
# TELAS DO SISTEMA
# ==========================================

# ----- TELA ADMIN -----
if menu == "⚙️ Painel do Administrador":
    st.title("Painel de Controle - Acesso Restrito")
    st.write("Gerencie os acessos da sua equipe.")
    
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
                senha_salva = f"'{nova_senha}" if nova_senha.isdigit() else nova_senha
                novo_registro = pd.DataFrame([{"Usuario": novo_usuario, "Senha": senha_salva}])
                df_users_atualizado = pd.concat([df_users, novo_registro], ignore_index=True)
                salvar_novo_usuario(df_users_atualizado)
                st.success("✅ Funcionário cadastrado!")
        else:
            st.warning("Preencha todos os campos.")
            
    st.markdown("---")
    st.markdown("### Funcionários Cadastrados")
    df_mostra = carregar_usuarios()
    st.dataframe(df_mostra, use_container_width=True)

# ----- TELA DE UPLOAD -----
elif menu == "📂 Upload de Dados":
    st.title("Importação de Resultados PDF")
    st.write("Suba o arquivo do sistema. Os dados serão lidos, higienizados e salvos na Nuvem.")
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
                    df_puro = conn.read(worksheet="Página1", ttl=0).dropna(how="all") if not df_historico.empty else pd.DataFrame(columns=COLUNAS_DB)
                    df_final = pd.concat([df_puro, df_novo]).drop_duplicates(subset=['Data', 'Código_Paciente', 'Material_Exame', 'Unidade'])
                    salvar_dados(df_final)
                    st.success(f"✅ Sucesso! {len(df_novo)} registros processados e salvos na Nuvem.")
                else:
                    st.warning("Não foi possível encontrar dados válidos neste arquivo.")

# ----- TELA DASHBOARD BÁSICO -----
elif menu == "🏢 Análise por Unidade":
    st.title("Análise Geral de Culturas")
    
    if df_historico.empty:
        st.warning("⚠️ Não há dados no sistema.")
    else:
        st.markdown("### Filtros Rápidos")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            periodos = ["Todos"] + sorted(list(df_historico[df_historico['Mês/Ano'] != 'Desconhecido']['Mês/Ano'].unique()))
            periodo_sel = st.selectbox("📅 Mês/Ano:", periodos)
        with col_f2:
            unidades = ["Todas"] + sorted(list(df_historico['Unidade'].dropna().unique()))
            unidade_sel = st.selectbox("🏢 Unidade:", unidades)
        
        df_f = df_historico.copy()
        if periodo_sel != "Todos": df_f = df_f[df_f['Mês/Ano'] == periodo_sel]
        if unidade_sel != "Todas": df_f = df_f[df_f['Unidade'] == unidade_sel]
            
        t_pos = len(df_f[df_f['Resultado'] == 'Positivo'])
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Exames Encontrados", len(df_f))
        c2.metric("Positivos", t_pos)
        c3.metric("Negativos", len(df_f[df_f['Resultado'] == 'Negativo']))
        
        if t_pos > 0:
            df_pos = df_f[df_f['Resultado'] == 'Positivo']
            st.markdown("---")
            st.subheader("Porcentagem de Cada Bactéria")
            df_percent = df_pos['Bactéria'].value_counts(normalize=True).mul(100).round(2).reset_index()
            df_percent.columns = ['Microrganismo (Bactéria)', 'Porcentagem (%)']
            st.dataframe(df_percent, use_container_width=True)
            
            st.subheader("Gráfico de Positivos")
            fig_bac = px.bar(df_percent, x='Microrganismo (Bactéria)', y='Porcentagem (%)', text_auto=True, color='Microrganismo (Bactéria)', color_discrete_sequence=PALETA_CORES)
            st.plotly_chart(fig_bac, use_container_width=True)

# ----- TELA COMPARATIVO AVANÇADO -----
elif menu == "📈 Relatório Comparativo Avançado":
    st.title("Painel de Inteligência Analítica")
    
    if df_historico.empty:
        st.warning("⚠️ Não há dados salvos no sistema.")
    else:
        st.markdown('<div style="background-color: #F0F2F6; padding: 15px; border-radius: 10px;">', unsafe_allow_html=True)
        col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
        
        with col_filtro1:
            opcoes_mes = ["Todos os Meses"] + sorted(list(df_historico[df_historico['Mês/Ano'] != 'Desconhecido']['Mês/Ano'].unique()))
            mes_comparativo = st.selectbox("📅 Filtrar Mês:", opcoes_mes)
            
        with col_filtro2:
            opcoes_unidade = ["Todas as Unidades"] + sorted(list(df_historico['Unidade'].unique()))
            unidade_comparativo = st.selectbox("🏢 Filtrar Unidade:", opcoes_unidade)
            
        with col_filtro3:
            opcoes_exame = ["Todos os Exames"] + sorted(list(df_historico['Material_Exame'].unique()))
            exame_comparativo = st.selectbox("🧪 Filtrar Exame:", opcoes_exame)
        st.markdown('</div><br>', unsafe_allow_html=True)

        df_comp = df_historico.copy()
        if mes_comparativo != "Todos os Meses": df_comp = df_comp[df_comp['Mês/Ano'] == mes_comparativo]
        if unidade_comparativo != "Todas as Unidades": df_comp = df_comp[df_comp['Unidade'] == unidade_comparativo]
        if exame_comparativo != "Todos os Exames": df_comp = df_comp[df_comp['Material_Exame'] == exame_comparativo]

        df_pos_comp = df_comp[df_comp['Resultado'] == 'Positivo']

        if not df_pos_comp.empty:
            bacteria_top = df_pos_comp['Bactéria'].value_counts().idxmax()
            
            if mes_comparativo == "Todos os Meses":
                mes_pico = df_pos_comp['Mês/Ano'].value_counts().idxmax()
                texto_mes_pico = f"Pico: {mes_pico}"
            else:
                texto_mes_pico = f"Análise: {mes_comparativo}"
                
            c_m1, c_m2, c_m3 = st.columns(3)
            c_m1.metric("Total de Casos Positivos", len(df_pos_comp))
            c_m2.metric("Bactéria Mais Detectada 🦠", bacteria_top)
            c_m3.metric("Maior Volume de Casos 📈", texto_mes_pico)

            st.markdown("---")
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.subheader("Crescimento de Positivos ao Longo do Tempo")
                agrupado_tempo = df_pos_comp.groupby('Mês/Ano').size().reset_index(name='Casos')
                fig_linha = px.line(agrupado_tempo, x='Mês/Ano', y='Casos', markers=True, color_discrete_sequence=[COR_AZUL_BIC])
                fig_linha.update_traces(line=dict(width=4), marker=dict(size=10))
                st.plotly_chart(fig_linha, use_container_width=True)
                
            with col_g2:
                st.subheader(f"Incidência Bacteriana")
                agrupado_bac = df_pos_comp['Bactéria'].value_counts(normalize=True).mul(100).round(2).reset_index()
                agrupado_bac.columns = ['Bactéria', '%']
                fig_bar_bac = px.bar(agrupado_bac.head(5), x='%', y='Bactéria', orientation='h', text_auto=True, color='Bactéria', color_discrete_sequence=PALETA_CORES)
                fig_bar_bac.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_bar_bac, use_container_width=True)

            st.markdown("### Detalhamento Completo (Aplicando Filtros)")
            df_percent_final = df_pos_comp.groupby(['Unidade', 'Bactéria']).size().reset_index(name='Casos')
            df_percent_final['%'] = (df_percent_final['Casos'] / len(df_pos_comp) * 100).round(2)
            df_percent_final = df_percent_final.sort_values(by='%', ascending=False)
            st.dataframe(df_percent_final, use_container_width=True)

        else:
            st.info("Nenhum caso positivo encontrado para a combinação de filtros selecionada.")
