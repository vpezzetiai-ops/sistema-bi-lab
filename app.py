import streamlit as st
import pandas as pd
import plotly.express as px
import re
import PyPDF2
from supabase import create_client, Client
import time
import base64
import os
from datetime import datetime
import io

# ==========================================
# 1. CONFIGURAÇÕES GERAIS E ARQUIVOS
# ==========================================
st.set_page_config(page_title="S.I.B.C. Enterprise", layout="wide", initial_sidebar_state="expanded")

ARQUIVO_VIDEO_FUNDO = "video.mp4"
ARQUIVO_LOGO_LOGIN = "logoprograma.png" 
ARQUIVO_ASSINATURA = "Gemini_Generated_Image_s8ldfcs8ldfcs8ld-removebg-preview.png" 
ARQUIVO_LOGO_MENU = "logoprograma.png" 

COR_POSITIVO = '#f43f5e'
COR_NEGATIVO = '#3b82f6'
UNIDADES_OFICIAIS = ["1 - Serra Negra", "3 - AME", "4 - Amparo Unidade 4", "5 - Monte Alegre", "6 - Lindóia", "9 - Cenam", "10 - Amparo Unidade BPA", "12 - Águas de Lindóia", "Sede / Sem Unidade"]

def get_base64_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f: return base64.b64encode(f.read()).decode()
    return None

# ==========================================
# 2. CONEXÃO COM O SUPABASE
# ==========================================
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_connection()
except Exception as e:
    st.error("⚠️ Erro ao conectar com o Supabase. Verifique o arquivo .streamlit/secrets.toml.")
    st.stop()

# ==========================================
# 3. MOTOR DE DADOS: TEXTO DESESTRUTURADO (PDF/TXT)
# ==========================================
def padronizar_unidade(unidade):
    if pd.isna(unidade) or str(unidade).strip() == "" or "Não Informada" in str(unidade): return "Sede / Sem Unidade"
    numeros = re.findall(r'\d+', str(unidade))
    if not numeros: return "Sede / Sem Unidade"
    mapa = {"1": "1 - Serra Negra", "3": "3 - AME", "4": "4 - Amparo Unidade 4", "5": "5 - Monte Alegre", "6": "6 - Lindóia", "9": "9 - Cenam", "10": "10 - Amparo Unidade BPA", "12": "12 - Águas de Lindóia"}
    return mapa.get(str(int(numeros[0])), "Excluir")

def padronizar_bacteria(nome):
    if pd.isna(nome) or nome == "N/A": return "N/A"
    n = str(nome).strip().lower()
    for bac in ["coli", "escherichia"]: 
        if bac in n: return "Escherichia coli"
    for bac_sp in ["proteus", "enterobacter", "pseudomonas", "klebsiella", "staphylococcus", "streptococcus", "enterococcus", "acinetobacter", "citrobacter"]:
        if bac_sp in n: return f"{bac_sp.capitalize()} sp."
    return str(nome).strip().title()

def padronizar_material(material):
    if pd.isna(material): return "Não Informado"
    mat_limpo = re.sub(r'\[.*?\]\s*', '', str(material))
    mat_limpo = re.sub(r'[\.\d:]+$', '', mat_limpo) 
    return mat_limpo.strip().title() if mat_limpo.strip() else "Não Informado"

