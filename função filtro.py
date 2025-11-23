def filter_blood_general(df_general):
    df_general["pedido_inicial"] = df_general["n_mero_do_pedido"].astype(str).str[:-2]
    resultados = []
    df_vazio = df_general[df_general["n_mero_do_pedido"].astype(str) == ""]
    df_sangue = df_general[df_general["qual_tipo_de_material"].astype(str).str.contains("5") & (df_general["n_mero_do_pedido"].astype(str) != "")]
    df_outros = df_general[~df_general["qual_tipo_de_material"].astype(str).str.contains("5") & (df_general["n_mero_do_pedido"].astype(str) != "")]
    for pedido, grupo in df_sangue.groupby("pedido_inicial"):
        positivas = grupo[grupo["qual_microorganismo"].notna() & (grupo["qual_microorganismo"] != "")]
        negativas = grupo[grupo["qual_microorganismo"].isna() | (grupo["qual_microorganismo"] == "")]
        if len(grupo) == 1:
            resultados.append(grupo.iloc[0].to_dict())
            continue
        adicionados = set()
        for _, row in positivas.iterrows():
            micro = row["qual_microorganismo"]
            ver_res = str(row.get("ver_resultado_em", "")).strip().lower()
            if micro not in adicionados and ver_res == "não":
                resultados.append(row.to_dict())
                adicionados.add(micro)
        for _, row in positivas.iterrows():
            micro = row["qual_microorganismo"]
            ver_res = str(row.get("ver_resultado_em", "")).strip().lower()
            if micro not in adicionados and ver_res == "sim":
                resultados.append(row.to_dict())
                adicionados.add(micro)
        if len(adicionados) == 0 and len(negativas) > 0:
            resultados.append(negativas.iloc[0].to_dict())
    df_final = pd.DataFrame(resultados)
    if len(df_outros) > 0:
        df_final = pd.concat([df_final, df_outros], ignore_index=True)
    if len(df_vazio) > 0:
        df_final = pd.concat([df_final, df_vazio], ignore_index=True)
    df_final.drop(columns=["pedido_inicial"], inplace=True, errors="ignore")
    return df_final