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

# ==========================================
# 2. CSS AVANÇADO (ANIMAÇÕES E PROTEÇÃO DARK MODE)
# ==========================================
st.markdown("""
    <style>
    /* Força botões, inputs, selects e uploaders a terem fundo claro e texto escuro sempre */
    [data-baseweb="input"], [data-baseweb="input"] input {
        background-color: #FFFFFF !important;
        color: #333333 !important;
        -webkit-text-fill-color: #333333 !important;
    }
    [data-baseweb="select"] > div { background-color: #FFFFFF !important; color: #333333 !important; }
    [data-testid="stFileUploaderDropzone"] { background-color: #F8F9FA !important; border: 2px dashed #002395 !important; }
    [data-testid="stFileUploaderDropzone"] * { color: #333333 !important; }
    
    /* Botões Primários Estilizados */
    div.stButton > button[kind="primary"] {
        background-color: #002395 !important; color: #FFFFFF !important;
        border-radius: 8px !important; border: none !important;
        font-weight: 600 !important; transition: all 0.3s ease !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #00155f !important; transform: translateY(-2px);
        box-shadow: 0 8px 15px rgba(0,35,149,0.3) !important;
    }

    /* Cards de Métricas */
    div[data-testid="metric-container"] {
        background-color: #FFFFFF !important; border: 1px solid #E5E7EB !important;
        padding: 20px !important; border-radius: 12px !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05) !important; border-left: 6px solid #002395 !important;
    }
    div[data-testid="metric-container"] label { color: #6B7280 !important; font-weight: 600 !important; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { color: #002395 !important; font-weight: 800 !important;}
    
    /* Títulos em Azul São Francisco */
    h1, h2, h3, h4, h5, h6 { color: #002395 !important; font-weight: 700 !important; }
    p, span, label { color: #333333 !important; }
    
    /* Abas do Painel */
    .stTabs [aria-selected="true"] { color: #002395 !important; border-bottom: 3px solid #002395 !important; }
    .stTabs [aria-selected="false"] { color: #808080 !important; }
    </style>
""", unsafe_allow_html=True)

COR_AZUL_BIC = '#002395'
COR_CINZA = '#808080'
PALETA_CORES = ['#002395', '#4A69BD', '#708ad4', '#808080', '#A6A6A6', '#C0C0C0', '#d9d9d9']

# ==========================================
# 3. FUNÇÕES DE LIMPEZA E PADRONIZAÇÃO
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
# 4. CONEXÃO COM GOOGLE SHEETS
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
        if df_users.empty: return pd.DataFrame(columns=["Usuario", "Senha", "Nivel_Acesso"])
        if "Nivel_Acesso" not in df_users.columns: df_users["Nivel_Acesso"] = "Administrador"
        df_users['Usuario'] = df_users['Usuario'].astype(str).str.strip()
        df_users['Senha'] = df_users['Senha'].astype(str).str.replace(r'\.0$', '', regex=True).str.lstrip("'").str.strip()
        return df_users
    except:
        return pd.DataFrame(columns=["Usuario", "Senha", "Nivel_Acesso"])

def salvar_novo_usuario(df_users):
    conn.update(worksheet="Usuarios", data=df_users)

# ==========================================
# 5. TELA DE LOGIN (COM BACKGROUND ANIMADO E FADE-UP)
# ==========================================
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'usuario' not in st.session_state: st.session_state['usuario'] = ""
if 'nivel_acesso' not in st.session_state: st.session_state['nivel_acesso'] = "Visualizador"

