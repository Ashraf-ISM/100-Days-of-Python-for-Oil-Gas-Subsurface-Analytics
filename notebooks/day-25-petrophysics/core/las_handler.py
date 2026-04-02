import lasio

def load_las_file(path):
    las = lasio.read(path)
    df = las.df()
    df.reset_index(inplace=True)
    return df