def extrair_dados_pdf(texto_bruto):
    dados = []
    periodo_doc = "Período Indefinido"
    match_per = re.search(r'PER[ÍI]ODO DE (\d{2}/\d{2}/\d{4}) [AÀ] (\d{2}/\d{2}/\d{4})', texto_bruto, re.IGNORECASE)
    if match_per: periodo_doc = f"{match_per.group(1)} a {match_per.group(2)}"

    # NOVO: Corta os pacientes EXATAMENTE onde tem "Data + Código Numérico" 
    # Isso garante que ele puxe TODOS os pacientes da lista, sem pular nenhum.
    blocos = re.split(r'(?=\b\d{2}/\d{2}/\d{4}\s+\d+)', texto_bruto)
    
    for bloco in blocos:
        if len(bloco.strip()) < 20: continue 
        
        # 1. CÓDIGO DO PACIENTE (Força pegar só números, ignorando a palavra 'Nome')
        match_header = re.search(r'(\d{2}/\d{2}/\d{4})\s+(\d+)', bloco)
        if not match_header: continue
        data_pac = match_header.group(1)
        cod_pac = match_header.group(2)

        # 2. SEXO INFERIDO PELO NOME (IA Simbólica)
        sexo_pac = "Não Informado"
        match_nome = re.search(r'Nome:\s*([^\n]+)', bloco, re.IGNORECASE)
        if match_nome:
            nome = match_nome.group(1).strip().upper()
            primeiro_nome = nome.split()[0].replace(' ', '')
            if primeiro_nome.endswith('A') or primeiro_nome in ['LOURDES', 'STHEFANIE', 'ALINE', 'VIVIANE', 'CARMEM', 'ESTER', 'RUTH', 'STHEF', 'SUELI', 'ROSELI', 'CLEIDE', 'IVONE', 'MIRIAN', 'RAQUEL', 'ELISABETE', 'BEATRIZ', 'IRIS']:
                sexo_pac = "Feminino"
            elif primeiro_nome.endswith('O') or primeiro_nome in ['LUIS', 'GABRIEL', 'DANIEL', 'IGOR', 'VITOR', 'ARTHUR', 'DAVI', 'RAFAEL', 'MIGUEL', 'LUCAS', 'GIOVANI', 'KAUE', 'THIAGO', 'WILLIAN', 'JEFFERSON']:
                sexo_pac = "Masculino"

        # 3. IDADE (Flexível)
        idade_pac = "Não Informada"
        match_idade = re.search(r'(?:Idade|I\s*d\s*a\s*d\s*e)[\s:=]*(\d+)', bloco, re.IGNORECASE)
        if match_idade: idade_pac = match_idade.group(1)

        # 4. UNIDADE (Lê o texto inteiro da unidade e converte)
        unidade_pac = "Sede / Sem Unidade"
        match_unidade = re.search(r'Unidade:\s*([^\n]+)', bloco, re.IGNORECASE)
        if match_unidade:
            u_str = match_unidade.group(1).upper()
            if "MONTE ALEGRE" in u_str: unidade_pac = "5 - Monte Alegre"
            elif "SERRA NEGRA" in u_str: unidade_pac = "1 - Serra Negra"
            elif "AME" in u_str: unidade_pac = "3 - AME"
            elif "AMPARO" in u_str and "4" in u_str: unidade_pac = "4 - Amparo Unidade 4"
            elif "LIND" in u_str and "AGUAS" not in u_str and "ÁGUAS" not in u_str: unidade_pac = "6 - Lindóia"
            elif "CENAM" in u_str: unidade_pac = "9 - Cenam"
            elif "BPA" in u_str: unidade_pac = "10 - Amparo Unidade BPA"
            elif "AGUAS" in u_str or "ÁGUAS" in u_str: unidade_pac = "12 - Águas de Lindóia"

        if unidade_pac == "Excluir": continue 

        linha = {
            "data_exame": data_pac, "codigo_paciente": cod_pac, 
            "idade": idade_pac, "sexo": sexo_pac, "material_exame": "Não Informado", 
            "resultado": "Negativo", "bacteria": "N/A", 
            "indicados_s": "", "resistentes_r": "", 
            "unidade": unidade_pac, "periodo_arquivo": periodo_doc
        }
        
        # Limpa quebras de linha que o PDF joga no meio das palavras (ex: micro-or ganismos)
        bloco_limpo = re.sub(r'\s+', ' ', bloco) 
        
        # 5. MATERIAL DO EXAME (Mapeamento Direto)
        if "URO1" in bloco_limpo or "URINA" in bloco_limpo.upper(): linha["material_exame"] = "Urina"
        elif "HEMOCULTURA" in bloco_limpo.upper() or "SANGUE" in bloco_limpo.upper(): linha["material_exame"] = "Sangue"
        elif "SECRE" in bloco_limpo.upper(): linha["material_exame"] = "Secreção"
        elif "FEZES" in bloco_limpo.upper() or "COPRO" in bloco_limpo.upper(): linha["material_exame"] = "Fezes"
        else:
            match_mat = re.search(r'(?:MAT(?:ERIAL)?|AMOSTRA)[\s:=]+([A-Za-zÀ-ÿ\s]+?)(?:(?=RES|M[EÉ]TODO|DATA|IDADE|UNIDADE|\n|1:|\.1:|$))', bloco, re.IGNORECASE)
            if match_mat: linha["material_exame"] = padronizar_material(match_mat.group(1))
        
        # 6. RESULTADO E BACTÉRIA
        if re.search(r'N[ãa]o\s+houve\s+desenvolvimento', bloco_limpo, re.IGNORECASE) or "ausência" in bloco_limpo.lower() or "ausentes" in bloco_limpo.lower():
            linha["resultado"] = "Negativo"
        else:
            linha["resultado"] = "Positivo"
            
            # Tenta achar a bactéria pelo padrão primário
            regex_bac = r'(?i:identificado|MIC|isolado\s*\d*|\b1|\.1|aer[oó]bia[^:]*|anaer[oó]bia[^:]*)\s*:\s*([A-Z][a-z]{2,}(?:\s+[a-z]{2,})?(?:\s+sp\.?)?)'
            match_bac = re.search(regex_bac, bloco_limpo)
            
            if match_bac:
                bac_str = match_bac.group(1).replace(":", "").strip()
                if "Não houve" not in bac_str and "Aplic" not in bac_str: 
                    linha["bacteria"] = padronizar_bacteria(bac_str)
            
            # PLANO B: Caçador de Bactérias (varredura forçada)
            if linha["bacteria"] == "N/A" or linha["bacteria"] == "":
                lista_bacterias = ["escherichia coli", "klebsiella", "proteus", "pseudomonas", "staphylococcus", "streptococcus", "enterococcus", "enterobacter", "acinetobacter", "citrobacter", "morganella", "salmonella"]
                for bac in lista_bacterias:
                    if bac in bloco_limpo.lower():
                        linha["bacteria"] = padronizar_bacteria(bac)
                        break
                        
        # 7. ANTIBIOGRAMA (Sensíveis S e Resistentes R)
        sensiveis, resistentes = [], []
        matches_atb = re.findall(r'([A-Z]{2,5})\d*[\s:=]+([SR])\b', bloco_limpo)
        for atb, status in matches_atb:
            if status == 'S': sensiveis.append(atb)
            elif status == 'R': resistentes.append(atb)
            
        linha["indicados_s"] = ", ".join(sorted(list(set(sensiveis))))
        linha["resistentes_r"] = ", ".join(sorted(list(set(resistentes))))
        
        dados.append(linha)
            
    return pd.DataFrame(dados)

