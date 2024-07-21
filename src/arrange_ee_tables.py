# Arrange csv tables from earth engine
# (c) Zijian HUANG 2024

import os
import time
import pandas as pd
from tqdm import tqdm
from support_tools import get_files_from_folder, get_satellite_info


# load the export csv files from earth engine
path_to_csv = input("-- Please input the folder of point tables: ")
csv_candidates = get_files_from_folder(path_to_csv)

satellite = get_satellite_info()

export_csv_name = input("-- Please input the full path of the exported CSV file (ends with .csv): ")

# REPORT
print(f">> Task starts at {time.strftime('%H:%M:%S', time.localtime())}.")

# initialize an empty list to hold the processed DataFrames
processed_dfs = []
pbar = tqdm(total=len(csv_candidates), desc="Arranging tables")
for csv in csv_candidates:
    # file ID
    table_prefix = csv.split(".")[0]
    table_name_split = table_prefix.split("_")
    vi = table_name_split[1]
    file_id = table_name_split[2]
    # load the table
    result_table = pd.read_csv(os.path.join(path_to_csv, csv))
    # create new columns for point ID and date
    split_column = result_table['system:index'].str.split('_', expand=True)
    if satellite == "Landsat":
        # Landsat {system:index} format -> {Point ID}_{Product Abbr.}_{TIle ID}_{Acquired Date}
        result_table['pointID'] = split_column[0]
        result_table['date'] = pd.to_datetime(split_column[3], format='%Y%m%d')
        result_table['vi'] = vi
        result_table['fileID'] = file_id
    else:
        # MODIS
        continue
    # append the processed data frame to the list
    export_table = result_table[['fileID', 'pointID', 'vi', 'lat', 'lon', 'date', 'target']]
    processed_dfs.append(export_table)
    pbar.update(1)
pbar.close()

# concatenate all processed data frames
combined_df = pd.concat(processed_dfs, ignore_index=True)

# output to disk
combined_df.to_csv(export_csv_name, index=False)

print(">> Finish arranging all tables in given folder.")
