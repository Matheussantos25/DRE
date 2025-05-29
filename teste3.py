import streamlit as st
import pandas as pd
from pandas.api.types import CategoricalDtype

# Exibe logo no topo da aplicação
st.image("m2inova_upscayl_4x_ultrasharp.png", use_container_width=True, clamp=False, output_format="PNG")

st.title("📊 Simulador de Projeção de DRE")

tabs = st.tabs([
    "Receitas",
    "Cenários de Crescimento",
    "Custos",
    "Despesas",
    "Resumo"
])

# ===================== ABA RECEITAS =====================
with tabs[0]:
    st.header("📈 Projeção de Receitas")

    # Entrada de múltiplos serviços
    servico_input = st.text_area(
        "Tipos de Serviço (um por linha)",
        value="Consulta",
        help="Digite cada tipo de serviço em uma linha separada."
    )
    tipos_servico = [s.strip() for s in servico_input.splitlines() if s.strip()]

    # Parâmetros de cada serviço
    params = {}
    for tipo in tipos_servico:
        with st.expander(f"Parâmetros para '{tipo}'", expanded=True):
            valor_venda_base = st.number_input(
                f"{tipo} - Valor de Venda Inicial (R$)",
                min_value=0.0, value=100.0, key=f"venda_{tipo}"
            )
            custo_unitario_base = st.number_input(
                f"{tipo} - Custo por Unidade Inicial (R$)",
                min_value=0.0, value=20.0, key=f"custo_{tipo}"
            )
            qtd_inicial = st.number_input(
                f"{tipo} - Quantidade Inicial", min_value=0, value=100, key=f"qtd_init_{tipo}"
            )
            qtd_maxima = st.number_input(
                f"{tipo} - Quantidade Máxima", min_value=0, value=500, key=f"qtd_max_{tipo}"
            )
            repasse_percentual = st.number_input(
                f"{tipo} - Repasse Médico (%)", min_value=0.0,
                max_value=100.0, value=30.0, key=f"repasse_{tipo}"
            )
            crescimento_percentual = st.number_input(
                f"{tipo} - Crescimento Mensal da Quantidade (%)", min_value=0.0,
                value=5.0, key=f"cres_{tipo}"
            )
            investimento_inicial = st.number_input(
                f"{tipo} - Investimento Inicial (R$)", min_value=0.0,
                value=10000.0, key=f"inv_{tipo}"
            )
            params[tipo] = {
                "valor_venda_base": valor_venda_base,
                "custo_unitario_base": custo_unitario_base,
                "qtd_inicial": qtd_inicial,
                "qtd_maxima": qtd_maxima,
                "repasse_percentual": repasse_percentual,
                "crescimento_percentual": crescimento_percentual,
                "investimento_inicial": investimento_inicial
            }

    meses = st.slider("Período de projeção (meses)", min_value=1, max_value=60, value=12)
    tipo_imposto = st.radio(
        "Tipo de Imposto",
        ["Imposto Único (12%)", "Por Faixa de Faturamento"]
    )

    # Container para resultados
    resultados = {}

    if st.button("📊 Gerar Projeção"):
        if not tipos_servico:
            st.warning("👉 Digite ao menos um Tipo de Serviço para gerar projeções.")
        else:
            # Soma dos investimentos iniciais de todos os serviços
            inv_total = sum(p["investimento_inicial"] for p in params.values())

            all_dados = []
            inflacao_anual  = 0.13
            inflacao_mensal = (1 + inflacao_anual)**(1/12) - 1

            # 1) Gera TODOS os registros mês-a-mês de cada serviço
            for tipo, p in params.items():
                venda0   = p["valor_venda_base"]
                custo0   = p["custo_unitario_base"]
                qtd0     = p["qtd_inicial"]
                qtd_max  = p["qtd_maxima"]
                repasse_pct = p["repasse_percentual"]
                cres_pct = p["crescimento_percentual"]

                quantidade      = qtd0
                valor_venda_mes = venda0
                custo_unit_mes  = custo0

                for mes in range(1, meses + 1):
                    rb = quantidade * valor_venda_mes
                    ct = quantidade * custo_unit_mes
                    rp = rb * repasse_pct/100

                    all_dados.append({
                        "Mês":            f"M{mes}",
                        "Receita Bruta":  rb,
                        "Custo Total":    ct,
                        "Repasse Médico": rp
                    })

                    quantidade      = min(quantidade * (1 + cres_pct/100), qtd_max)
                    valor_venda_mes *= (1 + inflacao_mensal)
                    custo_unit_mes  *= (1 + inflacao_mensal)

            # 2) DataFrame único e ordenação
            df_all = pd.DataFrame(all_dados)
            meses_cat = [f"M{i}" for i in range(1, meses+1)]
            df_all["Mês"] = df_all["Mês"].astype(
                CategoricalDtype(categories=meses_cat, ordered=True))
            df_all = df_all.sort_values("Mês").set_index("Mês")

            # 3) Agrega somando todos os serviços por mês
            df_agg = df_all.groupby(level=0).sum()

            # 4) Determina alíquota sobre a Receita Bruta TOTAL
            total_rec = df_agg["Receita Bruta"].sum()
            if tipo_imposto == "Imposto Único (12%)":
                aliquota = 0.12
            else:
                faixas = [
                    (0, 360000, 0.112),
                    (360000, 720000, 0.135),
                    (720000, 1800000, 0.16),
                    (1800000, 3600000, 0.21),
                    (3600000, 4800000, 0.33),
                ]
                aliquota = next((p for inf, sup, p in faixas if inf < total_rec <= sup), 0.0)
                if aliquota == 0.0:
                    st.warning("Receita total fora das faixas de tributação.")

            # 5) Calcula impostos, receita líquida, lucro bruto e acumulado
            df_agg["Impostos"]         = df_agg["Receita Bruta"] * aliquota
            df_agg["Receita Líquida"]  = df_agg["Receita Bruta"] - df_agg["Impostos"]
            df_agg["Lucro Bruto"]      = (df_agg["Receita Líquida"]
                                        - df_agg["Custo Total"]
                                        - df_agg["Repasse Médico"])
            df_agg["Lucro Acumulado"]  = df_agg["Lucro Bruto"].cumsum()

            # 6) Identifica payback (mês em que o acumulado >= total invested)
            payback_row = df_agg[df_agg["Lucro Acumulado"] >= inv_total]
            payback = payback_row.index[0] if not payback_row.empty else "Não atingido"

            # 7) Exibição consolidada
            st.subheader("📊 Projeção Consolidada (Todos os Serviços)")
            st.dataframe(df_agg.style.format({
                "Receita Bruta":    "R${:,.2f}",
                "Custo Total":      "R${:,.2f}",
                "Repasse Médico":   "R${:,.2f}",
                "Impostos":         "R${:,.2f}",
                "Receita Líquida":  "R${:,.2f}",
                "Lucro Bruto":      "R${:,.2f}",
                "Lucro Acumulado":  "R${:,.2f}"
            }))

            st.subheader("📈 Séries Consolidadas por Mês")
            st.line_chart(df_agg[[
                "Receita Bruta",
                "Receita Líquida",
                "Lucro Bruto"
            ]])

            # 8) Métricas finais
            st.metric("Receita Total Bruta", f"R$ {total_rec:,.2f}")
            st.metric("Imposto Total",       f"R$ {df_agg['Impostos'].sum():,.2f}")
            st.metric("Alíquota Efetiva",    f"{aliquota*100:.2f}%")
            st.metric("Investimento Total",  f"R$ {inv_total:,.2f}")
            st.metric("Payback",             payback)


