import streamlit as st
import pandas as pd

st.title("📊 Simulador de Projeção de DRE")

tabs = st.tabs(["Receitas", "Custos", "Despesas", "Resumo (em breve)"])

with tabs[0]:  # Aba de Receitas
    st.header("📈 Projeção de Receitas")

    # Entradas
    tipo_servico = st.text_input("Tipo de Serviço", value="Consulta")
    valor_venda = st.number_input("Valor de Venda (R$)", min_value=0.0, value=100.0)
    qtd_inicial = st.number_input("Quantidade Inicial", min_value=0, value=100)
    qtd_maxima = st.number_input("Quantidade Máxima", min_value=0, value=500)
    custo_unitario = st.number_input("Custo por Unidade (R$)", min_value=0.0, value=20.0)
    repasse_percentual = st.number_input("Repasse Médico (%)", min_value=0.0, max_value=100.0, value=30.0)
    crescimento_percentual = st.number_input("Crescimento Mensal da Quantidade (%)", min_value=0.0, value=5.0)
    meses = st.slider("Período de projeção (meses)", min_value=1, max_value=60, value=12)
    investimento_inicial = st.number_input("Investimento Inicial (R$)", min_value=0.0, value=10000.0)
    tipo_imposto = st.radio("Tipo de Imposto", ["Imposto Único (12%)", "Por Faixa de Faturamento"])

    if st.button("📊 Gerar Projeção"):
        dados = []
        quantidade = qtd_inicial
        total_receita = 0.0

        # Loop de projeção
        for mes in range(1, meses + 1):
            receita_bruta = quantidade * valor_venda
            custo_total = quantidade * custo_unitario
            repasse_valor = receita_bruta * (repasse_percentual / 100)
            total_receita += receita_bruta

            dados.append({
                "Mês": f"M{mes}",
                "Quantidade": round(quantidade),
                "Receita Operacional Bruta (R$)": receita_bruta,
                "Custo Total (R$)": custo_total,
                "Repasse Médico (R$)": repasse_valor
            })

            quantidade = min(quantidade * (1 + crescimento_percentual / 100), qtd_maxima)

        # Alíquota de imposto
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
            aliquota = 0.0
            for inf, sup, perc in faixas:
                if inf < total_receita <= sup:
                    aliquota = perc
                    break
            if aliquota == 0.0:
                st.warning("Receita fora das faixas de tributação. Nenhum imposto calculado.")

        # Cálculo de impostos, ROL, lucro e payback
        lucro_acumulado = 0.0
        payback_mes = None

        for row in dados:
            receita_bruta = row["Receita Operacional Bruta (R$)"]
            imposto_mes = receita_bruta * aliquota
            receita_liquida = receita_bruta - imposto_mes
            lucro = receita_liquida - row["Custo Total (R$)"] - row["Repasse Médico (R$)"]

            row["Impostos (R$)"] = imposto_mes
            row["Receita Operacional Líquida (R$)"] = receita_liquida
            row["Lucro Bruto (R$)"] = lucro

            lucro_acumulado += lucro
            row["Lucro Acumulado (R$)"] = lucro_acumulado

            if payback_mes is None and lucro_acumulado >= investimento_inicial:
                payback_mes = row["Mês"]

        # Construir DataFrame
        df = pd.DataFrame(dados)

        # Exibir Tabela
        st.subheader("📋 Tabela de Projeção")
        st.dataframe(df.style.format({
            "Receita Operacional Bruta (R$)": "R${:,.2f}",
            "Receita Operacional Líquida (R$)": "R${:,.2f}",
            "Custo Total (R$)": "R${:,.2f}",
            "Repasse Médico (R$)": "R${:,.2f}",
            "Impostos (R$)": "R${:,.2f}",
            "Lucro Bruto (R$)": "R${:,.2f}",
            "Lucro Acumulado (R$)": "R${:,.2f}"
        }))

        # Gráfico comparativo
        st.subheader("📈 Gráfico Comparativo")
        st.line_chart(df.set_index("Mês")[[
            "Receita Operacional Bruta (R$)",
            "Receita Operacional Líquida (R$)",
            "Lucro Bruto (R$)"
        ]])

        # Resumo Final
        st.subheader("📌 Resumo Anual")
        imposto_total = df["Impostos (R$)"].sum()
        st.metric("Receita Total Bruta", f"R$ {total_receita:,.2f}")
        st.metric("Imposto Total", f"R$ {imposto_total:,.2f}")
        st.metric("Alíquota Efetiva", f"{aliquota * 100:.2f}%")
        st.metric("Investimento Inicial", f"R$ {investimento_inicial:,.2f}")
        st.metric("Payback", payback_mes if payback_mes else "Não atingido")