# ==========================================
# 3.1. MOTOR DE DADOS: PLANILHAS ESTRUTURADAS (EXCEL/CSV)
# ==========================================
def processar_planilha(file):
    try:
        # Lê o arquivo dependendo da extensão
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            # engine=None faz o pandas usar o openpyxl (xlsx), xlrd (xls) ou odf (ods) automaticamente
            df = pd.read_excel(file, engine=None) 
            
        # Padroniza nomes das colunas lidas para minúsculo e sem espaços, para facilitar o "match"
        df.columns = [str(c).strip().lower().replace(" ", "_").replace("-", "_").replace(".", "") for c in df.columns]
        
        # Mapeamento Flexível de Colunas (O que vem do Excel -> Como o Supabase espera)
        mapeamento = {
            'data': 'data_exame', 'data_exame': 'data_exame', 'data_do_exame': 'data_exame', 'dataexame': 'data_exame',
            'codigo': 'codigo_paciente', 'codigo_paciente': 'codigo_paciente', 'cod': 'codigo_paciente', 'paciente_id': 'codigo_paciente',
            'idade': 'idade',
            'sexo': 'sexo', 'genero': 'sexo',
            'material': 'material_exame', 'material_exame': 'material_exame', 'exame': 'material_exame',
            'resultado': 'resultado', 'status': 'resultado',
            'bacteria': 'bacteria', 'patogeno': 'bacteria', 'micro_organismo': 'bacteria',
            'indicados_s': 'indicados_s', 'sensiveis': 'indicados_s', 'antibiograma_s': 'indicados_s',
            'resistentes_r': 'resistentes_r', 'resistentes': 'resistentes_r', 'antibiograma_r': 'resistentes_r',
            'unidade': 'unidade', 'local': 'unidade', 'posto': 'unidade',
            'periodo': 'periodo_arquivo', 'periodo_arquivo': 'periodo_arquivo'
        }
        
        df = df.rename(columns=mapeamento)
        
        # Garante que todas as colunas necessárias existam (mesmo se vazias)
        colunas_obrigatorias = ["data_exame", "codigo_paciente", "idade", "sexo", "material_exame", "resultado", "bacteria", "indicados_s", "resistentes_r", "unidade", "periodo_arquivo"]
        for col in colunas_obrigatorias:
            if col not in df.columns:
                df[col] = "Não Informado" if col not in ["indicados_s", "resistentes_r"] else ""
                
        # Força tipos string e limpa NaN
        df = df[colunas_obrigatorias]
        df = df.fillna("Não Informado")
        
        # Padroniza dados
        df['codigo_paciente'] = df['codigo_paciente'].astype(str)
        df['unidade'] = df['unidade'].apply(padronizar_unidade)
        
        # Exclui linhas marcadas como "Excluir" pela padronização da unidade
        df = df[df['unidade'] != "Excluir"]
        
        return df
    
    except Exception as e:
        st.error(f"Erro ao ler a planilha: {e}")
        return pd.DataFrame()


