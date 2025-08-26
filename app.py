# --- ETAPA 1: IMPORTAR BIBLIOTECAS ---
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- ETAPA 2: CARREGAR OS DADOS BRUTOS ---
@st.cache_data
def carregar_dados():
    df = pd.read_excel("Importação e Exportação - 19-25.xlsx")
    # Renomear colunas fixas
    df = df.rename(columns={
        "Países": "Pais",
        "Código SH4": "SH4",
        "Descrição SH4": "Descricao",
        "Via": "Via",
        "UF do Produto": "UF"
    })
    
    # --- ETAPA 3: TRANSFORMAR PARA FORMATO LONGO ---
    colunas_fixas = ["Pais", "SH4", "Descricao", "Via", "UF"]
    colunas_valores = [c for c in df.columns if c not in colunas_fixas]
    df_long = df.melt(
        id_vars=colunas_fixas,
        value_vars=colunas_valores,
        var_name="Metrica",
        value_name="Valor"
    )
    
    # Tratar colunas derivadas
    df_long["Ano"] = df_long["Metrica"].str.extract(r"(\d{4})").astype(int)
    df_long["Tipo"] = df_long["Metrica"].apply(lambda x: "Exportação" if "Exportação" in x else "Importação")
    df_long["Metrica"] = df_long["Metrica"].apply(lambda x: "Valor US$ FOB" if "Valor" in x else "Quilograma Líquido")
    df_long["Valor"] = pd.to_numeric(df_long["Valor"], errors="coerce").fillna(0)
    
    # --- ETAPA 4: PIVOTAR PARA VALOR E QUILO LADO A LADO ---
    df_final = df_long.pivot(
        index=["Pais", "SH4", "Descricao", "Via", "UF", "Ano", "Tipo"],
        columns="Metrica",
        values="Valor"
    ).reset_index()
    df_final = df_final.rename(columns={
        "Valor US$ FOB": "Valor_FOB",
        "Quilograma Líquido": "Quilo_Liquido"
    })
    
    return df_final

# --- FUNÇÃO PARA FORMATAR NÚMEROS ---
def formatar_numero(valor):
    if pd.isna(valor) or valor == 0:
        return "0"
    return f"{valor:,.0f}".replace(",", ".")

def formatar_moeda(valor):
    if pd.isna(valor) or valor == 0:
        return "$0"
    return f"${valor:,.0f}".replace(",", ".")

def encurtar_nome_produto(nome, max_chars=25):
    """Encurta nomes de produtos para gráficos mantendo a identidade"""
    if len(nome) <= max_chars:
        return nome
    
    # Mapeamento específico para produtos conhecidos
    mapeamentos = {
        "Soja, mesmo triturada": "Soja",
        "Açúcares de cana ou de beterraba e sacarose quimicamente pura, no estado sólido": "Açúcar",
        "Óleo de soja e respectivas fracções, mesmo refinados, mas não quimicamente modificados": "Óleo de Soja",
        "Álcool etílico não desnaturado, com um teor alcoólico em volume igual ou superior a 80 % vol; álcool etílico e aguardentes, desnaturados, com qualquer teor alcoólico": "Álcool Etílico",
        "Tortas e outros resíduos sólidos da extração do óleo de soja": "Farelo de Soja",
        "Milho": "Milho"
    }
    
    # Verificar se existe mapeamento específico
    for nome_completo, nome_curto in mapeamentos.items():
        if nome_completo in nome:
            return nome_curto
    
    # Se não houver mapeamento, truncar e adicionar "..."
    return nome[:max_chars-3] + "..."

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Dashboard Comércio Exterior", layout="wide")
st.title("📊 Dashboard de Importação e Exportação")

# Carregar dados
df_final = carregar_dados()

# --- CONSTANTES ---
ordem_vias = [
    "MARITIMA", "FLUVIAL", "RODOVIARIA", "FERROVIARIA", "AEREA",
    "LACUSTRE", "VICINAL FRONTEIRICO", "MEIOS PROPRIOS", "EM MAOS",
    "DUTOS", "ENTRADA/SAIDA FICTA", "CONDUTO/REDE DE TRANSMISSAO", "VIA NAO DECLARADA"
]

