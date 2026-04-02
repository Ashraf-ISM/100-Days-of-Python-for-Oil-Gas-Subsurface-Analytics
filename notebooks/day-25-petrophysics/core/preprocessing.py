def clean_data(df):
    df = df.replace(-999.25, None)
    df = df.fillna(method="ffill")
    return df
