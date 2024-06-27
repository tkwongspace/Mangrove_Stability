# Arrange csv tables from earth engine
# (c) Zijian HUANG 2024

import time
import pandas as pd

path_to_tables = r'../data/vi_gee/'

# REPORT
print(f">> Task starts at {time.strftime('%H:%M:%S', time.localtime())}.")

df = pd.DataFrame()
maximum_id_of_csv = 5
for csv_id in range(1, maximum_id_of_csv+1):
    print(f".. Now on csv #{csv_id}/{maximum_id_of_csv}.")
    # base number of feature ID in the table
    id_start = (csv_id - 1) * 400
    # join tables of both vegetation indices
    vi_df = pd.DataFrame()
    vi_df['id'] = vi_df['date'] = vi_df['lon'] = vi_df['lat'] = pd.Series(dtype='object')
    for vi in ['ndvi', 'nirv']:
        df0 = pd.read_csv(path_to_tables + f'Mean_{vi}_{csv_id}.csv',
                          usecols=['system:index', 'lat', 'lon', 'target'])
        # separate out feature ID and image date from system:index
        df0['id'] = df0['system:index'].str.split('_', expand=True)[0].astype(int) + id_start
        df0['date'] = pd.to_datetime(df0['system:index'].str.split('_', expand=True)[3],
                                     format='%Y%m%d')
        # rename the column of vegetation index
        df0 = df0.rename(columns={'target': vi})
        # reorder the table
        df0 = df0[['id', 'date', 'lon', 'lat', vi]]
        # summarize multiple vi of the same feature at the same date
        # due to tiles intersection
        df0 = df0.groupby(['id', 'date', 'lon', 'lat'])[vi].mean().reset_index()
        vi_df = pd.merge(vi_df, df0,
                         on=['id', 'date', 'lon', 'lat'],
                         how='outer')
    # separate the year and month of the image date
    vi_df['year'] = vi_df['date'].dt.year
    vi_df['month'] = vi_df['date'].dt.month
    df = pd.concat([df, vi_df], ignore_index=True)
    print(f">> Task #{csv_id}/{maximum_id_of_csv} finished at {time.strftime('%H:%M:%S', time.localtime())}.")

# output to disk
df.to_csv(r'../data/vi_gee.csv', index=False)

print(">> ALL PROCESS FINISHED.")