if not st.session_state['logado']:
    st.markdown("""
    <style>
    /* Animação Fundo Degradê Movendo (Super Leve) */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(-45deg, #e0e7ff, #ffffff, #f0f4ff, #dbeafe);
        background-size: 400% 400%;
        animation: gradientBG 15s ease infinite;
    }
    @keyframes gradientBG {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    [data-testid="stHeader"] { background-color: transparent !important; }
    
    /* Animação de Surgimento (Fade-Up) */
    @keyframes fadeUp {
        0% { opacity: 0; transform: translateY(40px); }
        100% { opacity: 1; transform: translateY(0); }
    }
    
    /* Estilização do Form de Login (Efeito Vidro) */
    [data-testid="stForm"] {
        background: rgba(255, 255, 255, 0.85) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border-radius: 20px !important;
        border: 1px solid rgba(255,255,255,0.8) !important;
        box-shadow: 0 20px 40px rgba(0, 35, 149, 0.1) !important;
        padding: 40px 30px !important;
        animation: fadeUp 1s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        opacity: 0; /* Começa invisível para a animação rodar */
    }
    </style>
    """, unsafe_allow_html=True)

    col_vazia_esq, col_login, col_vazia_dir = st.columns([1, 1.2, 1])
    with col_login:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        with st.form(key="login_form"):
            col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
            with col_logo2:
                try: st.image("logo.png", use_container_width=True)
                except: st.markdown("<h2 style='text-align: center; color:#002395;'>SÃO FRANCISCO</h2>", unsafe_allow_html=True)
            
            st.markdown("<h4 style='text-align: center; color: #555; margin-bottom:30px;'>Acesso ao Painel Analítico</h4>", unsafe_allow_html=True)
            
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
                    st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos. Acesso negado.")
    st.stop()

# Remove a animação do fundo depois de logado para não distrair na leitura dos gráficos
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background: #FAFAFA !important;
        animation: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 6. EXTRAÇÃO DO PDF 
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
# 7. MENU LATERAL
# ==========================================
try: st.sidebar.image("logo.png", use_container_width=True)
except: st.sidebar.empty() 

nivel_atual = st.session_state.get('nivel_acesso', 'Visualizador')
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

# ==========================================
# 8. TELAS DO SISTEMA
# ==========================================