mapa_sh4 = {
    1005: "Milho",
    1201: "Soja, mesmo triturada",
    1507: "Óleo de soja e fracções",
    1701: "Açúcares (cana/beterraba, sacarose pura)",
    2207: "Álcool etílico >= 80% vol / Aguardentes",
    2304: "Tortas e resíduos de óleo de soja"
}

# --- SIDEBAR PARA NAVEGAÇÃO ---
st.sidebar.title("🎛️ Controles")

# Seleção da página
pagina = st.sidebar.selectbox(
    "Escolha a análise:",
    ["📋 Tops Interativos", "🔍 Análise Detalhada por País", "📈 Evolução Temporal"]
)

# FILTRO DE ANOS
anos_disponiveis = sorted(df_final["Ano"].unique())
anos_selecionados = st.sidebar.multiselect(
    "Filtrar Anos (desmarque 2025 se incompleto):",
    anos_disponiveis,
    default=[ano for ano in anos_disponiveis if ano != 2025],
    key="filtro_anos"
)

# FILTRO DE PRODUTOS SH4
sh4_disponiveis = sorted(df_final["SH4"].unique())
sh4_selecionados = st.sidebar.multiselect(
    "Filtrar Produtos SH4:",
    sh4_disponiveis,
    default=sh4_disponiveis,
    format_func=lambda x: f"{x} - {mapa_sh4.get(x, 'Produto não mapeado')}",
    key="filtro_sh4"
)

# Aplicar filtros
if anos_selecionados:
    df_final = df_final[df_final["Ano"].isin(anos_selecionados)].copy()
else:
    st.sidebar.error("Selecione pelo menos um ano!")
    st.stop()

if sh4_selecionados:
    df_final = df_final[df_final["SH4"].isin(sh4_selecionados)].copy()
else:
    st.sidebar.error("Selecione pelo menos um produto SH4!")
    st.stop()

