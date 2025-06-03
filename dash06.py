import streamlit as st
import pandas as pd
import plotly.express as px
import locale

# ================= LOGIN =================
usuarios = {
    "Diego15": "Diego@dias15",
    "Admim": "123258"
}

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Login - Dashboard MRZ Group")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if usuario in usuarios and usuarios[usuario] == senha:
            st.session_state.logado = True
            st.session_state.usuario = usuario
            st.success("Login realizado com sucesso. Recarregando...")
            st.stop()  # Parar a execução aqui, recarregando com login ativo
        else:
            st.error("Usuário ou senha inválidos.")
    st.stop()
# =========================================

# 🌍 Configurações regionais
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        locale.setlocale(locale.LC_ALL, '')

# Layout
st.set_page_config(layout="wide")
st.title("📊 Dashboard Devoluções MRZ Group v1.0")

# Botão logout
if st.button("Sair"):
    st.session_state.logado = False
    st.experimental_rerun()

# 📁 Upload do Excel
uploaded_file = st.file_uploader("Selecione o arquivo Excel", type=["xlsx", "xls"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)

    # 🧹 Normalização
    df.columns = [col.strip().upper() for col in df.columns]
    df["FILIAL"] = df["FILIAL"].astype(str).str.strip().str.upper()
    df["MOTIVO"] = df["MOTIVO"].astype(str).str.strip()
    df["VENDEDOR"] = df["VENDEDOR"].astype(str).str.strip()
    df["CLIENTE"] = df["CLIENTE"].astype(str).str.strip()
    df["VALOR"] = pd.to_numeric(df["VALOR"], errors="coerce").fillna(0)

    df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")
    df = df.dropna(subset=["DATA"])
    df = df.sort_values("DATA")
    df["MES"] = df["DATA"].apply(lambda x: f"{x.month:02d} / {x.year}")
else:
    st.warning("Por favor, selecione um arquivo Excel para continuar.")
    st.stop()

# 📌 Filtros
meses_disponiveis = df["MES"].unique().tolist()
vendedores_opcoes = df["VENDEDOR"].dropna().unique().tolist()
meses_disponiveis.insert(0, "TODOS")
mes = st.sidebar.selectbox("SELECIONE O MÊS", meses_disponiveis)

motivos_opcoes = df["MOTIVO"].dropna().unique().tolist()
filiais_opcoes = df["FILIAL"].dropna().unique().tolist()

motivo_selecionado = st.sidebar.multiselect("SELECIONE O MOTIVO", motivos_opcoes, default=motivos_opcoes)
filial_selecionada = st.sidebar.multiselect("SELECIONE A UNIDADE LOGÍSTICA", filiais_opcoes, default=filiais_opcoes)
vendedor_selecionado = st.sidebar.multiselect("SELECIONE O VENDEDOR", vendedores_opcoes, default=vendedores_opcoes)

# 🔍 Filtro dinâmico
df_filtrado = df[
    (df["MOTIVO"].isin(motivo_selecionado)) &
    (df["FILIAL"].isin(filial_selecionada)) &
    (df["VENDEDOR"].isin(vendedor_selecionado))
]
if mes != "TODOS":
    df_filtrado = df_filtrado[df_filtrado["MES"] == mes]

# 📌 Verificação se há dados
if df_filtrado.empty:
    st.warning("Nenhum dado encontrado com os filtros selecionados.")
    st.stop()

# Função para formatar moeda com fallback
def formatar_moeda(valor):
    try:
        return locale.currency(valor, grouping=True)
    except Exception:
        return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

# 🔢 Métrica total
total_valor = df_filtrado["VALOR"].sum()
valor_formatado = formatar_moeda(total_valor)

# 🎯 Top 5 ocorrências por percentual
motivos_df = (
    df_filtrado.groupby("MOTIVO")["VALOR"]
    .sum()
    .reset_index()
    .sort_values("VALOR", ascending=False)
)
total_motivos = motivos_df["VALOR"].sum()
motivos_df["PERCENTUAL"] = (motivos_df["VALOR"] / total_motivos) * 100
motivos_df["PERCENTUAL"] = motivos_df["PERCENTUAL"].map("{:.1f}%".format)

top_5_motivos = motivos_df.head(10)[["MOTIVO", "PERCENTUAL"]]
top_5_motivos.index = range(1, len(top_5_motivos) + 1)

# 📊 Gráfico de devoluções por FILIAL
df_mes = df.copy()
df_mes["MÊS"] = df_mes["DATA"].dt.strftime("%b/%Y")
grafico_pizza = df_mes.groupby("FILIAL")["VALOR"].sum().reset_index()

st.subheader("📊 ANÁLISE POR UNIDADE LOGÍSTICA")
fig_pizza = px.pie(
    grafico_pizza,
    names="FILIAL",
    values="VALOR",
    title="",
    color_discrete_sequence=px.colors.qualitative.Set3
)
fig_pizza.update_traces(
    textinfo='percent+label',
    textfont=dict(family="Arial black", size=10, color="black")
)

col1, col2 = st.columns([2, 1])
with col1:
    st.plotly_chart(fig_pizza, use_container_width=True)

with col2:
    st.metric("VALOR TOTAL", f"{valor_formatado}")
    st.subheader("📋 PERCENTUAL P/ OCORRÊNCIAS")
    st.dataframe(top_5_motivos, use_container_width=True)

# 🔁 Função para gerar rankings
def gerar_ranking_df(df, coluna, titulo):
    if coluna in df.columns:
        rnk = (
            df.groupby(coluna)["VALOR"]
            .sum()
            .reset_index()
            .sort_values("VALOR", ascending=False)
            .head(10)
        )
        rnk.index = range(1, len(rnk) + 1)
        rnk["VALOR"] = rnk["VALOR"].apply(formatar_moeda)
        return titulo, rnk
    return None, None

# 📋 Rankings adicionais
rankings = []
top_10_motivos_valor = motivos_df.copy().head(10)[["MOTIVO", "VALOR"]]
top_10_motivos_valor["VALOR"] = top_10_motivos_valor["VALOR"].apply(formatar_moeda)
top_10_motivos_valor.index = range(1, len(top_10_motivos_valor) + 1)
rankings.append(("📊 VALORES P/ TIPO DE OCORRÊNCIA", top_10_motivos_valor))

for coluna, titulo in [
    ("VENDEDOR", "👔 OCORRÊNCIAS P/ VENDEDORES"),
    ("CLIENTE", "🧾 OCORRÊNCIAS P/ CLIENTES"),
    ("MOTORISTA", "🚚 OCORRÊNCIAS P/ MOTORISTAS"),
    ("ROTA", "🏙️ OCORRÊNCIAS P/ ROTAS"),
]:
    titulo, df_rnk = gerar_ranking_df(df_filtrado, coluna, titulo)
    if df_rnk is not None:
        rankings.append((titulo, df_rnk))

for i in range(0, len(rankings), 2):
    cols = st.columns(2)
    for col, (titulo, df_rnk) in zip(cols, rankings[i:i+2]):
        col.subheader(titulo)
        col.dataframe(df_rnk, use_container_width=True)

st.markdown("Auditoria de Logística Nacional - @Diego Dias.")
