import io
import json
import os
import uuid
from PIL import Image
import requests
import streamlit as st

DATA_FILE = "estoque_filamentos.json"
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
    page_title="Bambu Filament Studio Pro",
    page_icon="🖨️",
    layout="wide",
)

# --- ESTILIZAÇÃO CSS CUSTOMIZADA ---
st.markdown(
    """
    <style>
    /* Estilo do Fundo e Fontes */
    .stApp {
        background-color: #0B0E14;
        color: #E2E8F0;
        font-family: 'Segoe UI', -apple-system, sans-serif;
    }
    
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    [data-testid="stMetric"] {
        background: #151922;
        border: 1px solid #232D3F;
        border-radius: 12px;
        padding: 15px 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    
    [data-testid="stMetricLabel"] {
        color: #A0AEC0 !important;
        font-size: 0.85rem !important;
        font-weight: 700 !important;
        text-transform: uppercase;
    }
    
    [data-testid="stMetricValue"] {
        color: #00E676 !important;
        font-size: 1.8rem !important;
        font-weight: 800 !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: #0B0E14;
    }

    .stTabs [data-baseweb="tab"] {
        height: 48px;
        background-color: #151922;
        border-radius: 8px;
        color: #A0AEC0;
        font-weight: 600;
        border: 1px solid #232D3F;
        padding: 0px 24px;
    }

    .stTabs [aria-selected="true"] {
        background-color: #7C4DFF !important;
        color: #FFFFFF !important;
        border: 1px solid #7C4DFF !important;
    }

    .stButton > button {
        border-radius: 8px;
        font-weight: 700;
        border: none;
        transition: all 0.2s ease-in-out;
    }

    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
        background-color: #151922 !important;
        border: 1px solid #232D3F !important;
        border-radius: 8px !important;
        color: #FFFFFF !important;
    }
    </style>
    """,
    unsafe_allow_html=True,  # <--- ALTERADO AQUI
)


# --- PERSISTÊNCIA DE DADOS ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "inventory": [],
        "id_counter": 1,
        "bambu_token": None,
        "saved_email": "",
    }


def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        st.error(f"Erro ao salvar dados: {e}")


if "data" not in st.session_state:
    st.session_state["data"] = load_data()
if "recent_tasks" not in st.session_state:
    st.session_state["recent_tasks"] = []

data = st.session_state["data"]

# --- BANNER SUPERIOR ---
st.markdown(
    """
    <div style='background: linear-gradient(90deg, #151922 0%, #0B0E14 100%); padding: 20px; border-radius: 12px; border: 1px solid #232D3F; margin-bottom: 20px;'>
        <h2 style='margin: 0; color: #00E676;'>⚡ BAMBU FILAMENT STUDIO PRO</h2>
        <p style='margin: 5px 0 0 0; color: #A0AEC0; font-size: 0.9rem;'>Gestão Inteligente de Estoque 3D & Sincronização Cloud</p>
    </div>
    """,
    unsafe_allow_html=True,  # <--- ALTERADO AQUI
)