# ==========================================
# 4. CONTROLE DE SESSÃO
# ==========================================
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'usuario' not in st.session_state: st.session_state['usuario'] = ""
if 'nivel_acesso' not in st.session_state: st.session_state['nivel_acesso'] = "Visualizador"
if 'unidades_permitidas' not in st.session_state: st.session_state['unidades_permitidas'] = "Todas"

# ==========================================
# 5. TELA DE LOGIN
# ==========================================
if not st.session_state['logado']:
    
    video_fundo_b64 = get_base64_file(ARQUIVO_VIDEO_FUNDO)
    if video_fundo_b64:
        st.markdown(f'''
        <video autoplay loop muted playsinline style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; object-fit: cover; z-index: -999; filter: brightness(0.3) contrast(1.2);">
            <source src="data:video/mp4;base64,{video_fundo_b64}" type="video/mp4">
        </video>
        ''', unsafe_allow_html=True)

    st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    .block-container { padding-top: 5vh !important; max-width: 100% !important; }
    
    [data-testid="stForm"] {
        background: rgba(15, 23, 42, 0.7) !important;
        backdrop-filter: blur(20px) !important; -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-top: 1px solid rgba(0, 238, 255, 0.3) !important;
        border-radius: 16px !important;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.8) !important;
        padding: 40px !important;
    }
    
    [data-testid="stForm"] p { color: #94a3b8 !important; font-weight: 600; font-size: 14px;}
    
    [data-testid="stFormSubmitButton"] button {
        background: linear-gradient(90deg, #0284c7, #2563eb) !important; color: white !important;
        border: none !important; border-radius: 8px !important; padding: 10px !important;
        font-weight: bold !important; letter-spacing: 1px !important; width: 100% !important;
        transition: all 0.3s ease !important; margin-top: 15px !important; box-shadow: 0 4px 15px rgba(37, 99, 235, 0.4) !important;
    }
    [data-testid="stFormSubmitButton"] button:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(37, 99, 235, 0.6) !important; }
    </style>
    """, unsafe_allow_html=True)

    col_vazia1, col_centro, col_vazia2 = st.columns([1, 1.2, 1])

    with col_centro:
        logo_b64 = get_base64_file(ARQUIVO_LOGO_LOGIN)
        if logo_b64:
            st.markdown(f'<div style="text-align: center; margin-bottom: 20px;"><img src="data:image/png;base64,{logo_b64}" style="height: 120px; filter: drop-shadow(0 10px 15px rgba(0,0,0,0.8));"></div>', unsafe_allow_html=True)
        
        with st.form(key="login_form"):
            st.markdown("<h2 style='text-align: center; color: white; margin-bottom: 5px; font-weight: 800; letter-spacing: 2px;'>S.I.B.C.</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #00eeff; margin-bottom: 30px; font-size: 12px; letter-spacing: 1px; font-weight: bold;'>SISTEMA INTEGRADO DE BIOLOGIA COMPUTACIONAL</p>", unsafe_allow_html=True)
            
            usuario_input = st.text_input("Identificação:")
            senha_input = st.text_input("Senha de Acesso:", type="password")
            submit_button = st.form_submit_button("AUTENTICAR")
            
            if submit_button:
                try:
                    resposta = supabase.table("usuarios").select("*").eq("usuario", usuario_input).execute()
                    usuarios_encontrados = resposta.data
                    
                    if len(usuarios_encontrados) > 0 and str(usuarios_encontrados[0]['senha']) == str(senha_input):
                        st.session_state['logado'] = True
                        st.session_state['usuario'] = usuario_input
                        st.session_state['nivel_acesso'] = usuarios_encontrados[0]['nivel_acesso']
                        st.session_state['unidades_permitidas'] = usuarios_encontrados[0]['unidades_permitidas']
                        st.rerun()
                    else:
                        st.error("❌ Credenciais inválidas.")
                except Exception as e:
                    st.error(f"Erro de comunicação com o banco de dados. {e}")

        assinatura_b64 = get_base64_file(ARQUIVO_ASSINATURA)
        if assinatura_b64:
            st.markdown(f'<div style="text-align: center; margin-top: 30px;"><img src="data:image/png;base64,{assinatura_b64}" style="height: 45px; opacity: 0.7;"></div>', unsafe_allow_html=True)

    st.stop()

# ==========================================
# 6. SISTEMA INTERNO E CSS DE IMPRESSÃO
# ==========================================
else:
    st.markdown("""
        <style>
        .stApp { background-color: #0b1120 !important; color: #f8fafc !important; }
        section[data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #1e293b !important; }
        
        div[data-testid="metric-container"] { background: #1e293b !important; border-left: 4px solid #3b82f6 !important; padding: 20px !important; border-radius: 8px !important; box-shadow: 0 4px 6px rgba(0,0,0,0.3) !important; }
        div[data-testid="metric-container"] label { color: #94a3b8 !important; font-size: 14px !important;}
        div[data-testid="metric-container"] div { color: white !important; }
        
        @media print {
            @page { size: A4 landscape !important; margin: 10mm !important; }
            body, html, .stApp, .main, .block-container { background-color: white !important; color: black !important; }
            [data-testid="stSidebar"], header, button, form { display: none !important; }
            .stDataFrame, table { width: 100% !important; }
            th { background-color: #f1f5f9 !important; color: black !important; border: 1px solid #cbd5e1 !important; }
            td { border: 1px solid #cbd5e1 !important; color: black !important; }
            div[data-testid="metric-container"] { background: white !important; border: 1px solid #cbd5e1 !important; border-left: 5px solid #3b82f6 !important; }
            div[data-testid="metric-container"] div, div[data-testid="metric-container"] label { color: black !important; }
        }
        </style>
    """, unsafe_allow_html=True)

    st.components.v1.html("""<script>function doPrint() { window.parent.print(); }</script><button onclick="doPrint()" style="background: #2563eb; color:white; padding:12px; border:none; border-radius:6px; cursor:pointer; font-weight:bold; width:100%; box-shadow: 0 4px 6px rgba(0,0,0,0.2);">🖨️ Exportar Relatório Oficial (PDF)</button>""", height=50)

    df_reais = pd.DataFrame()
    try:
        res = supabase.table("laudos").select("*").execute()
        if len(res.data) > 0:
            df_todos_dados = pd.DataFrame(res.data)
            df_todos_dados = df_todos_dados.rename(columns={
                "data_exame": "Data", "codigo_paciente": "Código_Paciente", "idade": "Idade", "sexo": "Sexo",
                "material_exame": "Material_Exame", "resultado": "Resultado", "bacteria": "Bactéria",
                "indicados_s": "Indicados (S)", "resistentes_r": "Resistentes (R)", "unidade": "Unidade", "periodo_arquivo": "Período_Arquivo"
            })
            df_todos_dados['Data_Obj'] = pd.to_datetime(df_todos_dados['Data'], format="%d/%m/%Y", errors='coerce')
            df_todos_dados['Mês/Ano'] = df_todos_dados['Data_Obj'].dt.strftime('%m/%Y').fillna('Desconhecido')
            
            unid_perm = st.session_state.get('unidades_permitidas', 'Todas')
            if unid_perm != "Todas" and st.session_state['usuario'] != "admin":
                df_todos_dados = df_todos_dados[df_todos_dados['Unidade'].isin([u.strip() for u in unid_perm.split(",")])]
            
            df_reais = df_todos_dados[df_todos_dados['Período_Arquivo'] != 'Gerado Demo']
    except Exception as e:
        st.warning("Aviso: Nenhuma tabela de laudos conectada ou banco vazio.")

    # ==========================================
    # MENU LATERAL
    # ==========================================
    logo_menu_b64 = get_base64_file(ARQUIVO_LOGO_MENU)
    if logo_menu_b64:
        st.sidebar.markdown(f'<div style="text-align: center; margin-bottom: 20px;"><img src="data:image/png;base64,{logo_menu_b64}" style="width: 130px;"></div>', unsafe_allow_html=True)
    
    st.sidebar.markdown(f"👤 Usuário: **{st.session_state['usuario'].upper()}**")
    st.sidebar.markdown(f"🛡️ Nível: **{st.session_state.get('nivel_acesso', '')}**")
    st.sidebar.markdown("---")

    opcoes_menu = ["📊 Painel Principal", "📈 Análise e Tendências"]
    if st.session_state.get('nivel_acesso') in ["Operador", "Administrador"]: opcoes_menu.append("📂 Ingestão de Dados")
    if st.session_state.get('nivel_acesso') == "Administrador": opcoes_menu.append("⚙️ Painel de Controle (Admin)")

    menu = st.sidebar.radio("Navegação", opcoes_menu)
    
    df_f = pd.DataFrame()
    if menu in ["📊 Painel Principal", "📈 Análise e Tendências"] and not df_reais.empty:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Filtros Globais")
        with st.sidebar.form("form_filtros"):
            meses_sel = st.multiselect("Período (Mês/Ano)", sorted(list(df_reais['Mês/Ano'].unique())), default=sorted(list(df_reais['Mês/Ano'].unique())))
            unid_sel = st.multiselect("Unidades", sorted(list(df_reais['Unidade'].unique())), default=sorted(list(df_reais['Unidade'].unique())))
            exame_sel = st.multiselect("Materiais", sorted(list(df_reais['Material_Exame'].unique())), default=sorted(list(df_reais['Material_Exame'].unique())))
            st.form_submit_button("Aplicar Filtros")
        
        df_f = df_reais[df_reais['Mês/Ano'].isin(meses_sel) & df_reais['Unidade'].isin(unid_sel) & df_reais['Material_Exame'].isin(exame_sel)]

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Encerrar Sessão", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    # ========================================================
    # TELA 1: PAINEL PRINCIPAL
    # ========================================================
    if menu == "📊 Painel Principal":
        st.title("Monitoramento Clínico Operacional")
        
        if df_reais.empty: st.info("Banco de dados central vazio. Vá para Ingestão de Dados.")
        elif df_f.empty: st.warning("Nenhum laudo corresponde aos filtros atuais.")
        else:
            t_total = len(df_f)
            t_pos = len(df_f[df_f['Resultado'] == 'Positivo'])
            pct_pos = (t_pos / t_total * 100) if t_total > 0 else 0
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Volume Analisado", t_total)
            m2.metric("Laudos Positivos", t_pos, f"{pct_pos:.1f}% de Positividade", delta_color="inverse")
            m3.metric("Laudos Negativos", len(df_f[df_f['Resultado'] == 'Negativo']))
            m4.metric("Unidades Ativas", len(df_f['Unidade'].unique()))
            
            df_pos = df_f[df_f['Resultado'] == 'Positivo']
            if not df_pos.empty:
                st.markdown("---")
                g1, g2 = st.columns(2)
                with g1:
                    st.markdown("#### Proporção de Resultados")
                    fig1 = px.pie(df_f, names='Resultado', hole=0.5, color='Resultado', color_discrete_map={'Positivo': COR_POSITIVO, 'Negativo': COR_NEGATIVO}, template="plotly_dark")
                    fig1.update_traces(textposition='inside', textinfo='percent+label')
                    fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig1, use_container_width=True)
                with g2:
                    st.markdown("#### Ranking de Patógenos")
                    df_bact = df_pos['Bactéria'].value_counts().reset_index()
                    fig2 = px.bar(df_bact, y='Bactéria', x='count', text='count', orientation='h', template="plotly_dark", color='count', color_continuous_scale="Blues")
                    fig2.update_layout(yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=0, b=0, l=0, r=0), xaxis_title="")
                    st.plotly_chart(fig2, use_container_width=True)

                st.markdown("#### Base de Casos Críticos (Positivos)")
                st.dataframe(df_pos[['Data', 'Código_Paciente', 'Unidade', 'Material_Exame', 'Bactéria', 'Indicados (S)', 'Resistentes (R)']], use_container_width=True, hide_index=True)

    # ========================================================
    # TELA 2: ANÁLISE E TENDÊNCIAS
    # ========================================================
    elif menu == "📈 Análise e Tendências":
        st.title("Análise Estratégica e Epidemiológica")
        
        if not df_f.empty:
            df_pos_comp = df_f[df_f['Resultado'] == 'Positivo'].copy()
            if not df_pos_comp.empty:
                c1, c2, c3 = st.columns(3)
                c1.metric("Patógeno Dominante", df_pos_comp['Bactéria'].value_counts().idxmax())
                c2.metric("Material mais Afetado", df_pos_comp['Material_Exame'].value_counts().idxmax())
                c3.metric("Focos de Infecção", f"{len(df_pos_comp)} Casos")
                
                st.markdown("---")
                col_g1, col_g2 = st.columns([1.5, 1])
                with col_g1:
                    st.markdown("#### Curva de Casos Positivos")
                    df_pos_comp['Data_Obj'] = pd.to_datetime(df_pos_comp['Data'], format="%d/%m/%Y", errors='coerce')
                    linha_tempo = df_pos_comp.dropna(subset=['Data_Obj']).groupby(df_pos_comp['Data_Obj'].dt.to_period("W")).size().reset_index(name='Casos')
                    linha_tempo['Data_Obj'] = linha_tempo['Data_Obj'].dt.to_timestamp()
                    fig_linha = px.line(linha_tempo, x='Data_Obj', y='Casos', markers=True, template="plotly_dark")
                    fig_linha.update_traces(line=dict(color='#0284c7', width=3), marker=dict(size=8, color='#0284c7'))
                    fig_linha.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis_title="", yaxis_title="")
                    st.plotly_chart(fig_linha, use_container_width=True)
                        
                with col_g2:
                    st.markdown("#### Distribuição por Unidade")
                    top_unid = df_pos_comp['Unidade'].value_counts().reset_index()
                    fig_unid = px.bar(top_unid, x='count', y='Unidade', orientation='h', text='count', template="plotly_dark", color='count', color_continuous_scale="Reds")
                    fig_unid.update_layout(yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis_title="")
                    st.plotly_chart(fig_unid, use_container_width=True)

    # ========================================================
    # TELA 3: INGESTÃO DE DADOS (PDF/TXT/EXCEL -> SUPABASE)
    # ========================================================
    elif menu == "📂 Ingestão de Dados":
        st.title("Processamento de Laudos em Lote")
        
        if 'texto_bruto_debug' not in st.session_state: st.session_state['texto_bruto_debug'] = ""

        arq = st.file_uploader("Arraste os documentos (PDF/TXT/XLSX/CSV)", type=['pdf', 'txt', 'csv', 'xlsx', 'xls', 'xlsb', 'xlsm', 'ods'])
        
        if arq and st.button("Sincronizar com Servidor", use_container_width=True):
            df_novo = pd.DataFrame()
            
            with st.spinner("Processando Inteligência de Dados..."):
                # Rota 1: Planilhas (Estruturado)
                if arq.name.endswith(('.csv', '.xlsx', '.xls', '.xlsb', '.xlsm', '.ods')):
                    df_novo = processar_planilha(arq)
                
                # Rota 2: PDF ou TXT (Desestruturado)
                else:
                    texto_bruto = ""
                    if arq.name.endswith('.pdf'):
                        try:
                            leitor = PyPDF2.PdfReader(arq)
                            for p in leitor.pages: texto_bruto += p.extract_text() + "\n"
                        except Exception as e: st.error(f"Erro na leitura do PDF: {e}")
                    else: 
                        texto_bruto = arq.read().decode("utf-8")
                    
                    st.session_state['texto_bruto_debug'] = texto_bruto 
                    df_novo = extrair_dados_pdf(texto_bruto)
                
                # Envio para o Banco de Dados Central
                if not df_novo.empty:
                    records = df_novo.to_dict(orient="records")
                    try:
                        # O Upsert envia os blocos de dados. O Supabase converte automaticamente NaN para NULL.
                        supabase.table("laudos").upsert(records).execute()
                        st.success(f"✅ {len(df_novo)} registros processados e enviados para o banco de dados central com sucesso!")
                        st.dataframe(df_novo, use_container_width=True)
                    except Exception as e:
                        st.error(f"Erro ao inserir no Supabase: {e}")
                else: 
                    st.error("Nenhum dado compatível identificado neste documento/planilha.")

        if st.session_state['texto_bruto_debug']: 
            st.markdown("---")
            st.warning("⚠️ MODO DIAGNÓSTICO PARA PDF/TXT: Se faltar informação na tabela acima, copie um pedaço do texto abaixo referente a 1 paciente e mande para o desenvolvedor.")
            st.text_area("VISUALIZADOR DE DADOS BRUTOS (Matriz):", st.session_state['texto_bruto_debug'][:3000], height=300)

    # ========================================================
    # TELA 4: ADMINISTRAÇÃO SUPABASE
    # ========================================================
    elif menu == "⚙️ Painel de Controle (Admin)":
        st.title("Administração do Sistema")
        tab1, tab2 = st.tabs(["Gerenciamento de Acessos", "Auditoria de Dados"])
        
        try:
            res_users = supabase.table("usuarios").select("*").execute()
            df_users_adm = pd.DataFrame(res_users.data)
            lista_usuarios = df_users_adm['usuario'].tolist() if not df_users_adm.empty else []
        except:
            df_users_adm = pd.DataFrame()
            lista_usuarios = []

        with tab1:
            with st.form("form_cadastro"):
                st.markdown("#### Criar Credencial")
                c1, c2 = st.columns(2)
                n_user = c1.text_input("Usuário:")
                n_senha = c2.text_input("Senha:", type="password")
                c3, c4 = st.columns(2)
                n_nivel = c3.selectbox("Permissão:", ["Visualizador", "Operador", "Administrador"])
                n_unid = c4.multiselect("Restringir Unidades:", UNIDADES_OFICIAIS)
                
                if st.form_submit_button("Provisionar Acesso"):
                    if n_user and n_senha:
                        if n_user not in lista_usuarios:
                            str_unid = ", ".join(n_unid) if n_unid else "Todas"
                            supabase.table("usuarios").insert({"usuario": n_user, "senha": n_senha, "nivel_acesso": n_nivel, "unidades_permitidas": str_unid}).execute()
                            st.success("Credencial criada!"); time.sleep(1); st.rerun()
                        else: st.error("Usuário já existe.")

            st.markdown("---")
            usr_editar = st.selectbox("Revogar Acesso:", [""] + lista_usuarios)
            if usr_editar and st.button("🗑️ Revogar Credencial"):
                supabase.table("usuarios").delete().eq("usuario", usr_editar).execute()
                st.success("Acesso revogado!"); time.sleep(1); st.rerun()

        with tab2:
            st.markdown("Tabela Bruta: *usuarios*")
            st.dataframe(df_users_adm, use_container_width=True)
            st.markdown("Tabela Bruta: *laudos*")
            if not df_reais.empty: st.dataframe(df_reais, use_container_width=True)
