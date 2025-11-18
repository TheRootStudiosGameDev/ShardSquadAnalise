# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
import os


# Change the visibility of items in the toolbar, options menu,
# and settings dialog (top right of the app).
# Allowed values:
# * "auto"      : Show the developer options if the app is accessed through
#                 localhost or through Streamlit Community Cloud as a developer.
#                 Hide them otherwise.
# * "developer" : Show the developer options.
# * "viewer"    : Hide the developer options.
# * "minimal"   : Show only options set externally (e.g. through
#                 Streamlit Community Cloud) or through st.set_page_config.
#                 If there are no options left, hide the menu.
# Default: "auto

st.set_option("client.toolbarMode", "minimal")



st.set_page_config(page_title="ShardSquad Análise", layout="wide")

# ==========================
# LOGIN SIMPLES
# ==========================
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["login"]["password"]:
            st.session_state["authenticated"] = True
            del st.session_state["password"]  # não guardar a senha
        else:
            st.session_state["password_incorrect"] = True

    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.text_input(
            "Senha", type="password", on_change=password_entered, key="password"
        )
        if "password_incorrect" in st.session_state:
            st.error("Senha incorreta. Tente novamente.")
        return False
    return True


# Verifica login antes de mostrar qualquer coisa
if not check_password():
    st.stop()

# Sua connection string (do Supabase com Pooler)
DATABASE_URL = (
    "postgresql://postgres.rsxdlivgzvkohtzahnbs:TheRootData1475@"
    "aws-0-sa-east-1.pooler.supabase.com:6543/postgres"
    "?options=-c%20statement_timeout=120000"
)

# Cria engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_timeout=120)

# Dicionário de personagens: id -> nome
PERSONAGENS = {
    "0": "Sid",
    "1": "Braut",
    "2": "Deruto",
    "3": "Haus",
    "4": "Kiara",
    "5": "Nana",
    "6": "Slap",
    "7": "Zippy",
    "8": "Dex",
    "9": "Mossy",
    "10": "Kai",
    "11": "Juno",
    "12": "Snarky",
    "13": "Drip",
    "14": "Klaus",
    "15": "HopHop",
    "16": "Lilac",
    "17": "Edge",
    "18": "Blip",
    "19": "Dorian",
    "20": "Akari",
    "21": "Liu Kong",
}


@st.cache_data(ttl=300)
def load_data():
    query = """
    SELECT
        id,
        version,
        steam_name,
        steam_id,
        win,
        wave,
        stage,
        difficulty,
        total_seconds,
        coins,
        critical_hit_quantity,
        multiplayer,
        characters_damage_data,
        relics_id,
        selected_rewards,
        start_time
    FROM tb_partidas_tst2
    WHERE characters_damage_data IS NOT NULL
    ORDER BY id DESC
    LIMIT 1000
    """
    df = pd.read_sql(query, engine)

    df["characters_count"] = df["characters_damage_data"].apply(
        lambda x: len(x) if isinstance(x, list) else 0
    )
    df["total_damage"] = df["characters_damage_data"].apply(
        lambda x: sum(item.get("damage", 0) for item in x) if isinstance(x, list) else 0
    )
    df["relic_count"] = df["relics_id"].apply(
        lambda x: len(x) if isinstance(x, list) else 0
    )
    df["rewards_count"] = df["selected_rewards"].apply(
        lambda x: len(x) if isinstance(x, list) else 0
    )
    df["difficulty"] = df["difficulty"].astype(str)
    df["start_time_dt"] = pd.to_datetime(df["start_time"], errors="coerce")

    char_rows = []
    for _, row in df.iterrows():
        chars = row["characters_damage_data"]
        if isinstance(chars, list):
            for idx, char in enumerate(chars):
                char_rows.append(
                    {
                        "partida_id": row["id"],
                        "steam_name": row["steam_name"],
                        "steam_id": row["steam_id"],  # ⬅️ Adicionado
                        "version": row["version"],
                        "win": row["win"],
                        "wave": row["wave"],
                        "difficulty": str(row["difficulty"]),
                        "multiplayer": row["multiplayer"],
                        "character_id": char.get("character"),
                        "is_main": idx == 0,
                        "damage": char.get("damage", 0),
                        "damage_boss": char.get("damage_boss", 0),
                        "dps": char.get("dps", 0),
                        "upgrade_count": len(char.get("upgrade_indexes", [])),
                    }
                )
    df_chars = pd.DataFrame(char_rows)

    return df, df_chars


# ==========================
# INTERFACE
# ==========================


with st.spinner("Carregando dados do Supabase..."):
    df_partidas, df_personagens = load_data()