# ===================== ABA CENÁRIOS =====================
with tabs[1]:
    st.header("📊 Análise de Cenários de Crescimento")

    qtd_inicial_cenario = st.number_input("Quantidade Inicial (cenários)", min_value=1, value=100)
    crescimento_conservador = [0.25, 0.20, 0.20]
    crescimento_otimista = [x + 0.20 for x in crescimento_conservador]
    crescimento_pessimista = [max(x - 0.20, 0.0) for x in crescimento_conservador]

    def gerar_series_crescimento(taxas_anuais):
        meses_lbl = []
        quantidades = []
        quantidade = qtd_inicial_cenario
        for ano_idx, taxa_anual in enumerate(taxas_anuais):
            taxa_mensal = (1 + taxa_anual) ** (1/12) - 1
            for m in range(12):
                numero = ano_idx * 12 + m + 1
                meses_lbl.append(f"M{numero}")
                quantidades.append(quantidade)
                quantidade *= (1 + taxa_mensal)
        return meses_lbl, quantidades

    meses_lbl, q_conservador = gerar_series_crescimento(crescimento_conservador)
    _, q_otimista = gerar_series_crescimento(crescimento_otimista)
    _, q_pessimista = gerar_series_crescimento(crescimento_pessimista)

    df_cenario = pd.DataFrame({
        "Mês": meses_lbl,
        "Conservador": q_conservador,
        "Otimista": q_otimista,
        "Pessimista": q_pessimista
    })

    # ————— Mesma lógica de categorical ordering —————
    cat_type_c = CategoricalDtype(categories=meses_lbl, ordered=True)
    df_cenario["Mês"] = df_cenario["Mês"].astype(cat_type_c)
    df_cenario = df_cenario.sort_values("Mês").set_index("Mês")
    # ——————————————————————————————————————

    st.subheader("📈 Gráfico de Crescimento - 3 Cenários")
    st.line_chart(df_cenario)

    st.subheader("📋 Tabela de Quantidades por Mês")
    st.dataframe(df_cenario.style.format("{:,.0f}"))


