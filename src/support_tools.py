import os


def get_files_from_folder(path, suffix='.csv', omit='._'):
    tables = [f for f in os.listdir(path) if f.endswith(suffix) and not f.startswith(omit)]
    print(f">> {len(tables)} CSV files found.")
    return tables


def get_satellite_info():
    ask = input("-- Landsat / MODIS? (L/M): ").strip().upper()
    if ask == "L":
        return "Landsat"
    elif ask == "M":
        return "MODIS"
    else:
        get_satellite_info()