# --- PÁGINA 1: TOPS INTERATIVOS ---
if pagina == "📋 Tops Interativos":
    st.header("📋 Tops Interativos")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        tipo_analise = st.selectbox(
            "Tipo de Análise:",
            ["🌍 Global", "🚢 Por Via", "📦 Por Produto"]
        )
    
    with col2:
        fluxo_tipo = st.selectbox(
            "Fluxo Comercial:",
            ["Exportação", "Importação", "Ambos"]
        )
    
    with col3:
        top_n = st.selectbox("Top N:", [5, 10, 15, 20], index=0)
    
    with col4:
        # Seletor de ano
        anos_tops = ["Todos"] + sorted(df_final["Ano"].unique(), reverse=True)
        ano_selecionado_tops = st.selectbox(
            "Selecionar Ano:",
            anos_tops,
            key="ano_tops"
        )
    
    # Filtros específicos baseados no tipo de análise
    if tipo_analise == "🚢 Por Via":
        via_selecionada = st.selectbox("Selecione a Via:", ordem_vias)
    elif tipo_analise == "📦 Por Produto":
        sh4_selecionado = st.selectbox(
            "Selecione o Produto:", 
            list(mapa_sh4.keys()),
            format_func=lambda x: f"{x} - {mapa_sh4[x]}"
        )
    
    # Função para mostrar tops
    def mostrar_top_interativo(df, group_cols, tipos_fluxo, titulo, topn=5, filtro_adicional=None, ano_especifico=None):
        if ano_especifico and ano_especifico != "Todos":
            # Mostrar apenas o ano selecionado
            anos = [ano_especifico]
        else:
            # Mostrar todos os anos
            anos = sorted(df["Ano"].unique())
        
        # Se "Ambos" foi selecionado, mostrar Exportação e depois Importação separadamente
        if "Ambos" in tipos_fluxo:
            tipos_para_mostrar = ["Exportação", "Importação"]
        else:
            tipos_para_mostrar = tipos_fluxo
        
        for tipo_fluxo in tipos_para_mostrar:
            if "Ambos" in tipos_fluxo:
                st.subheader(f"📊 {tipo_fluxo}")
            
            for ano in anos:
                df_ano = df[df["Ano"] == ano].copy()
                
                # Aplicar filtro adicional se necessário
                if filtro_adicional:
                    df_ano = filtro_adicional(df_ano)
                
                # Filtrar por tipo de fluxo específico
                df_ano = df_ano[df_ano["Tipo"] == tipo_fluxo]
                
                if not df_ano.empty:
                    tabela = (
                        df_ano.groupby(group_cols, as_index=False)
                        [["Valor_FOB", "Quilo_Liquido"]]
                        .sum()
                        .sort_values("Valor_FOB", ascending=False)
                        .head(topn)
                    )
                    
                    if not tabela.empty:
                        # Adicionar colunas formatadas para exibição
                        tabela["Valor FOB ($)"] = tabela["Valor_FOB"].apply(formatar_moeda)
                        tabela["Quantidade Líquida (Kg)"] = tabela["Quilo_Liquido"].apply(formatar_numero)
                        
                        # Selecionar colunas para exibição
                        colunas_exibicao = group_cols + ["Valor FOB ($)", "Quantidade Líquida (Kg)"]
                        
                        if "Ambos" in tipos_fluxo:
                            st.write(f"**{titulo} - {tipo_fluxo} - {ano}**")
                        else:
                            st.subheader(f"{titulo} - {ano}")
                        
                        st.dataframe(tabela[colunas_exibicao], use_container_width=True)
                        
                        # Gráfico
                        if len(tabela) > 1:
                            fig = px.bar(
                                tabela, 
                                x=group_cols[0], 
                                y="Valor_FOB",
                                title=f"Valor FOB ($) - {titulo} - {tipo_fluxo} - {ano}",
                                labels={"Valor_FOB": "Valor FOB ($)"}
                            )
                            fig.update_layout(xaxis_tickangle=-45)
                            st.plotly_chart(fig, use_container_width=True)
    
    # Executar análise baseada na seleção
    tipos_selecionados = [fluxo_tipo] if fluxo_tipo != "Ambos" else ["Ambos"]
    
    if tipo_analise == "🌍 Global":
        mostrar_top_interativo(df_final, ["Pais"], tipos_selecionados, "Top Global", top_n, ano_especifico=ano_selecionado_tops)
    
    elif tipo_analise == "🚢 Por Via":
        filtro_via = lambda df: df[df["Via"] == via_selecionada]
        mostrar_top_interativo(
            df_final, ["Pais"], tipos_selecionados, 
            f"Via {via_selecionada}", top_n, filtro_via, ano_especifico=ano_selecionado_tops
        )
    
    elif tipo_analise == "📦 Por Produto":
        filtro_produto = lambda df: df[df["SH4"] == sh4_selecionado]
        mostrar_top_interativo(
            df_final, ["Pais"], tipos_selecionados,
            f"{sh4_selecionado} - {mapa_sh4[sh4_selecionado]}", top_n, filtro_produto, ano_especifico=ano_selecionado_tops
        )