# --- DASHBOARD DE MÉTRICAS ---
inventory = data.get("inventory", [])
total_spools = len(inventory)
total_weight_kg = sum(item["current_g"] for item in inventory) / 1000.0
total_value_brl = sum(
    item["current_g"] * item["cost_per_g"] for item in inventory
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Carretéis no Estoque", f"{total_spools}")
m2.metric("Peso Total", f"{total_weight_kg:.2f} kg")
m3.metric("Valor em Plástico", f"R$ {total_value_brl:.2f}")

status_conn = (
    f"🟢 Conectado" if data.get("bambu_token") else "🔴 Desconectado"
)
m4.metric("Status Bambu Cloud", status_conn)

st.write("")

# --- ABAS DE NAVEGAÇÃO ---
tab_stock, tab_cloud = st.tabs(
    ["📦 Gerenciador de Estoque", "☁️ Conexão Bambu Cloud"]
)

# ==========================================
# ABA 1: GERENCIADOR DE ESTOQUE
# ==========================================
with tab_stock:
    col_left, col_right = st.columns([1.3, 1])

    with col_left:
        st.markdown("### ➕ Cadastrar Novo Filamento")
        with st.form("form_add_spool"):
            f_col1, f_col2 = st.columns(2)
            mat_name = f_col1.text_input("Material / Marca", "PLA Basic")
            color_name = f_col2.selectbox(
                "Cor do Carretel", list(PRESET_COLORS.keys()), index=0
            )

            f_col3, f_col4 = st.columns(2)
            price = f_col3.number_input(
                "Preço Pago (R$)", value=120.0, step=5.0
            )
            curr_w = f_col4.number_input(
                "Sobra Atual (g)", value=1000.0, step=50.0
            )

            btn_save = st.form_submit_button("➕ Salvar no Estoque")

            if btn_save:
                if mat_name and price > 0 and curr_w >= 0:
                    new_spool = {
                        "id": data.get("id_counter", 1),
                        "name": mat_name,
                        "color_name": color_name,
                        "color_hex": PRESET_COLORS.get(color_name, "#111111"),
                        "price": price,
                        "initial_g": 1000.0,
                        "current_g": curr_w,
                        "cost_per_g": price / 1000.0,
                    }
                    data["inventory"].append(new_spool)
                    data["id_counter"] += 1
                    save_data(data)
                    st.success(f"Carretel '{mat_name} ({color_name})' salvo!")
                    st.rerun()

        st.markdown("### 📦 Tabela de Estoque")

        if inventory:
            filter_color = st.selectbox(
                "🎨 Filtrar por Cor:",
                ["Todas as Cores"] + list(PRESET_COLORS.keys()),
            )

            display_list = []
            for item in inventory:
                if (
                    filter_color != "Todas as Cores"
                    and item.get("color_name") != filter_color
                ):
                    continue

                curr = item["current_g"]
                status = (
                    "🔴 Esgotado"
                    if curr <= 0
                    else (
                        "⚠ Crítico"
                        if curr < 150
                        else ("🟡 Médio" if curr < 500 else "🟢 Cheio")
                    )
                )

                display_list.append(
                    {
                        "ID": item["id"],
                        "Material": item["name"],
                        "Cor": item.get("color_name", "N/A"),
                        "Sobra (g)": f"{curr:.1f}g",
                        "Custo/g": f"R$ {item['cost_per_g']:.3f}",
                        "Nível": status,
                    }
                )

            if display_list:
                st.dataframe(display_list, use_container_width=True)
            else:
                st.info("Nenhum filamento encontrado para o filtro selecionado.")

            st.caption("Ações de Gerenciamento:")
            spool_options = {
                f"#{s['id']} - {s['name']} ({s.get('color_name', '')}) - {s['current_g']}g": s[
                    "id"
                ]
                for s in inventory
            }
            selected_spool_label = st.selectbox(
                "Selecione um carretel:", list(spool_options.keys())
            )

            if st.button("🗑️ Excluir Carretel Selecionado"):
                s_id = spool_options[selected_spool_label]
                data["inventory"] = [
                    s for s in data["inventory"] if s["id"] != s_id
                ]
                save_data(data)
                st.success("Carretel removido!")
                st.rerun()
        else:
            st.info("Seu estoque está vazio. Cadastre um carretel acima.")

    with col_right:
        st.markdown("### 🖼️ Sincronização Bambu Cloud")

        b_token = data.get("bambu_token")

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
                    resp = requests.get(
                        history_url, headers=headers, params=params, timeout=12
                    )

                    if resp.status_code == 200:
                        res_json = resp.json()
                        st.session_state["recent_tasks"] = res_json.get(
                            "hits", []
                        ) or res_json.get("tasks", [])
                        st.success("Histórico carregado!")
                    else:
                        st.error("Token expirado ou inválido.")
                except Exception as e:
                    st.error(f"Erro de conexão: {e}")

        tasks = st.session_state.get("recent_tasks", [])

        if tasks:
            task_options = [
                f"{t.get('title', 'Sem Nome')} ({t.get('weight', 0)}g)"
                for t in tasks
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
                        st.image(
                            Image.open(io.BytesIO(img_resp.content)),
                            width=260,
                        )
                except Exception:
                    pass

            st.markdown(
                f"**📦 Consumo:** `{job_weight}g` &nbsp;&nbsp;|&nbsp;&nbsp; **⏱️ Duração:** `{job_time} min`"
            )

            if inventory:
                target_spool_label = st.selectbox(
                    "Descontar do Carretel:",
                    list(spool_options.keys()),
                    key="target_spool",
                )

                if st.button("⚡ Dar Baixa no Estoque", type="primary", use_container_width=True):
                    target_id = spool_options[target_spool_label]
                    spool = next(
                        s for s in data["inventory"] if s["id"] == target_id
                    )

                    if spool["current_g"] < job_weight:
                        spool["current_g"] = 0
                    else:
                        spool["current_g"] -= job_weight

                    cost = job_weight * spool["cost_per_g"]
                    save_data(data)
                    st.success(f"Baixa efetuada! Custo: R$ {cost:.2f}")
                    st.rerun()

# ==========================================
# ABA 2: CONEXÃO CLOUD
# ==========================================
with tab_cloud:
    st.markdown("### 🔑 Autenticação na Bambu Cloud")

    st.markdown("#### Opção A: Login com Token Manual (Recomendado)")
    manual_token = st.text_input("Cole o Token JWT do seu navegador:")
    if st.button("Entrar por Token"):
        if manual_token.strip():
            data["bambu_token"] = manual_token.strip()
            data["saved_email"] = "Token Manual"
            save_data(data)
            st.success("Token ativado com sucesso!")
            st.rerun()

    st.divider()

    st.markdown("#### Opção B: Login por E-mail e Senha")
    email_in = st.text_input("E-mail Bambu:", value=data.get("saved_email", ""))
    pass_in = st.text_input("Senha:", type="password")
    code_in = st.text_input("Código 2FA (se recebido no e-mail):")

    if st.button("Conectar por E-mail"):
        if email_in and pass_in:
            dev_id = str(uuid.uuid4())
            login_url = f"{BAMBU_BASE_URL}/v1/user-service/user/login"
            payload = {
                "account": email_in,
                "password": pass_in,
                "device_id": dev_id,
            }
            if code_in.strip():
                payload["code"] = code_in.strip()
                payload["verify_code"] = code_in.strip()

            headers = {
                "Content-Type": "application/json",
                "User-Agent": "BambuStudio/01.09.00.00",
                "Accept": "application/json",
                "X-Bambu-Client-Type": "studio",
            }

            try:
                resp = requests.post(
                    login_url, json=payload, headers=headers, timeout=12
                )
                res_data = resp.json()

                if resp.status_code == 200:
                    token = res_data.get("token") or res_data.get("accessToken")
                    if token:
                        data["bambu_token"] = token
                        data["saved_email"] = email_in
                        save_data(data)
                        st.success("Conectado à Bambu Cloud!")
                        st.rerun()
                else:
                    st.error(f"Erro ({resp.status_code}): {resp.text}")
            except Exception as e:
                st.error(f"Erro de conexão: {e}")

    if data.get("bambu_token"):
        st.divider()
        if st.button("🚪 Encerrar Sessão"):
            data["bambu_token"] = None
            data["saved_email"] = ""
            save_data(data)
            st.success("Sessão encerrada.")
            st.rerun()
