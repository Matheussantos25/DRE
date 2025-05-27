import streamlit as st
import pandas as pd
from pandas.api.types import CategoricalDtype

st.title("📊 Simulador de Projeção de DRE")

tabs = st.tabs([
    "Receitas",
    "Cenários de Crescimento",
    "Custos",
    "Despesas",
    "Resumo (em breve)"
])

# ===================== ABA RECEITAS =====================
with tabs[0]:
    st.header("📈 Projeção de Receitas")

    # ————— Inputs —————
    tipo_servico = st.text_input("Tipo de Serviço", value="Consulta")
    valor_venda_base = st.number_input("Valor de Venda Inicial (R$)", min_value=0.0, value=100.0)
    custo_unitario_base = st.number_input("Custo por Unidade Inicial (R$)", min_value=0.0, value=20.0)
    qtd_inicial = st.number_input("Quantidade Inicial", min_value=0, value=100)
    qtd_maxima = st.number_input("Quantidade Máxima", min_value=0, value=500)
    repasse_percentual = st.number_input("Repasse Médico (%)", min_value=0.0, max_value=100.0, value=30.0)
    crescimento_percentual = st.number_input("Crescimento Mensal da Quantidade (%)", min_value=0.0, value=5.0)
    meses = st.slider("Período de projeção (meses)", min_value=1, max_value=60, value=12)
    investimento_inicial = st.number_input("Investimento Inicial (R$)", min_value=0.0, value=10000.0)
    tipo_imposto = st.radio("Tipo de Imposto", ["Imposto Único (12%)", "Por Faixa de Faturamento"])

    if st.button("📊 Gerar Projeção"):
        # ————— Geração dos dados —————
        dados = []
        quantidade = qtd_inicial
        total_receita = 0.0
        inflacao_anual = 0.13
        inflacao_mensal = (1 + inflacao_anual) ** (1 / 12) - 1
        valor_venda_mes = valor_venda_base
        custo_unitario_mes = custo_unitario_base

        for mes in range(1, meses + 1):
            receita_bruta = quantidade * valor_venda_mes
            custo_total = quantidade * custo_unitario_mes
            repasse_valor = receita_bruta * (repasse_percentual / 100)
            total_receita += receita_bruta

            dados.append({
                "Mês": f"M{mes}",
                "Quantidade": round(quantidade),
                "Valor Venda com Inflação (R$)": valor_venda_mes,
                "Custo Unitário com Inflação (R$)": custo_unitario_mes,
                "Receita Operacional Bruta (R$)": receita_bruta,
                "Custo Total (R$)": custo_total,
                "Repasse Médico (R$)": repasse_valor
            })

            quantidade = min(quantidade * (1 + crescimento_percentual / 100), qtd_maxima)
            valor_venda_mes *= (1 + inflacao_mensal)
            custo_unitario_mes *= (1 + inflacao_mensal)

        # ————— Cálculo do imposto —————
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
            aliquota = next((perc for inf, sup, perc in faixas if inf < total_receita <= sup), 0.0)
            if aliquota == 0.0:
                st.warning("Receita fora das faixas de tributação. Nenhum imposto calculado.")

        # ————— Cálculo de lucro e payback —————
        lucro_acumulado = 0.0
        payback_mes = None
        for row in dados:
            imposto_mes = row["Receita Operacional Bruta (R$)"] * aliquota
            receita_liquida = row["Receita Operacional Bruta (R$)"] - imposto_mes
            lucro = receita_liquida - row["Custo Total (R$)"] - row["Repasse Médico (R$)"]

            row["Impostos (R$)"] = imposto_mes
            row["Receita Operacional Líquida (R$)"] = receita_liquida
            row["Lucro Bruto (R$)"] = lucro

            lucro_acumulado += lucro
            row["Lucro Acumulado (R$)"] = lucro_acumulado
            if payback_mes is None and lucro_acumulado >= investimento_inicial:
                payback_mes = row["Mês"]

        df = pd.DataFrame(dados)

        # —————** AQUI FAZEMOS O TRUQUE DA ORDENAÇÃO **—————
        month_cats = [f"M{i}" for i in range(1, meses + 1)]
        cat_type = CategoricalDtype(categories=month_cats, ordered=True)
        df["Mês"] = df["Mês"].astype(cat_type)
        df = df.sort_values("Mês").set_index("Mês")
        # ————————————————————————————————————————————

        # ————— Exibição —————
        st.subheader("📋 Tabela de Projeção com Inflação de 13% a.a.")
        st.dataframe(df.style.format({
            "Valor Venda com Inflação (R$)": "R${:,.2f}",
            "Custo Unitário com Inflação (R$)": "R${:,.2f}",
            "Receita Operacional Bruta (R$)": "R${:,.2f}",
            "Receita Operacional Líquida (R$)": "R${:,.2f}",
            "Custo Total (R$)": "R${:,.2f}",
            "Repasse Médico (R$)": "R${:,.2f}",
            "Impostos (R$)": "R${:,.2f}",
            "Lucro Bruto (R$)": "R${:,.2f}",
            "Lucro Acumulado (R$)": "R${:,.2f}"
        }))

        st.subheader("📈 Gráfico Comparativo")
        st.line_chart(df[[
            "Receita Operacional Bruta (R$)",
            "Receita Operacional Líquida (R$)",
            "Lucro Bruto (R$)"
        ]])

        st.subheader("📌 Resumo Anual")
        st.metric("Receita Total Bruta", f"R$ {total_receita:,.2f}")
        st.metric("Imposto Total", f"R$ {df['Impostos (R$)'].sum():,.2f}")
        st.metric("Alíquota Efetiva", f"{aliquota * 100:.2f}%")
        st.metric("Investimento Inicial", f"R$ {investimento_inicial:,.2f}")
        st.metric("Payback", payback_mes or "Não atingido")


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
