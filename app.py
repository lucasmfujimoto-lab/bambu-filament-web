import io
import json
import uuid
from PIL import Image
import requests
import streamlit as st
from supabase import create_client, Client

# --- CONFIGURAÇÃO DO SUPABASE ---
SUPABASE_URL = "https://aaxicngdahpbunwlgjsj.supabase.co"
SUPABASE_KEY = "SUA_CHAVE_ANON_AQUI"  # Cole aqui a sua chave anon / public

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

BAMBU_BASE_URL = "https://api.bambulab.com"

PRESET_COLORS = {
    "Preto": "#111111",
    "Branco": "#FFFFFF",
    "Cinza": "#808080",
    "Vermelho": "#FF2A2A",
    "Azul": "#2A75FF",
    "Verde Menta": "#00E676",
    "Amarelo": "#FFD600",
    "Laranja": "#FF6D00",
    "Roxo": "#9C27B0",
    "Dourado": "#FFD700",
    "Prata": "#C0C0C0",
    "Transparente": "#E0E0E0",
}

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Bambu Filament Studio",
    page_icon="🖨️",
    layout="wide",
)

# --- ESTILIZAÇÃO CSS (LARANJA SUAVE) ---
st.markdown(
    """
    <style>
    .stApp {
        background-color: #FFF3E0;
        color: #2E1C0C;
        font-family: 'Segoe UI', -apple-system, sans-serif;
    }
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    h1, h2, h3, h4, h5, h6, label, p, span {
        color: #2E1C0C !important;
    }

    [data-testid="stMetric"] {
        background: #FFFFFF;
        border: 2px solid #FFE0B2;
        border-radius: 12px;
        padding: 15px 20px;
    }
    [data-testid="stMetricLabel"] {
        color: #795548 !important;
        font-size: 0.85rem !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricValue"] {
        color: #E65100 !important;
        font-size: 1.8rem !important;
        font-weight: 800 !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: #FFF3E0;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        background-color: #FFE0B2;
        border-radius: 8px;
        color: #4E342E;
        font-weight: 700;
        border: 1px solid #FFCC80;
        padding: 0px 24px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #EF6C00 !important;
        color: #FFFFFF !important;
        border: 1px solid #E65100 !important;
    }

    .stButton > button {
        border-radius: 8px;
        font-weight: 700;
        background-color: #EF6C00;
        color: #FFFFFF !important;
        border: none;
    }
    
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        border: 1px solid #FFCC80 !important;
        border-radius: 8px !important;
        color: #2E1C0C !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Inicialização da Sessão de Utilizador
if "user" not in st.session_state:
    st.session_state["user"] = None
if "recent_tasks" not in st.session_state:
    st.session_state["recent_tasks"] = []
if "bambu_token" not in st.session_state:
    st.session_state["bambu_token"] = None

# ==========================================
# TELA DE LOGIN E CADASTRO (BLOQUEIO)
# ==========================================
if st.session_state["user"] is None:
    st.markdown(
        """
        <div style='text-align: center; padding: 30px 0 10px 0;'>
            <h1 style='color: #E65100;'>🖨️ Bambu Filament Studio</h1>
            <p style='color: #5D4037; font-size: 1.1rem;'>Aceda à sua conta para gerir o seu estoque de filamentos 3D</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, col_center, _ = st.columns([1, 1.2, 1])

    with col_center:
        # BOTÃO DE LOGIN COM O GOOGLE
        if st.button("🌐 Entrar com a Conta Google", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_oauth({
                    "provider": "google",
                    "options": {
                        "redirect_to": "https://lucasmfujimoto-lab-bambu-filament-web.streamlit.app"
                    }
                })
                if res.url:
                    st.markdown(f'<meta http-equiv="refresh" content="0;url={res.url}">', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Erro ao iniciar login com Google: {e}")

        st.markdown("<p style='text-align: center; margin: 15px 0;'><b>OU</b></p>", unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs(["🔑 Entrar com E-mail", "📝 Criar Conta"])

        with tab_login:
            email_login = st.text_input("E-mail:", key="login_email")
            pass_login = st.text_input("Palavra-passe:", type="password", key="login_pass")
            if st.button("Entrar no App", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password(
                        {"email": email_login, "password": pass_login}
                    )
                    st.session_state["user"] = res.user
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error("Erro no login. Verifique o seu e-mail e palavra-passe.")

        with tab_signup:
            email_signup = st.text_input("Novo E-mail:", key="signup_email")
            pass_signup = st.text_input("Nova Palavra-passe:", type="password", key="signup_pass")
            if st.button("Criar Minha Conta", use_container_width=True):
                try:
                    res = supabase.auth.sign_up(
                        {"email": email_signup, "password": pass_signup}
                    )
                    st.success("Conta criada! Pode agora fazer login.")
                except Exception as e:
                    st.error(f"Erro ao cadastrar: {e}")

    # Interrompe a execução do restante app se não estiver logado
    st.stop()

# ==========================================
# APLICAÇÃO PRINCIPAL (SÓ EXECUTA SE LOGADO)
# ==========================================
user_id = st.session_state["user"].id
user_email = getattr(st.session_state["user"], "email", "Utilizador Google")

def fetch_inventory():
    try:
        res = supabase.table("filamentos").select("*").eq("user_id", user_id).execute()
        return res.data or []
    except Exception:
        return []

inventory = fetch_inventory()

# BANNER SUPERIOR COM BOTÃO DE SAÍDA
header_c1, header_c2 = st.columns([3, 1])
with header_c1:
    st.markdown(
        f"""
        <div style='background: #FFE0B2; padding: 15px; border-radius: 12px; border: 2px solid #FFCC80;'>
            <h3 style='margin: 0; color: #E65100;'>⚡ BAMBU FILAMENT STUDIO PRO</h3>
            <p style='margin: 0; color: #5D4037;'>Sessão de: <b>{user_email}</b></p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with header_c2:
    if st.button("🚪 Sair da Conta", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state["user"] = None
        st.session_state["bambu_token"] = None
        st.rerun()

st.write("")

# MÉTRICAS
total_spools = len(inventory)
total_weight_kg = sum(float(item["current_g"]) for item in inventory) / 1000.0 if inventory else 0.0
total_value_brl = sum(float(item["current_g"]) * float(item["cost_per_g"]) for item in inventory) if inventory else 0.0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Meus Carretéis", f"{total_spools}")
m2.metric("Meu Peso Total", f"{total_weight_kg:.2f} kg")
m3.metric("Meu Valor em Plástico", f"R$ {total_value_brl:.2f}")
status_conn = "🟢 Conectado" if st.session_state.get("bambu_token") else "🔴 Desconectado"
m4.metric("Status Bambu Cloud", status_conn)

st.write("")

tab_stock, tab_cloud = st.tabs(["📦 Meu Estoque", "☁️ Bambu Cloud"])

# ABA 1: GERENCIADOR DE ESTOQUE
with tab_stock:
    col_left, col_right = st.columns([1.3, 1])

    with col_left:
        st.markdown("### ➕ Cadastrar Novo Filamento")
        with st.form("form_add_spool"):
            f_col1, f_col2 = st.columns(2)
            mat_name = f_col1.text_input("Material / Marca", "PLA Basic")
            color_name = f_col2.selectbox("Cor do Carretel", list(PRESET_COLORS.keys()), index=0)

            f_col3, f_col4 = st.columns(2)
            price = f_col3.number_input("Preço Pago (R$)", value=120.0, step=5.0)
            curr_w = f_col4.number_input("Sobra Atual (g)", value=1000.0, step=50.0)

            btn_save = st.form_submit_button("➕ Salvar no Meu Estoque")

            if btn_save:
                if mat_name and price > 0 and curr_w >= 0:
                    new_data = {
                        "user_id": user_id,
                        "name": mat_name,
                        "color_name": color_name,
                        "color_hex": PRESET_COLORS.get(color_name, "#111111"),
                        "price": price,
                        "current_g": curr_w,
                        "cost_per_g": price / 1000.0,
                    }
                    supabase.table("filamentos").insert(new_data).execute()
                    st.success("Carretel salvo com sucesso!")
                    st.rerun()

        st.markdown("### 📦 Tabela do Meu Estoque")

        if inventory:
            filter_color = st.selectbox(
                "🎨 Filtrar por Cor:",
                ["Todas as Cores"] + list(PRESET_COLORS.keys()),
            )

            display_list = []
            for item in inventory:
                if filter_color != "Todas as Cores" and item.get("color_name") != filter_color:
                    continue

                curr = float(item["current_g"])
                status = (
                    "🔴 Esgotado"
                    if curr <= 0
                    else ("⚠ Crítico" if curr < 150 else ("🟡 Médio" if curr < 500 else "🟢 Cheio"))
                )

                display_list.append(
                    {
                        "ID": item["id"],
                        "Material": item["name"],
                        "Cor": item.get("color_name", "N/A"),
                        "Sobra (g)": f"{curr:.1f}g",
                        "Custo/g": f"R$ {float(item['cost_per_g']):.3f}",
                        "Nível": status,
                    }
                )

            if display_list:
                st.dataframe(display_list, use_container_width=True)
            else:
                st.info("Nenhum filamento encontrado para esta cor.")

            spool_options = {
                f"#{s['id']} - {s['name']} ({s.get('color_name', '')}) - {s['current_g']}g": s["id"]
                for s in inventory
            }
            selected_spool_label = st.selectbox("Selecione um carretel:", list(spool_options.keys()))

            if st.button("🗑️ Excluir Carretel Selecionado"):
                s_id = spool_options[selected_spool_label]
                supabase.table("filamentos").delete().eq("id", s_id).execute()
                st.success("Carretel removido!")
                st.rerun()
        else:
            st.info("Ainda não cadastrou nenhum carretel.")

    with col_right:
        st.markdown("### 🖼️ Sincronização Bambu Cloud")

        b_token = st.session_state.get("bambu_token")

        if st.button("🔄 Carregar Impressões da Nuvem", use_container_width=True):
            if not b_token:
                st.warning("Conecte-se à Bambu Cloud na aba ao lado primeiro.")
            else:
                try:
                    history_url = f"{BAMBU_BASE_URL}/v1/user-service/my/tasks"
                    headers = {
                        "Authorization": f"Bearer {b_token}",
                        "User-Agent": "BambuStudio/01.09.00.00",
                    }
                    params = {"limit": 15, "offset": 0}
                    resp = requests.get(history_url, headers=headers, params=params, timeout=12)

                    if resp.status_code == 200:
                        res_json = resp.json()
                        st.session_state["recent_tasks"] = res_json.get("hits", []) or res_json.get("tasks", [])
                        st.success("Histórico carregado!")
                    else:
                        st.error("Token expirado ou inválido.")
                except Exception as e:
                    st.error(f"Erro de conexão: {e}")

        tasks = st.session_state.get("recent_tasks", [])

        if tasks:
            task_options = [
                f"{t.get('title', 'Sem Nome')} ({t.get('weight', 0)}g)" for t in tasks
            ]
            selected_task_idx = st.selectbox(
                "Selecione o Trabalho Realizado:",
                range(len(task_options)),
                format_func=lambda x: task_options[x],
            )

            chosen_task = tasks[selected_task_idx]
            job_weight = float(chosen_task.get("weight", 0))
            job_time = chosen_task.get("costTime", 0) // 60
            cover_url = chosen_task.get("cover") or chosen_task.get("imageUrl")

            if cover_url:
                try:
                    img_resp = requests.get(cover_url, timeout=5)
                    if img_resp.status_code == 200:
                        st.image(Image.open(io.BytesIO(img_resp.content)), width=260)
                except Exception:
                    pass

            st.markdown(f"**📦 Consumo:** `{job_weight}g` | **⏱️ Duração:** `{job_time} min`")

            if inventory:
                target_spool_label = st.selectbox(
                    "Descontar do Carretel:", list(spool_options.keys()), key="target_spool"
                )

                if st.button("⚡ Dar Baixa no Estoque", type="primary", use_container_width=True):
                    target_id = spool_options[target_spool_label]
                    spool = next(s for s in inventory if s["id"] == target_id)

                    new_weight = float(spool["current_g"]) - job_weight
                    if new_weight < 0:
                        new_weight = 0

                    supabase.table("filamentos").update({"current_g": new_weight}).eq("id", target_id).execute()
                    cost = job_weight * float(spool["cost_per_g"])
                    st.success(f"Baixa efetuada! Custo: R$ {cost:.2f}")
                    st.rerun()

# ABA 2: CONEXÃO CLOUD
with tab_cloud:
    st.markdown("### 🔑 Autenticação Bambu Cloud")

    st.markdown("#### Cole o Token JWT do seu aplicativo/navegador:")
    manual_token = st.text_input("Token JWT:")
    if st.button("Conectar Conta Bambu"):
        if manual_token.strip():
            st.session_state["bambu_token"] = manual_token.strip()
            st.success("Conectado com sucesso à conta Bambu Lab!")
            st.rerun()