# --- PÁGINA 2: ANÁLISE DETALHADA POR PAÍS ---
elif pagina == "🔍 Análise Detalhada por País":
    st.header("🔍 Análise Detalhada por País")
    
    # Selecionar país
    paises_disponiveis = sorted(df_final["Pais"].unique())
    pais_selecionado = st.selectbox("Selecione o País:", paises_disponiveis)
    
    if pais_selecionado:
        df_pais = df_final[df_final["Pais"] == pais_selecionado].copy()
        
        # ========== RESUMO GERAL DO PAÍS ==========
        st.subheader(f"📊 Resumo Geral - {pais_selecionado}")
        
        resumo_pais = df_pais.groupby(["Ano", "Tipo"], as_index=False)["Valor_FOB"].sum()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Tabela resumo
            pivot_resumo = resumo_pais.pivot(index="Ano", columns="Tipo", values="Valor_FOB").fillna(0)
            pivot_resumo["Saldo"] = pivot_resumo.get("Exportação", 0) - pivot_resumo.get("Importação", 0)
            
            # Formatar para exibição
            pivot_resumo_formatado = pivot_resumo.copy()
            for col in pivot_resumo_formatado.columns:
                pivot_resumo_formatado[col] = pivot_resumo_formatado[col].apply(formatar_moeda)
            
            st.dataframe(pivot_resumo_formatado, use_container_width=True)
        
        with col2:
            # Gráfico evolução total
            fig = px.line(
                resumo_pais, x="Ano", y="Valor_FOB", color="Tipo",
                title=f"Evolução do Fluxo Comercial - {pais_selecionado}",
                labels={"Valor_FOB": "Valor FOB ($)"}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # ========== ANÁLISE DE PRODUTOS ==========
        st.subheader(f"🔍 Detalhamento por Produtos - {pais_selecionado}")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            tipo_fluxo_pais = st.selectbox(
                "Tipo de Fluxo:", 
                ["Exportação", "Importação"], 
                key="tipo_fluxo_pais"
            )
        
        with col2:
            modo_analise_produto = st.selectbox(
                "Modo de Análise:",
                ["Ano Específico", "Evolução Temporal"],
                key="modo_analise_produto"
            )
        
        with col3:
            if modo_analise_produto == "Ano Específico":
                anos_pais = sorted(df_pais["Ano"].unique(), reverse=True)
                ano_selecionado = st.selectbox(
                    "Selecione o Ano:",
                    anos_pais,
                    key="ano_produto"
                )
        
        df_produtos_pais = df_pais[df_pais["Tipo"] == tipo_fluxo_pais].copy()
        
        if not df_produtos_pais.empty:
            # Resumo por produto e ano
            resumo_produtos = (
                df_produtos_pais.groupby(["SH4", "Descricao", "Ano"], as_index=False)
                [["Valor_FOB", "Quilo_Liquido"]].sum()
            )
            
            if modo_analise_produto == "Ano Específico":
                # TODOS os produtos no ano selecionado (não apenas top 10)
                produtos_ano = (
                    resumo_produtos[resumo_produtos["Ano"] == ano_selecionado]
                    .sort_values("Valor_FOB", ascending=False)
                )
                
                if not produtos_ano.empty:
                    # Calcular percentuais antes da formatação
                    total_fob_tabela = produtos_ano["Valor_FOB"].sum()
                    produtos_ano["% FOB"] = (produtos_ano["Valor_FOB"] / total_fob_tabela * 100).round(1).apply(lambda x: f"{x}%")
                    
                    # Formatar para exibição
                    produtos_ano["Valor FOB ($)"] = produtos_ano["Valor_FOB"].apply(formatar_moeda)
                    produtos_ano["Quantidade Líquida (Kg)"] = produtos_ano["Quilo_Liquido"].apply(formatar_numero)
                    
                    st.write(f"**Produtos em {ano_selecionado}:**")
                    st.dataframe(
                        produtos_ano[["SH4", "Descricao", "Valor FOB ($)", "% FOB", "Quantidade Líquida (Kg)"]], 
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Calcular e mostrar totais fora da tabela
                    total_fob = produtos_ano["Valor_FOB"].sum()
                    total_quilo = produtos_ano["Quilo_Liquido"].sum()
                    
                    st.success(f"📊 **TOTAL**: {formatar_moeda(total_fob)} | {formatar_numero(total_quilo)} Kg")
                else:
                    st.write(f"Não há dados para {ano_selecionado}")
            
            else:  # Evolução Temporal
                # Mostrar evolução de TODOS os produtos principais
                st.write(f"**Evolução Temporal dos Principais Produtos:**")
                
                # Pegar todos os produtos relevantes do ano mais recente
                ano_mais_recente = resumo_produtos["Ano"].max()
                produtos_evolucao = (
                    resumo_produtos[resumo_produtos["Ano"] == ano_mais_recente]
                    .sort_values("Valor_FOB", ascending=False)["SH4"].tolist()
                )
                
                df_evolucao_produtos = resumo_produtos[resumo_produtos["SH4"].isin(produtos_evolucao)]
                
                if not df_evolucao_produtos.empty:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Tabela evolução com nomes encurtados na coluna
                        pivot_evolucao = df_evolucao_produtos.pivot(
                            index="Ano", columns="Descricao", values="Valor_FOB"
                        ).fillna(0)
                        
                        # Renomear colunas para nomes encurtados
                        colunas_encurtadas = {}
                        for col in pivot_evolucao.columns:
                            colunas_encurtadas[col] = encurtar_nome_produto(col)
                        pivot_evolucao = pivot_evolucao.rename(columns=colunas_encurtadas)
                        
                        pivot_evolucao_formatado = pivot_evolucao.copy()
                        for col in pivot_evolucao_formatado.columns:
                            pivot_evolucao_formatado[col] = pivot_evolucao_formatado[col].apply(formatar_moeda)
                        
                        st.dataframe(pivot_evolucao_formatado, use_container_width=True)
                    
                    with col2:
                        # Gráfico evolução com nomes encurtados
                        df_evolucao_produtos_grafico = df_evolucao_produtos.copy()
                        df_evolucao_produtos_grafico["Descricao_Curta"] = df_evolucao_produtos_grafico["Descricao"].apply(encurtar_nome_produto)
                        
                        fig = px.line(
                            df_evolucao_produtos_grafico, 
                            x="Ano", y="Valor_FOB", 
                            color="Descricao_Curta",
                            title=f"Evolução dos Produtos",
                            labels={"Valor_FOB": "Valor FOB ($)", "Descricao_Curta": "Produto"}
                        )
                        st.plotly_chart(fig, use_container_width=True)
        
        # ========== ANÁLISE DE VIAS DE TRANSPORTE - REESCRITO COMPLETAMENTE ==========
        st.subheader(f"🚢 Vias de Transporte - {pais_selecionado}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            tipo_fluxo_via = st.selectbox(
                "Tipo de Fluxo:", 
                ["Exportação", "Importação"], 
                key="tipo_fluxo_via"
            )
        
        with col2:
            modo_analise_via = st.selectbox(
                "Modo de Análise:",
                ["Evolução Temporal", "Composição por Produtos"],
                key="modo_analise_via"
            )
        
        # Filtrar dados por tipo de fluxo
        df_vias_pais = df_pais[df_pais["Tipo"] == tipo_fluxo_via].copy()
        
        if not df_vias_pais.empty:
            
            if modo_analise_via == "Evolução Temporal":
                st.write(f"**Evolução das Vias de Transporte - {tipo_fluxo_via}:**")
                
                # Resumo por via e ano
                resumo_vias_tempo = (
                    df_vias_pais.groupby(["Via", "Ano"], as_index=False)
                    [["Valor_FOB", "Quilo_Liquido"]].sum()
                )
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Tabela evolução das vias (com FOB e Quantidade)
                    pivot_vias_fob = resumo_vias_tempo.pivot(index="Ano", columns="Via", values="Valor_FOB").fillna(0)
                    pivot_vias_quilo = resumo_vias_tempo.pivot(index="Ano", columns="Via", values="Quilo_Liquido").fillna(0)
                    
                    st.write("**💰 Evolução por Valor FOB ($):**")
                    pivot_vias_fob_formatado = pivot_vias_fob.copy()
                    for col in pivot_vias_fob_formatado.columns:
                        pivot_vias_fob_formatado[col] = pivot_vias_fob_formatado[col].apply(formatar_moeda)
                    st.dataframe(pivot_vias_fob_formatado, use_container_width=True)
                    
                    st.write("**📦 Evolução por Quantidade (Kg):**")
                    pivot_vias_quilo_formatado = pivot_vias_quilo.copy()
                    for col in pivot_vias_quilo_formatado.columns:
                        pivot_vias_quilo_formatado[col] = pivot_vias_quilo_formatado[col].apply(formatar_numero)
                    st.dataframe(pivot_vias_quilo_formatado, use_container_width=True)
                
                with col2:
                    # Gráfico evolução das principais vias
                    vias_principais = (
                        resumo_vias_tempo.groupby("Via")["Valor_FOB"].sum()
                        .sort_values(ascending=False).head(5).index.tolist()
                    )
                    
                    df_vias_principais = resumo_vias_tempo[resumo_vias_tempo["Via"].isin(vias_principais)]
                    
                    fig = px.line(
                        df_vias_principais, 
                        x="Ano", y="Valor_FOB", 
                        color="Via",
                        title=f"Evolução das Top 5 Vias - {tipo_fluxo_via}",
                        labels={"Valor_FOB": "Valor FOB ($)"}
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            else:  # Composição por Produtos
                st.write(f"**Composição por Produtos nas Vias - {tipo_fluxo_via}:**")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Seletor de via
                    vias_disponiveis = sorted(df_vias_pais["Via"].unique())
                    via_selecionada = st.selectbox(
                        "Selecione a Via:",
                        vias_disponiveis,
                        key="via_composicao"
                    )
                
                with col2:
                    # Seletor de ano
                    anos_vias = sorted(df_vias_pais["Ano"].unique(), reverse=True)
                    ano_via = st.selectbox(
                        "Selecione o Ano:",
                        anos_vias,
                        key="ano_via_composicao"
                    )
                
                # Análise da composição
                df_composicao = df_vias_pais[
                    (df_vias_pais["Via"] == via_selecionada) & 
                    (df_vias_pais["Ano"] == ano_via)
                ].copy()
                
                if not df_composicao.empty:
                    composicao_produtos = (
                        df_composicao.groupby(["SH4", "Descricao"], as_index=False)
                        [["Valor_FOB", "Quilo_Liquido"]].sum()
                        .sort_values("Valor_FOB", ascending=False)
                    )
                    
                    # Tabela produtos com FOB e Quantidade (fora das colunas)
                    composicao_produtos["Valor FOB ($)"] = composicao_produtos["Valor_FOB"].apply(formatar_moeda)
                    composicao_produtos["Quantidade Líquida (Kg)"] = composicao_produtos["Quilo_Liquido"].apply(formatar_numero)
                    
                    st.write(f"**Produtos - Via {via_selecionada} - {ano_via}:**")
                    st.dataframe(composicao_produtos[["SH4", "Descricao", "Valor FOB ($)", "Quantidade Líquida (Kg)"]], use_container_width=True, hide_index=True)
                    
                    # Agora as duas colunas com % e gráfico
                    col1_viz, col2_viz = st.columns(2)
                    
                    with col1_viz:
                        # Tabela de percentuais
                        st.write("**📊 Composição Percentual:**")
                        composicao_top8 = composicao_produtos.head(8).copy()
                        total_valor = composicao_top8["Valor_FOB"].sum()
                        
                        tabela_percentual = pd.DataFrame({
                            "Produto": composicao_top8["Descricao"].apply(encurtar_nome_produto),
                            "Percentual (%)": (composicao_top8["Valor_FOB"] / total_valor * 100).round(1).apply(lambda x: f"{x}%")
                        })
                        
                        st.dataframe(tabela_percentual, use_container_width=True, hide_index=True)
                    
                    with col2_viz:
                        # Gráfico pizza com nomes encurtados
                        composicao_para_grafico = composicao_produtos.head(8).copy()
                        composicao_para_grafico["Descricao_Curta"] = composicao_para_grafico["Descricao"].apply(encurtar_nome_produto)
                        
                        fig = px.pie(
                            composicao_para_grafico, 
                            values="Valor_FOB", 
                            names="Descricao_Curta",
                            title=f"Composição - {via_selecionada} - {ano_via}"
                        )
                        fig.update_traces(
                            textposition='inside', 
                            textinfo='percent+label',
                            textfont_size=10
                        )
                        fig.update_layout(
                            font=dict(size=12),
                            legend=dict(font=dict(size=10))
                        )
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.write(f"Não há dados para {via_selecionada} em {ano_via}")
        
        else:
            st.write(f"Não há dados de {tipo_fluxo_via.lower()} para este país.")

# --- PÁGINA 3: EVOLUÇÃO TEMPORAL ---
elif pagina == "📈 Evolução Temporal":
    st.header("📈 Evolução Temporal")
    
    # ========== ANÁLISE TEMPORAL GERAL ==========
    st.subheader("🌍 Evolução do Comércio Exterior Brasileiro")
    
    evolucao_geral = df_final.groupby(["Ano", "Tipo"], as_index=False)["Valor_FOB"].sum()
    
    col1, col2 = st.columns(2)
    
    with col1:
        pivot_geral = evolucao_geral.pivot(index="Ano", columns="Tipo", values="Valor_FOB").fillna(0)
        pivot_geral["Saldo"] = pivot_geral.get("Exportação", 0) - pivot_geral.get("Importação", 0)
        
        # Formatar para exibição
        pivot_geral_formatado = pivot_geral.copy()
        for col in pivot_geral_formatado.columns:
            pivot_geral_formatado[col] = pivot_geral_formatado[col].apply(formatar_moeda)
        
        st.dataframe(pivot_geral_formatado, use_container_width=True)
    
    with col2:
        fig = px.line(
            evolucao_geral, x="Ano", y="Valor_FOB", color="Tipo",
            title="Evolução Geral do Comércio Exterior",
            labels={"Valor_FOB": "Valor FOB ($)"}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # ========== EVOLUÇÃO POR PRODUTO ==========
    st.subheader("📦 Evolução por Produto")
    
    evolucao_produtos = (
        df_final.groupby(["SH4", "Descricao", "Ano", "Tipo"], as_index=False)["Valor_FOB"].sum()
    )
    
    # Seletores
    col1, col2 = st.columns(2)
    with col1:
        produtos_evolucao = st.multiselect(
            "Selecione produtos:",
            list(mapa_sh4.keys()),
            default=list(mapa_sh4.keys())[:3],
            format_func=lambda x: f"{x} - {mapa_sh4.get(x, 'N/A')}"
        )
    
    with col2:
        tipo_evolucao = st.selectbox(
            "Tipo de Fluxo:",
            ["Exportação", "Importação"],
            key="tipo_evolucao"
        )
    
    if produtos_evolucao:
        df_evolucao_filtrado = evolucao_produtos[
            (evolucao_produtos["SH4"].isin(produtos_evolucao)) &
            (evolucao_produtos["Tipo"] == tipo_evolucao)
        ]
        
        # Aplicar nomes encurtados para o gráfico
        df_evolucao_filtrado_grafico = df_evolucao_filtrado.copy()
        df_evolucao_filtrado_grafico["Descricao_Curta"] = df_evolucao_filtrado_grafico["Descricao"].apply(encurtar_nome_produto)
        
        fig = px.line(
            df_evolucao_filtrado_grafico, 
            x="Ano", y="Valor_FOB", 
            color="Descricao_Curta",
            title=f"Evolução de Produtos - {tipo_evolucao}",
            labels={"Valor_FOB": "Valor FOB ($)", "Descricao_Curta": "Produto"}
        )
        st.plotly_chart(fig, use_container_width=True)

# --- FOOTER --- ok
st.sidebar.markdown("---")
st.sidebar.markdown("**💡 Dicas:**")
st.sidebar.markdown("• Desmarque 2025 se os dados estão incompletos")
st.sidebar.markdown("• Use os filtros para análises específicas")
st.sidebar.markdown("• Analise países detalhadamente na seção específica")
st.sidebar.markdown("• FOB e Quantidade sempre aparecem juntos")