# ===================== ABA RESUMO =====================
with tabs[4]:
    st.header("📌 Resumo Consolidado de Indicadores")

    # se a projeção não foi gerada, df_agg não existirá
    if "df_agg" not in locals():
        st.info("Gere a projeção para ver o resumo consolidado aqui.")
    else:
        # 1) Calcula totais
        total_rec       = df_agg["Receita Bruta"].sum()
        total_custo     = df_agg["Custo Total"].sum()
        total_repasse   = df_agg["Repasse Médico"].sum()
        total_imp       = df_agg["Impostos"].sum()
        total_liquida   = df_agg["Receita Líquida"].sum()
        total_lucro     = df_agg["Lucro Bruto"].sum()
        investimento    = inv_total
        payback_label   = payback

        # 2) Exibe as métricas principais em colunas
        c1, c2, c3 = st.columns(3)
        c1.metric("Receita Bruta Total", f"R$ {total_rec:,.2f}")
        c1.metric("Custo Total",        f"R$ {total_custo:,.2f}")
        c2.metric("Repasse Médico Total", f"R$ {total_repasse:,.2f}")
        c2.metric("Imposto Total",        f"R$ {total_imp:,.2f}")
        c3.metric("Lucro Bruto Total",   f"R$ {total_lucro:,.2f}")
        c3.metric("Investimento Total",  f"R$ {investimento:,.2f}")
        st.metric("Payback", payback_label)

        # 3) Monta um DataFrame resumo para tabela e gráfico
        resumo_df = pd.DataFrame({
            "Valor (R$)": [
                total_rec,
                total_custo,
                total_repasse,
                total_imp,
                total_liquida,
                total_lucro,
                investimento
            ]
        }, index=[
            "Receita Bruta",
            "Custo Total",
            "Repasse Médico",
            "Impostos",
            "Receita Líquida",
            "Lucro Bruto",
            "Investimento"
        ])

        st.subheader("📋 Tabela Resumo Consolidado")
        st.dataframe(resumo_df.style.format("R${:,.2f}"))

        st.subheader("📊 Comparativo de Totais")
        # remove 'Investimento' do gráfico se quiser comparar só receitas e custos
        st.bar_chart(resumo_df["Valor (R$)"])
