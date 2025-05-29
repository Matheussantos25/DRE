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
            for tipo, p in params.items():
                # Extrai parâmetros
                venda0 = p["valor_venda_base"]
                custo0 = p["custo_unitario_base"]
                qtd0 = p["qtd_inicial"]
                qtd_max = p["qtd_maxima"]
                repasse_pct = p["repasse_percentual"]
                cres_pct = p["crescimento_percentual"]
                inv0 = p["investimento_inicial"]
                
                dados = []
                quantidade = qtd0
                total_receita = 0.0
                inflacao_anual = 0.13
                inflacao_mensal = (1 + inflacao_anual)**(1/12) - 1
                valor_venda_mes = venda0
                custo_unit_mes = custo0

                # Geração mensal
                for mes in range(1, meses + 1):
                    receita_bruta = quantidade * valor_venda_mes
                    custo_total = quantidade * custo_unit_mes
                    repasse_valor = receita_bruta * (repasse_pct / 100)
                    total_receita += receita_bruta

                    dados.append({
                        "Tipo": tipo,
                        "Mês": f"M{mes}",
                        "Quantidade": round(quantidade),
                        "Valor Venda (R$)": valor_venda_mes,
                        "Custo Unitário (R$)": custo_unit_mes,
                        "Receita Bruta (R$)": receita_bruta,
                        "Custo Total (R$)": custo_total,
                        "Repasse Médico (R$)": repasse_valor
                    })

                    quantidade = min(quantidade * (1 + cres_pct/100), qtd_max)
                    valor_venda_mes *= (1 + inflacao_mensal)
                    custo_unit_mes *= (1 + inflacao_mensal)

                # Alíquota
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
                    aliquota = next((p for inf, sup, p in faixas if inf < total_receita <= sup), 0.0)
                    if aliquota == 0.0:
                        st.warning(f"{tipo}: Receita fora das faixas de tributação.")

                # Lucro e payback
                lucro_acum = 0.0
                payback = None
                for row in dados:
                    imp = row["Receita Bruta (R$)"] * aliquota
                    liq = row["Receita Bruta (R$)"] - imp
                    lucro = liq - row["Custo Total (R$)"] - row["Repasse Médico (R$)"]

                    row["Impostos (R$)"] = imp
                    row["Receita Líquida (R$)"] = liq
                    row["Lucro Bruto (R$)"] = lucro

                    lucro_acum += lucro
                    row["Lucro Acumulado (R$)"] = lucro_acum
                    if payback is None and lucro_acum >= inv0:
                        payback = row["Mês"]

                df = pd.DataFrame(dados)
                # Ordenação
                meses_cat = [f"M{i}" for i in range(1, meses+1)]
                df["Mês"] = df["Mês"].astype(CategoricalDtype(categories=meses_cat, ordered=True))
                df = df.sort_values("Mês").set_index("Mês")

                # Resultados
                # Armazena resultados para o resumo

                resultados[tipo] = {
                    "df": df,
                    "total_receita": total_receita,
                    "total_imposto": df["Impostos (R$)"].sum(),
                    "aliquota": aliquota,
                    "payback": payback or "Não atingido"
                }

                # Exibição
                st.subheader(f"Projeção: {tipo}")
                st.dataframe(df.style.format({
                    "Valor Venda (R$)": "R${:,.2f}",
                    "Custo Unitário (R$)": "R${:,.2f}",
                    "Receita Bruta (R$)": "R${:,.2f}",
                    "Receita Líquida (R$)": "R${:,.2f}",
                    "Custo Total (R$)": "R${:,.2f}",
                    "Repasse Médico (R$)": "R${:,.2f}",
                    "Impostos (R$)": "R${:,.2f}",
                    "Lucro Bruto (R$)": "R${:,.2f}",
                    "Lucro Acumulado (R$)": "R${:,.2f}"
                }))

                st.line_chart(df[["Receita Bruta (R$)", "Receita Líquida (R$)", "Lucro Bruto (R$)"]])
                st.metric("Receita Total Bruta", f"R$ {total_receita:,.2f}")
                st.metric("Imposto Total", f"R$ {df['Impostos (R$)'].sum():,.2f}")
                st.metric("Alíquota Efetiva", f"{aliquota*100:.2f}%")
                st.metric("Payback", payback or "Não atingido")

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
    st.header("📌 Resumo Consolidado de Serviços")
    if resultados:
        resumo = []
        for tipo, res in resultados.items():
            resumo.append({
                "Tipo": tipo,
                "Receita Total (R$)": res["total_receita"],
                "Imposto Total (R$)": res["total_imposto"],
                "Alíquota (%)": res["aliquota"] * 100,
                "Payback": res["payback"]
            })
        df_resumo = pd.DataFrame(resumo).set_index("Tipo")
        st.dataframe(df_resumo.style.format({
            "Receita Total (R$)": "R${:,.2f}",
            "Imposto Total (R$)": "R${:,.2f}",
            "Alíquota (%)": "{:.2f}%"
        }))
        # Gráfico comparativo de receita
        st.subheader("Comparativo de Receita por Serviço")
        st.bar_chart(df_resumo["Receita Total (R$)"])
    else:
        st.info("Gere as projeções para ver o resumo consolidado aqui.")
