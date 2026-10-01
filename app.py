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
    page_title="Bambu Filament Studio Web",
    page_icon="🖨️",
    layout="wide",
)

# --- FUNÇÕES DE PERSISTÊNCIA DE DADOS ---
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


# Inicializa o estado da sessão
if "data" not in st.session_state:
    st.session_state["data"] = load_data()
if "recent_tasks" not in st.session_state:
    st.session_state["recent_tasks"] = []

data = st.session_state["data"]

# --- TITULO E BARRA SUPERIOR ---
st.title("🖨️ Bambu Filament Studio Web")
st.caption("Gerenciador de Estoque de Filamentos & Sincronização Bambu Cloud")

# --- CARDS DE MÉTRICAS NO TOPO ---
inventory = data.get("inventory", [])
total_spools = len(inventory)
total_weight_kg = sum(item["current_g"] for item in inventory) / 1000.0
total_value_brl = sum(
    item["current_g"] * item["cost_per_g"] for item in inventory
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Carretéis no Estoque", f"{total_spools}")
m2.metric("Peso Total", f"{total_weight_kg:.2f} kg")
m3.metric("Valor Estimado", f"R$ {total_value_brl:.2f}")

status_conn = (
    f"🟢 Conectado ({data.get('saved_email', 'Token Salvo')})"
    if data.get("bambu_token")
    else "🔴 Desconectado"
)
m4.metric("Status Bambu Cloud", status_conn)

st.divider()

# --- ABAS NAVEGÁVEIS ---
tab_stock, tab_cloud = st.tabs(
    ["📦 Gerenciador de Estoque", "☁️ Conexão Bambu Cloud"]
)

# ==========================================
# ABA 1: ESTOQUE E IMPRESSÕES
# ==========================================
with tab_stock:
    col_left, col_right = st.columns([1.2, 1])

    # COLUNA ESQUERDA: CADASTRO E TABELA
    with col_left:
        st.subheader("➕ Cadastrar Novo Carretel")
        with st.form("form_add_spool"):
            f_col1, f_col2 = st.columns(2)
            mat_name = f_col1.text_input("Material / Marca", "PLA Basic")
            color_name = f_col2.selectbox(
                "Cor", list(PRESET_COLORS.keys()), index=0
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
                    st.success(f"Carretel '{mat_name} ({color_name})' adicionado!")
                    st.rerun()

        st.subheader("📦 Estoque Atual")

        if inventory:
            # Opções para filtrar a tabela por cor
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
                st.info("Nenhum filamento encontrado com essa cor.")

            # Seleção para Excluir / Editar
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

            col_btn1, col_btn2 = st.columns(2)
            if col_btn1.button("🗑️ Excluir Carretel Selecionado"):
                s_id = spool_options[selected_spool_label]
                data["inventory"] = [
                    s for s in data["inventory"] if s["id"] != s_id
                ]
                save_data(data)
                st.success("Carretel removido!")
                st.rerun()
        else:
            st.info("Nenhum carretel cadastrado no estoque.")

    # COLUNA DIREITA: IMPRESSÕES E BAIXA
    with col_right:
        st.subheader("🖼️ Sincronização Bambu Cloud")

        b_token = data.get("bambu_token")

        if st.button("🔄 Buscar Últimas Impressões"):
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
                        st.success("Histórico atualizado com sucesso!")
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
                "Escolha a Impressão:",
                range(len(task_options)),
                format_func=lambda x: task_options[x],
            )

            chosen_task = tasks[selected_task_idx]
            job_weight = float(chosen_task.get("weight", 0))
            job_time = chosen_task.get("costTime", 0) // 60
            cover_url = chosen_task.get("cover") or chosen_task.get("imageUrl")

            # Foto 3D da Peça
            if cover_url:
                try:
                    img_resp = requests.get(cover_url, timeout=5)
                    if img_resp.status_code == 200:
                        st.image(
                            Image.open(io.BytesIO(img_resp.content)),
                            width=240,
                        )
                except Exception:
                    pass

            st.write(
                f"**Consumo registrado:** {job_weight}g | **Duração:** {job_time} min"
            )

            if inventory:
                target_spool_label = st.selectbox(
                    "Descontar do Carretel:",
                    list(spool_options.keys()),
                    key="target_spool",
                )

                if st.button("⚡ Dar Baixa no Estoque", type="primary"):
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
                    st.success(
                        f"Baixa efetuada! Custo do plástico: R$ {cost:.2f}"
                    )
                    st.rerun()

# ==========================================
# ABA 2: CONEXÃO COM A BAMBU CLOUD
# ==========================================
with tab_cloud:
    st.subheader("🔑 Autenticação na Bambu Cloud")

    st.markdown("### Opção A: Login Direto com Token JWT")
    st.caption("O jeito mais simples: pegue seu Token no navegador e cole aqui.")

    manual_token = st.text_input("Cole seu Token JWT aqui:")
    if st.button("Salvar Token Manual"):
        if manual_token.strip():
            data["bambu_token"] = manual_token.strip()
            data["saved_email"] = "Token Manual"
            save_data(data)
            st.success("Token salvo com sucesso!")
            st.rerun()

    st.divider()

    st.markdown("### Opção B: Login por E-mail e Senha")
    email_in = st.text_input("E-mail Bambu:", value=data.get("saved_email", ""))
    pass_in = st.text_input("Senha:", type="password")
    code_in = st.text_input("Código 2FA (se recebido no e-mail):")

    if st.button("Conectar por E-mail/Senha"):
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
                        st.success("Conectado à Bambu Cloud com sucesso!")
                        st.rerun()
                else:
                    st.error(f"Erro ({resp.status_code}): {resp.text}")
            except Exception as e:
                st.error(f"Erro de conexão: {e}")

    if data.get("bambu_token"):
        st.divider()
        if st.button("🚪 Desconectar / Encerrar Sessão"):
            data["bambu_token"] = None
            data["saved_email"] = ""
            save_data(data)
            st.success("Sessão encerrada.")
            st.rerun()