if df_partidas.empty:
    st.error("Nenhum dado encontrado.")
    st.stop()

# ==========================
# FILTROS com valores padrão e session_state
# ==========================
st.sidebar.header("🔍 Filtros")

# --- Versão: padrão = versão mais recente (ou "Todas" se preferir)
versions = ["Todas"] + sorted(df_partidas["version"].dropna().unique().tolist())
default_version = versions[-1] if len(versions) > 1 else "Todas"  # pega a mais recente

# --- Multijogador: padrão = "Todos"
mp_options = ["Todos", "Sim", "Não"]
default_mp = "Não"

# --- Dificuldade: padrão = "Todas"
diffs = ["Todas"] + sorted(df_partidas["difficulty"].dropna().unique().tolist())
default_diff = "1"

# Inicializa session_state se não existir
if "selected_version" not in st.session_state:
    st.session_state.selected_version = default_version
if "selected_mp" not in st.session_state:
    st.session_state.selected_mp = default_mp
if "selected_diff" not in st.session_state:
    st.session_state.selected_diff = default_diff


# Função para atualizar o session_state quando o usuário muda o seletor
def update_version():
    st.session_state.selected_version = st.session_state.version_key


def update_mp():
    st.session_state.selected_mp = st.session_state.mp_key


def update_diff():
    st.session_state.selected_diff = st.session_state.diff_key


# Criar os selectbox com key e on_change
selected_version = st.sidebar.selectbox(
    "Versão",
    versions,
    index=versions.index(st.session_state.selected_version),
    key="version_key",
    on_change=update_version,
)

selected_mp = st.sidebar.selectbox(
    "Multijogador",
    mp_options,
    index=mp_options.index(st.session_state.selected_mp),
    key="mp_key",
    on_change=update_mp,
)

selected_diff = st.sidebar.selectbox(
    "Dificuldade",
    diffs,
    index=diffs.index(st.session_state.selected_diff),
    key="diff_key",
    on_change=update_diff,
)

# Aplicar filtros
df_f = df_partidas.copy()
if selected_version != "Todas":
    df_f = df_f[df_f["version"] == selected_version]
if selected_mp == "Sim":
    df_f = df_f[df_f["multiplayer"] == True]
elif selected_mp == "Não":
    df_f = df_f[df_f["multiplayer"] == False]
if selected_diff != "Todas":
    df_f = df_f[df_f["difficulty"] == selected_diff]

df_chars_f = df_personagens[df_personagens["partida_id"].isin(df_f["id"])]


# ==========================
# KPIs ATUALIZADOS
# ==========================
st.title("📊 ShardSquad - Análise Direta do Supabase")

# 1. Total de partidas
total_partidas = len(df_f)

# 2. Wave com mais derrotas
derrotas = df_f[df_f["win"] == False]
wave_mais_derrotas = "–"
if not derrotas.empty:
    wave_counts = derrotas["wave"].value_counts()
    wave_mais_derrotas = wave_counts.idxmax()

# 3. Jogador com mais vitórias (usa steam_id para cálculo, mostra steam_name)
jogador_mais_vitorias = "–"
if not df_f[df_f["win"] == True].empty:
    vitorias_por_jogador = (
        df_f[df_f["win"] == True].groupby(["steam_id", "steam_name"]).size()
    )
    if not vitorias_por_jogador.empty:
        top_jogador = vitorias_por_jogador.idxmax()  # (steam_id, steam_name)
        jogador_mais_vitorias = top_jogador[1]  # steam_name

# 4. Taxa de vitórias (%)
taxa_vitorias = 0.0
if total_partidas > 0:
    vitorias_total = df_f["win"].sum()
    taxa_vitorias = (vitorias_total / total_partidas) * 100

# Exibir KPIs
col1, col2, col3, col4 = st.columns(4)
col1.metric("🎮 Partidas", f"{total_partidas:,}".replace(",", "."))
col2.metric("🌊 Wave com mais derrotas", wave_mais_derrotas)
col3.metric("🏆 Jogador com mais vitórias", jogador_mais_vitorias)
col4.metric("📊 Taxa de vitórias", f"{taxa_vitorias:.1f}%")

st.divider()

# ==========================
# ABAS
# ==========================
tab1, tab2, tab3, tab4 = st.tabs(
    ["📈 Visão Geral", "👥 Jogadores", "🎭 Personagens", "📄 Dados Brutos"]
)

with tab1:
    st.subheader("Wave com mais derrotas")
    derrotas = df_f[df_f["win"] == False]
    if not derrotas.empty:
        fig = px.bar(
            derrotas.groupby("wave").size().reset_index(name="count"),
            x="wave",
            y="count",
            text="count",
        )
        fig.update_layout(dragmode=False)
        st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
    else:
        st.info("Nenhuma derrota.")