# ----- TELA ADMIN -----
if menu == "⚙️ Painel do Administrador":
    st.title("⚙️ Painel de Controle Administrativo")
    st.markdown("Gerencie os acessos da sua equipe e os níveis de permissão no sistema.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["➕ Cadastrar Novo Funcionário", "📋 Usuários Cadastrados no Sistema"])
    
    with tab1:
        st.markdown("#### Criar Nova Credencial")
        with st.container(border=True):
            col1, col2, col3 = st.columns(3)
            with col1: 
                novo_usuario = st.text_input("Login do Funcionário (Ex: maria.silva):")
            with col2: 
                nova_senha = st.text_input("Senha de Acesso:", type="password")
            with col3:
                novo_nivel = st.selectbox("Nível de Permissão:", [
                    "Visualizador (Apenas Gráficos)", 
                    "Operador (Gráficos + Upload)", 
                    "Administrador (Acesso Total)"
                ])
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("Salvar Cadastro ✔️", type="primary", use_container_width=True):
                if novo_usuario and nova_senha:
                    df_users = carregar_usuarios()
                    if novo_usuario in df_users['Usuario'].values:
                        st.error("❌ Este login já existe no sistema.")
                    else:
                        senha_salva = f"'{nova_senha}" if nova_senha.isdigit() else nova_senha
                        nivel_salvo = novo_nivel.split(" ")[0]
                        novo_registro = pd.DataFrame([{"Usuario": novo_usuario, "Senha": senha_salva, "Nivel_Acesso": nivel_salvo}])
                        df_users_atualizado = pd.concat([df_users, novo_registro], ignore_index=True)
                        salvar_novo_usuario(df_users_atualizado)
                        st.success(f"✅ Funcionário cadastrado como {nivel_salvo}!")
                else:
                    st.warning("Preencha todos os campos antes de salvar.")
                    
    with tab2:
        st.markdown("#### Lista de Acessos")
        df_mostra = carregar_usuarios()
        st.dataframe(df_mostra, use_container_width=True, hide_index=True)

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
        st.info("⚠️ Não há dados no sistema. Faça o upload do primeiro PDF.")
    else:
        st.markdown('<div style="background-color: #FFFFFF; padding: 20px; border-radius: 10px; border: 1px solid #E6E9EF; margin-bottom: 20px;">', unsafe_allow_html=True)
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            periodos = ["Todos os Meses"] + sorted(list(df_historico[df_historico['Mês/Ano'] != 'Desconhecido']['Mês/Ano'].unique()))
            periodo_sel = st.selectbox("📅 Selecione o Mês:", periodos)
        with col_f2:
            unidades = ["Todas as Unidades"] + sorted(list(df_historico['Unidade'].unique()))
            unidade_sel = st.selectbox("🏢 Selecione a Unidade:", unidades)
        st.markdown('</div>', unsafe_allow_html=True)
        
        df_f = df_historico.copy()
        if periodo_sel != "Todos os Meses": df_f = df_f[df_f['Mês/Ano'] == periodo_sel]
        if unidade_sel != "Todas as Unidades": df_f = df_f[df_f['Unidade'] == unidade_sel]
            
        t_pos = len(df_f[df_f['Resultado'] == 'Positivo'])
        
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
                # O comando theme=None mata o bug do fundo preto no Dark Mode!
                fig_pizza.update_layout(template='plotly_white', margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig_pizza, use_container_width=True, theme=None)
                
            with c_graf2:
                st.markdown("#### 🧫 Frequência Bacteriana")
                df_percent = df_pos['Bactéria'].value_counts(normalize=True).mul(100).round(2).reset_index()
                df_percent.columns = ['Bactéria', '%']
                fig_bac = px.bar(df_percent, x='%', y='Bactéria', orientation='h', text_auto=True, color='Bactéria', color_discrete_sequence=PALETA_CORES)
                fig_bac.update_layout(template='plotly_white', yaxis={'categoryorder':'total ascending'}, margin=dict(t=20, b=20, l=20, r=20), showlegend=False)
                st.plotly_chart(fig_bac, use_container_width=True, theme=None)

            st.markdown("#### 📋 Detalhamento dos Pacientes (Positivos)")
            st.dataframe(df_pos[['Data', 'Unidade', 'Material_Exame', 'Bactéria', 'Indicados (S)', 'Resistentes (R)']], use_container_width=True, hide_index=True)

# ----- TELA COMPARATIVO AVANÇADO -----
elif menu == "📈 Relatório Comparativo Avançado":
    st.title("📈 Inteligência Analítica e Tendências")
    
    if df_historico.empty:
        st.info("⚠️ Não há dados salvos no sistema.")
    else:
        st.markdown('<div style="background-color: #FFFFFF; padding: 20px; border-radius: 10px; border: 1px solid #E6E9EF; margin-bottom: 20px;">', unsafe_allow_html=True)
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
        st.markdown('</div>', unsafe_allow_html=True)

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
                
            c_m1, c_m2, c_m3 = st.columns(3)
            c_m1.metric("Total de Positivos Filtrados", len(df_pos_comp))
            c_m2.metric("Bactéria Mais Detectada 🦠", bacteria_top)
            c_m3.metric("Indicador de Volume 📈", texto_mes_pico)

            st.markdown("<br>", unsafe_allow_html=True)
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.markdown("#### 📊 Crescimento de Positivos ao Longo do Tempo")
                agrupado_tempo = df_pos_comp.groupby('Mês/Ano').size().reset_index(name='Casos')
                fig_linha = px.area(agrupado_tempo, x='Mês/Ano', y='Casos', markers=True, color_discrete_sequence=[COR_AZUL_BIC])
                fig_linha.update_layout(template='plotly_white', margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig_linha, use_container_width=True, theme=None)
                
            with col_g2:
                st.markdown("#### 🎯 Top 5 Incidências Bacterianas")
                agrupado_bac = df_pos_comp['Bactéria'].value_counts(normalize=True).mul(100).round(2).reset_index()
                agrupado_bac.columns = ['Bactéria', '%']
                fig_bar_bac = px.bar(agrupado_bac.head(5), x='%', y='Bactéria', orientation='h', text_auto=True, color='Bactéria', color_discrete_sequence=PALETA_CORES)
                fig_bar_bac.update_layout(template='plotly_white', yaxis={'categoryorder':'total ascending'}, margin=dict(t=20, b=20, l=20, r=20), showlegend=False)
                st.plotly_chart(fig_bar_bac, use_container_width=True, theme=None)

            st.markdown("#### 📌 Detalhamento Estratégico (% Do Total Filtrado)")
            df_percent_final = df_pos_comp.groupby(['Unidade', 'Material_Exame', 'Bactéria']).size().reset_index(name='Casos')
            df_percent_final['%'] = (df_percent_final['Casos'] / len(df_pos_comp) * 100).round(2)
            df_percent_final = df_percent_final.sort_values(by='%', ascending=False)
            st.dataframe(df_percent_final, use_container_width=True, hide_index=True)

        else:
            st.info("Não houve nenhum registro positivo encontrado com os filtros selecionados acima.")
