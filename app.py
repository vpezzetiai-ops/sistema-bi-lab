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
# 1. CONFIGURAÇÕES INICIAIS
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
# 3. CONEXÃO COM GOOGLE SHEETS E FUNÇÕES B64
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)
COLUNAS_DB = ["Data", "Código_Paciente", "Idade", "Sexo", "Material_Exame", "Resultado", "Bactéria", "Indicados (S)", "Resistentes (R)", "Unidade", "Período_Arquivo"]

def carregar_dados_salvos():
    try:
        df = conn.read(worksheet="Página1", ttl=0).dropna(how="all")
        if df.empty: return pd.DataFrame(columns=COLUNAS_DB)
        
        # Garante compatibilidade com planilhas antigas
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

# ==========================================
# FUNÇÃO: GERAR DADOS DE DEMONSTRAÇÃO
# ==========================================
def gerar_dados_teste():
    exames_mock = ["[URAB] Urina", "[HEMO] Sangue", "[SWAB] Secreção", "[LCR] Líquido"]
    bacterias_mock = ["Escherichia coli", "Staphylococcus aureus", "Klebsiella sp.", "Pseudomonas sp.", "Proteus sp."]
    sexos_mock = ["Feminino", "Masculino"]
    
    novos_dados = []
    for _ in range(100): # Gera 100 laudos fictícios
        res = random.choice(["Positivo", "Positivo", "Negativo"]) # Mais chance de positivo para os gráficos
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
# 5. TELA DE LOGIN 
# ==========================================
if not st.session_state['logado']:
    
    video_b64 = get_base64_file("video_apresentacao.mp4")
    
    if video_b64:
        st.markdown(f'''
        <video autoplay loop muted playsinline style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -999; object-fit: cover; object-position: center; filter: brightness(0.85) contrast(1.15);">
            <source src="data:video/mp4;base64,{video_b64}" type="video/mp4">
        </video>
        ''', unsafe_allow_html=True)

    st.markdown("""
    <style>
    @keyframes fadeInDown { 0% { opacity: 0; transform: translateY(-80px); } 100% { opacity: 1; transform: translateY(0); } }

    html, body, [data-testid="stAppViewContainer"], .block-container { 
        overflow: hidden !important; padding-top: 0rem !important; padding-bottom: 0rem !important; margin: 0 !important;
    }
    .stApp { background: transparent !important; }
    [data-testid="stHeader"] { background: transparent !important; display: none !important; }
    
    [data-testid="stForm"] {
        background: rgba(255, 255, 255, 0.2) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border-radius: 15px !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        box-shadow: 0px 15px 30px rgba(0,0,0,0.6) !important;
        padding: 25px 20px 15px 20px !important;
        margin-top: 8vh !important; 
        z-index: 10; max-width: 330px; margin-left: auto; margin-right: auto;
        animation: fadeInDown 1.2s ease-out forwards;
    }
    
    [data-testid="stForm"] p, [data-testid="stForm"] label, [data-testid="stForm"] div { color: #111827 !important; font-weight: 600; text-shadow: 0px 1px 2px rgba(255,255,255,0.8) !important; }
    
    input[type="text"], input[type="password"] {
        background-color: rgba(255, 255, 255, 0.95) !important; color: #111827 !important; -webkit-text-fill-color: #111827 !important;
        border: 1px solid rgba(255, 255, 255, 0.8) !important; border-radius: 8px !important; padding: 10px !important;
    }
    
    div.stButton > button {
        background-color: #002395 !important; color: #FFFFFF !important; border: none !important; border-radius: 8px !important; 
        padding: 10px !important; margin-top: 5px !important; box-shadow: 0px 4px 15px rgba(0, 35, 149, 0.4) !important;
    }
    div.stButton > button * { color: #FFFFFF !important; font-weight: 900 !important; font-size: 16px !important; }
    
    hr.custom-divider { border: 0; height: 1px; background: linear-gradient(to right, rgba(255,255,255,0), rgba(255,255,255,0.8), rgba(255,255,255,0)); margin: 15px 0 10px 0; }
    </style>
    """, unsafe_allow_html=True)

    col_vazia_esq, col_login, col_vazia_dir = st.columns([1, 1, 1]) 
    
    with col_login:
        with st.form(key="login_form"):
            st.markdown("<h3 style='text-align: center; color:#002395 !important; font-weight: 900; margin-bottom: 20px; text-shadow: 0px 0px 15px rgba(255,255,255,0.8);'>Sistema BI - Laboratorial</h3>", unsafe_allow_html=True)
            
            usuario_input = st.text_input("👤 Nome de Usuário:")
            senha_input = st.text_input("🔑 Senha de Acesso:", type="password")
            lembrar_senha = st.checkbox("Lembrar senha (Habilitar preenchimento)")
            
            submit_button = st.form_submit_button("Fazer Login 🚀", type="primary", use_container_width=True)
            st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
            
            assinatura_b64 = get_base64_file("assinatura.png")
            if assinatura_b64:
                st.markdown(f'''
                    <div style="text-align: center; padding-bottom: 5px;">
                        <p style="color: #4B5563; font-size: 9px; font-weight: 800; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 2px;">Desenvolvido Por</p>
                        <img src="data:image/png;base64,{assinatura_b64}" style="max-height: 45px; max-width: 100%; object-fit: contain; margin: 0 auto; display: block;">
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
# 6. TELA DO SISTEMA (DASHBOARD)
# ==========================================
else:
    # CSS dinâmico: Funciona perfeitamente no Dark Mode!
    st.markdown("""
        <style>
        video { display: none !important; }
        html, body, [data-testid="stAppViewContainer"], .block-container { overflow: auto !important; }
        .stApp { background-image: none !important; animation: none !important;}
        header[data-testid="stHeader"] { display: flex !important;}
        
        div.stButton > button { background-color: #002395 !important; border: none !important; }
        div.stButton > button * { color: #FFFFFF !important; font-weight: bold !important; }
        </style>
    """, unsafe_allow_html=True)

    # Botão Injetado via Javascript para imprimir em PDF
    st.components.v1.html("""
        <script>
        function printPDF() { window.parent.print(); }
        </script>
        <button onclick="printPDF()" style="background-color:#002395;color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;font-weight:bold;width:100%;">🖨️ Exportar Tela para PDF</button>
    """, height=50)

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

    st.sidebar.markdown("<h3 style='text-align: center; color:#002395;'>Sistema BI - Laboratorial</h3>", unsafe_allow_html=True)
    nivel_atual = st.session_state.get('nivel_acesso', 'Visualizador')
    unid_perm = st.session_state.get('unidades_permitidas', 'Todas')

    st.sidebar.markdown(f"### 👋 Olá, **{st.session_state['usuario'].capitalize()}**")
    st.sidebar.markdown(f"<span style='color:#002395; font-weight:bold;'>• {nivel_atual}</span>", unsafe_allow_html=True)
    st.sidebar.markdown("---")

    opcoes_menu = ["🏢 Análise por Unidade", "📈 Relatório Comparativo", "🧬 Demografia (Idade e Sexo)"]
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
        
        if unid_perm != "Todas" and st.session_state['usuario'] != "vhpezzeti":
            unidades_liberadas = [u.strip() for u in unid_perm.split(",")]
            df_historico = df_historico[df_historico['Unidade'].isin(unidades_liberadas)]

    # ========================== MÓDULOS DO DASHBOARD ==========================
    if menu == "⚙️ Painel do Administrador":
        st.title("⚙️ Painel de Controle Administrativo")
        
        if st.button("🧪 Gerar 100 Dados de Demonstração (MOCK)", use_container_width=True):
            df_mock = gerar_dados_teste()
            df_atual = conn.read(worksheet="Página1", ttl=0).dropna(how="all")
            df_novo = pd.concat([df_atual, df_mock])
            salvar_dados(df_novo)
            st.success("✅ 100 laudos fictícios foram injetados no sistema com sucesso!")
            time.sleep(2)
            st.rerun()

        tab1, tab2, tab3 = st.tabs(["➕ Cadastrar Novo", "✏️ Editar / Excluir", "📋 Lista de Acessos"])
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
        with tab3: st.dataframe(df_users_adm)

    elif menu == "📂 Upload de Dados":
        st.title("📂 Importação de PDF")
        arq = st.file_uploader("Arraste o PDF", type=['pdf', 'txt'])
        if arq and st.button("Processar e Salvar"):
            txt = ""
            if arq.name.endswith('.pdf'):
                for p in PyPDF2.PdfReader(arq).pages: txt += p.extract_text() + "\n"
            else: txt = arq.read().decode("utf-8")
            df_novo = extrair_dados_pdf(txt)
            if not df_novo.empty:
                df_puro = conn.read(worksheet="Página1", ttl=0).dropna(how="all")
                salvar_dados(pd.concat([df_puro, df_novo]).drop_duplicates(subset=['Data', 'Código_Paciente', 'Material_Exame', 'Unidade']))
                st.success(f"✅ {len(df_novo)} registros salvos!")
            else: st.error("Falha ao ler dados.")

    elif menu == "🏢 Análise por Unidade":
        st.title("🏢 Análise Geral Multifiltros")
        if df_historico.empty: st.info("Sem dados.")
        else:
            c1, c2, c3 = st.columns(3)
            # Filtros Múltiplos
            meses_disp = sorted(list(df_historico[df_historico['Mês/Ano'] != 'Desconhecido']['Mês/Ano'].unique()))
            meses_sel = c1.multiselect("📅 Meses Analisados", meses_disp, default=meses_disp)
            
            unid_disp = sorted(list(df_historico['Unidade'].unique()))
            unid_sel = c2.multiselect("🏢 Unidades", unid_disp, default=unid_disp)
            
            exame_disp = sorted(list(df_historico['Material_Exame'].unique()))
            exame_sel = c3.multiselect("🧪 Exames", exame_disp, default=exame_disp)
            
            df_f = df_historico[df_historico['Mês/Ano'].isin(meses_sel) & df_historico['Unidade'].isin(unid_sel) & df_historico['Material_Exame'].isin(exame_sel)]
            
            if df_f.empty: st.warning("Nenhum dado encontrado para esta combinação.")
            else:
                t_pos = len(df_f[df_f['Resultado'] == 'Positivo'])
                t_neg = len(df_f[df_f['Resultado'] == 'Negativo'])
                qtd_meses = len(meses_sel) if len(meses_sel) > 0 else 1
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total de Exames", len(df_f))
                m2.metric("Positivos 🦠", t_pos)
                m3.metric("Negativos 🛡️", t_neg)
                m4.metric("Média / Mês Selecionado", round(len(df_f) / qtd_meses, 1))

                if t_pos > 0:
                    df_pos = df_f[df_f['Resultado'] == 'Positivo']
                    
                    st.markdown("---")
                    g1, g2 = st.columns(2)
                    with g1:
                        st.markdown("#### 📊 % Positivos x Negativos")
                        st.plotly_chart(px.pie(df_f, names='Resultado', hole=0.5, color='Resultado', color_discrete_map={'Positivo': COR_AZUL_BIC, 'Negativo': COR_CINZA}), use_container_width=True)
                    with g2:
                        st.markdown("#### 🧫 % Ocorrência Bacteriana")
                        df_pct = df_pos['Bactéria'].value_counts(normalize=True).mul(100).round(2).reset_index()
                        df_pct.columns = ['Bactéria', '%']
                        st.plotly_chart(px.bar(df_pct, x='%', y='Bactéria', orientation='h', text_auto=True, color='Bactéria', color_discrete_sequence=PALETA_CORES).update_layout(yaxis={'categoryorder':'total ascending'}), use_container_width=True)

                    st.markdown("#### 📋 Detalhamento dos Pacientes Positivos")
                    st.dataframe(df_pos[['Data', 'Código_Paciente', 'Idade', 'Sexo', 'Unidade', 'Material_Exame', 'Bactéria', 'Indicados (S)', 'Resistentes (R)']], use_container_width=True, hide_index=True)

    elif menu == "📈 Relatório Comparativo":
        st.title("📈 Tendências e Campeões")
        if not df_historico.empty:
            df_pos_comp = df_historico[df_historico['Resultado'] == 'Positivo']
            if not df_pos_comp.empty:
                b_top = df_pos_comp['Bactéria'].value_counts().idxmax()
                exame_top = df_pos_comp['Material_Exame'].value_counts().idxmax()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Bactéria de Maior Risco", b_top)
                c2.metric("Exame com Mais Positivos", exame_top)
                c3.metric("Mês com Mais Casos", df_pos_comp['Mês/Ano'].value_counts().idxmax())
                
                st.markdown("#### 📉 Curva Epidemiológica")
                agrupado = df_pos_comp.groupby('Mês/Ano').size().reset_index(name='Casos')
                st.plotly_chart(px.area(agrupado, x='Mês/Ano', y='Casos', markers=True, color_discrete_sequence=[COR_AZUL_BIC]), use_container_width=True)
                
                st.markdown("#### 🏆 Top Bactérias por Tipo de Exame")
                top_b_exame = df_pos_comp.groupby(['Material_Exame', 'Bactéria']).size().reset_index(name='Qtd').sort_values(['Material_Exame', 'Qtd'], ascending=[True, False])
                st.dataframe(top_b_exame.groupby('Material_Exame').head(2), use_container_width=True, hide_index=True)

    elif menu == "🧬 Demografia (Idade e Sexo)":
        st.title("🧬 Análise Demográfica de Infecções")
        if df_historico.empty: st.info("Sem dados.")
        else:
            df_demo = df_historico[(df_historico['Resultado'] == 'Positivo') & (df_historico['Idade'] != 'Não Informada')]
            if df_demo.empty: st.warning("⚠️ Você precisa gerar dados de teste ou fazer upload de PDFs que contenham idade.")
            else:
                df_demo['Idade'] = pd.to_numeric(df_demo['Idade'])
                
                d1, d2 = st.columns(2)
                with d1:
                    st.markdown("#### 👥 Infecções por Sexo")
                    st.plotly_chart(px.pie(df_demo, names='Sexo', hole=0.4, color_discrete_sequence=['#ff4b4b', '#002395']), use_container_width=True)
                with d2:
                    st.markdown("#### 📊 Faixa Etária dos Positivos")
                    st.plotly_chart(px.histogram(df_demo, x='Idade', nbins=10, color_discrete_sequence=[COR_AZUL_BIC], text_auto=True), use_container_width=True)