with tab2:
    # Calcula estatísticas por jogador
    jogadores_stats = (
        df_f.groupby("steam_name")
        .agg(
            vitorias=("win", lambda x: x.sum()),
            derrotas=("win", lambda x: (~x).sum()),
        )
        .astype(int)
        .reset_index()
    )
    jogadores_stats["total"] = jogadores_stats["vitorias"] + jogadores_stats["derrotas"]
    jogadores_stats = jogadores_stats.nlargest(15, "total")  # top 15 por volume

    if jogadores_stats.empty:
        st.info("Nenhum dado de jogador.")
    else:
        # Preparar para gráfico empilhado
        fig = px.bar(
            jogadores_stats,
            y="steam_name",
            x=["vitorias", "derrotas"],
            orientation="h",
            labels={"value": "Partidas", "steam_name": "Jogador"},
            color_discrete_sequence=[
                "#2E568B",
                "#FF2323",
            ],  # verde escuro, vermelho claro
            barmode="stack",
        )
        fig.update_layout(
            dragmode=False,
            yaxis={"categoryorder": "total ascending"},
            legend_title_text="Resultado",
            xaxis_title="Partidas",
            yaxis_title="Jogador",
        )
        st.subheader("Desempenho por Jogador (Vitórias vs Derrotas)")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# --------------------------
# TAB 3: Personagens
# --------------------------
with tab3:
    if df_chars_f.empty:
        st.info("Nenhum dado de personagem nos filtros atuais.")
    else:
        # Separar apenas vitórias
        df_chars_wins = df_chars_f[df_chars_f["win"] == True]

        if df_chars_wins.empty:
            st.warning(
                "Nenhuma partida vencida com dados de personagens nos filtros atuais."
            )
        else:
            # Adicionar nome dos personagens
            df_chars_wins = df_chars_wins.copy()
            df_chars_wins["nome"] = (
                df_chars_wins["character_id"]
                .astype(str)
                .map(PERSONAGENS)
                .fillna(df_chars_wins["character_id"])
            )

            # --- Separar principais e secundários ---
            mains = df_chars_wins[df_chars_wins["is_main"] == True]
            secs = df_chars_wins[df_chars_wins["is_main"] == False]

            # --- Função para calcular KPIs ---
            def calcular_kpis(df, tipo):
                if df.empty:
                    return None, None, None, None

                stats = (
                    df.groupby(["character_id", "nome"])
                    .agg(
                        quantidade=("character_id", "size"),
                        dps_medio=("dps", "mean"),
                        dano_boss_medio=("damage_boss", "mean"),
                    )
                    .round(2)
                    .reset_index()
                )

                # 1. Mais popular
                mais_popular = stats.loc[stats["quantidade"].idxmax()]
                # 2. Melhor DPS
                melhor_dps = stats.loc[stats["dps_medio"].idxmax()]
                # 3. Maior dano contra chefes
                maior_dano_boss = stats.loc[stats["dano_boss_medio"].idxmax()]

                # 4. Mais equilibrado (desempenho combinado)
                # Normalizar DPS e Dano Boss para mesma escala
                stats["dps_norm"] = (stats["dps_medio"] - stats["dps_medio"].min()) / (
                    stats["dps_medio"].max() - stats["dps_medio"].min() + 1e-5
                )
                stats["dano_norm"] = (
                    stats["dano_boss_medio"] - stats["dano_boss_medio"].min()
                ) / (
                    stats["dano_boss_medio"].max()
                    - stats["dano_boss_medio"].min()
                    + 1e-5
                )
                stats["score_composto"] = stats["dps_norm"] + stats["dano_norm"]
                mais_equilibrado = stats.loc[stats["score_composto"].idxmax()]

                return mais_popular, melhor_dps, maior_dano_boss, mais_equilibrado

            kpis_mains = calcular_kpis(mains, "principal")
            kpis_secs = calcular_kpis(secs, "secundário")

            # --- Exibir KPIs ---
            st.subheader("🔍 Visão Rápida – Em Vitórias")

            if kpis_mains[0] is not None:
                mp, mdps, mdb, meq = kpis_mains
                col1, col2, col3, col4 = st.columns(4)
                col1.metric(
                    "Principal Mais Usado",
                    mp["nome"],
                    f'{int(mp["quantidade"]):,}'.replace(",", "."),
                )
                col2.metric(
                    "Melhor DPS (Principal)",
                    mdps["nome"],
                    f'{mdps["dps_medio"]:,.2f}'.replace(",", "X")
                    .replace(".", ",")
                    .replace("X", "."),
                )
                col3.metric(
                    "Maior Dano Boss (Principal)",
                    mdb["nome"],
                    f'{mdb["dano_boss_medio"]:,.2f}'.replace(",", "X")
                    .replace(".", ",")
                    .replace("X", "."),
                )
                col4.metric(
                    "Mais Equilibrado (Principal)",
                    meq["nome"],
                    f'{meq["score_composto"]:.2f}',
                    help="DPS + Dano Boss",
                )
            else:
                st.info("Nenhum personagem principal em vitórias.")

            st.divider()

            if kpis_secs[0] is not None:
                mp, mdps, mdb, meq = kpis_secs
                col5, col6, col7, col8 = st.columns(4)
                col5.metric(
                    "Secundário Mais Usado",
                    mp["nome"],
                    f'{int(mp["quantidade"]):,}'.replace(",", "."),
                )
                col6.metric(
                    "Melhor DPS (Secundário)",
                    mdps["nome"],
                    f'{mdps["dps_medio"]:,.2f}'.replace(",", "X")
                    .replace(".", ",")
                    .replace("X", "."),
                )
                col7.metric(
                    "Maior Dano Boss (Secundário)",
                    mdb["nome"],
                    f'{mdb["dano_boss_medio"]:,.2f}'.replace(",", "X")
                    .replace(".", ",")
                    .replace("X", "."),
                )
                col8.metric(
                    "Mais Equilibrado (Secundário)",
                    meq["nome"],
                    f'{meq["score_composto"]:.2f}',
                    help="DPS + Dano Boss",
                )
            else:
                st.info("Nenhum personagem secundário em vitórias.")

            st.divider()

            # --- Tabelas detalhadas ---
            if not mains.empty:
                stats_mains = (
                    mains.groupby(["character_id", "nome"])
                    .agg(
                        quantidade=("character_id", "size"),
                        dps_medio=("dps", "mean"),
                        dano_boss_medio=("damage_boss", "mean"),
                    )
                    .round(2)
                    .reset_index()
                )
                stats_mains = stats_mains.sort_values("dps_medio", ascending=False)

                st.subheader("Personagens Principais (em vitórias)")
                display_df_mains = stats_mains[
                    ["nome", "quantidade", "dps_medio", "dano_boss_medio"]
                ].rename(
                    columns={
                        "nome": "Personagem",
                        "quantidade": "Quantidade",
                        "dps_medio": "DPS Médio",
                        "dano_boss_medio": "Dano Médio contra Chefes",
                    }
                )

                st.dataframe(
                    display_df_mains,
                    hide_index=True,
                    width="stretch",
                    height=400,
                    column_config={
                        "DPS Médio": st.column_config.NumberColumn(
                            "DPS Médio",
                            format="localized",
                            help="Dano por segundo médio",
                        ),
                        "Dano Médio contra Chefes": st.column_config.NumberColumn(
                            "Dano Médio contra Chefes",
                            format="localized",
                            help="Dano total médio causado contra chefes",
                        ),
                        "Quantidade": st.column_config.NumberColumn(
                            "Quantidade",
                            format="localized",
                            help="Número de vezes usado em vitórias",
                        ),
                    },
                )
            else:
                st.info("Nenhum personagem principal em vitórias.")

            st.divider()

            if not secs.empty:
                stats_secs = (
                    secs.groupby(["character_id", "nome"])
                    .agg(
                        quantidade=("character_id", "size"),
                        dps_medio=("dps", "mean"),
                        dano_boss_medio=("damage_boss", "mean"),
                    )
                    .round(2)
                    .reset_index()
                )
                stats_secs = stats_secs.sort_values("dps_medio", ascending=False)

                st.subheader("Personagens Secundários (em vitórias)")
                display_df_secs = stats_secs[
                    ["nome", "quantidade", "dps_medio", "dano_boss_medio"]
                ].rename(
                    columns={
                        "nome": "Personagem",
                        "quantidade": "Quantidade",
                        "dps_medio": "DPS Médio",
                        "dano_boss_medio": "Dano Médio contra Chefes",
                    }
                )

                st.dataframe(
                    display_df_secs,
                    hide_index=True,
                    width="stretch",
                    height=400,
                    column_config={
                        "DPS Médio": st.column_config.NumberColumn(
                            "DPS Médio",
                            format="localized",
                            help="Dano por segundo médio",
                        ),
                        "Dano Médio contra Chefes": st.column_config.NumberColumn(
                            "Dano Médio contra Chefes",
                            format="localized",
                            help="Dano total médio causado contra chefes",
                        ),
                        "Quantidade": st.column_config.NumberColumn(
                            "Quantidade",
                            format="localized",
                            help="Número de vezes usado em vitórias",
                        ),
                    },
                )
            else:
                st.info("Nenhum personagem secundário em vitórias.")


with tab4:
    st.subheader("Partidas")

    # === Filtros locais ===
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)

    # Filtro por resultado (Vitória/Derrota)
    with col_f1:
        resultado_filtro = st.selectbox(
            "Resultado", options=["Todos", "Vitória", "Derrota"], key="tab4_resultado"
        )

    # Filtro por jogador
    with col_f2:
        jogadores_unicos = ["Todos"] + sorted(
            df_f["steam_name"].dropna().unique().tolist()
        )
        jogador_filtro = st.selectbox(
            "Jogador", options=jogadores_unicos, key="tab4_jogador"
        )

    # Filtro por jogador
    with col_f3:
        jogadores_unicos_id = ["Todos"] + sorted(
            df_f["steam_id"].dropna().unique().tolist()
        )
        jogador_id_filtro = st.selectbox(
            "Steam ID", options=jogadores_unicos_id, key="tab4_jogador_id"
        )

    # Filtro por versão
    with col_f4:
        versoes_unicas = ["Todas"] + sorted(df_f["version"].dropna().unique().tolist())
        versao_filtro = st.selectbox(
            "Versão", options=versoes_unicas, key="tab4_versao"
        )

        # Aplicar filtros locais ao df_f (que já está filtrado globalmente)
        df_filtrado_tab4 = df_f.copy()

        # Filtro por resultado
        if resultado_filtro == "Vitória":
            df_filtrado_tab4 = df_filtrado_tab4[df_filtrado_tab4["win"] == True]
        elif resultado_filtro == "Derrota":
            df_filtrado_tab4 = df_filtrado_tab4[df_filtrado_tab4["win"] == False]

        # Filtro por nome do jogador
        if jogador_filtro != "Todos":
            df_filtrado_tab4 = df_filtrado_tab4[
                df_filtrado_tab4["steam_name"] == jogador_filtro
            ]

        # Filtro por Steam ID
        if jogador_id_filtro != "Todos":
            df_filtrado_tab4 = df_filtrado_tab4[
                df_filtrado_tab4["steam_id"] == jogador_id_filtro
            ]

        # Filtro por versão
        if versao_filtro != "Todas":
            df_filtrado_tab4 = df_filtrado_tab4[
                df_filtrado_tab4["version"] == versao_filtro
            ]

    # === Funções de formatação (mantidas) ===
    def format_personagens(chars_data):
        if not isinstance(chars_data, list):
            return "–"
        nomes = []
        for char in chars_data:
            char_id = str(char.get("character", ""))
            nome = PERSONAGENS.get(char_id, char_id)
            nomes.append(nome)
        if not nomes:
            return "–"
        elif len(nomes) == 1:
            return nomes[0]
        else:
            return f"{nomes[0]}, {', '.join(nomes[1:])}"

    def format_lista(lista):
        if not isinstance(lista, list) or not lista:
            return "–"
        return ", ".join(str(item) for item in lista)

    # === Preparar dados para exibição ===
    df_exibicao = df_filtrado_tab4.sort_values("id", ascending=False)
    df_exibicao["composicao"] = df_exibicao["characters_damage_data"].apply(
        format_personagens
    )
    df_exibicao["reliquias"] = df_exibicao["relics_id"].apply(format_lista)
    df_exibicao["recompensas"] = df_exibicao["selected_rewards"].apply(format_lista)

    cols_exibir = [
        "id",
        "steam_id",
        "steam_name",
        "total_seconds",
        "version",
        "win",
        "wave",
        "difficulty",
        "multiplayer",
        "composicao",
        "reliquias",
        "recompensas",
        "total_damage",
    ]

    st.dataframe(
        df_exibicao[cols_exibir],
        width="stretch",
        hide_index=True,
        height=500,
        column_config={
            "total_damage": st.column_config.NumberColumn(
                "Dano Total", format="localized", help="Dano total causado na partida"
            ),
            "composicao": st.column_config.TextColumn(
                "Composição", help="Principal + Secundários"
            ),
            "reliquias": st.column_config.TextColumn(
                "Relíquias", help="IDs das relíquias usadas"
            ),
            "recompensas": st.column_config.TextColumn(
                "Recompensas", help="IDs das recompensas escolhidas"
            ),
        },
    )


st.divider()
st.caption("Dados carregados diretamente do Supabase • Atualizado a cada 5 minutos")
