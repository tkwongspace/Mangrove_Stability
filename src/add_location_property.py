import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from tqdm import tqdm


def get_satellite_info():
    ask = input("-- Landsat / MODIS? (L/M): ").strip().upper()
    if ask == "L":
        return "Landsat"
    elif ask == "M":
        return "MODIS"
    else:
        get_satellite_info()


# load the table of points
# points_table = pd.read_csv(r"../data/vi_gee/Landsat/Mean_ndvi_1.csv")

path_to_table = input("-- Please input the folder of point tables: ")
csv_candidates = [f for f in os.listdir(path_to_table) if f.endswith('.csv') and not f.startswith("._")]
print(f">> {len(csv_candidates)} CSV files found.")

satellite = get_satellite_info()

export_csv_name = input("-- Please input the full path of the exported CSV file (ends with .csv): ")

# initialize an empty list to hold the processed DataFrames
processed_dfs = []

# load the shapefile
protected_area = gpd.read_file(r"../data/pa.shp")
unprotected_area = gpd.read_file(r"../data/npa.shp")

# process each csv file
pbar = tqdm(total=len(csv_candidates), desc="Arranging tables")
for csv in csv_candidates:
    # load the table of points
    points_table = pd.read_csv(os.path.join(path_to_table, csv))

    # create a geo-dataframe from the points dataframe
    geometry = [Point(xy) for xy in zip(points_table['lon'], points_table['lat'])]
    points_gdf = gpd.GeoDataFrame(points_table, geometry=geometry, crs="EPSG:4326")

    # # Debug output: check crs
    # print("CRS of points_gdf: ", points_gdf.crs)
    # print("CRS of protected area: ", protected_area.crs)
    # print("CRS of unprotected area: ", unprotected_area.crs)

    # ensure the coordinate reference system (CRS) is the same for all geo-dataframes
    points_gdf = points_gdf.to_crs(protected_area.crs)

    # spatial join points with (un)protected areas
    protected_points = gpd.sjoin(points_gdf, protected_area, how="left", predicate="within")
    unprotected_points = gpd.sjoin(points_gdf, unprotected_area, how="left", predicate="within")

    # initialize the location column with None
    points_gdf['state'] = None

    # set state to (un)protected where points are within (un)protected areas
    protected_indices = protected_points[protected_points.index_right.notnull()].index
    points_gdf.loc[protected_indices, 'state'] = 'protected'
    unprotected_indices = unprotected_points[unprotected_points.index_right.notnull()].index
    points_gdf.loc[unprotected_indices, 'state'] = 'unprotected'

    # create new columns for point ID and date
    # split point ID and capture date from system:index
    split_column = points_gdf['system:index'].str.split('_', expand=True)
    if satellite == "Landsat":
        # Landsat system:index format -> {Point ID}_{Product Abbr.}_{TIle ID}_{Acquired Date}
        points_gdf['pointID'] = split_column[0]
        points_gdf['date'] = pd.to_datetime(split_column[3], format='%Y%m%d')
        points_gdf['filename'] = csv.split(".")[0]
    else:
        # MODIS system:index format -> {Point ID}_{Acquired Year}_{Acquired Month}_{Acquired Day}
        points_gdf['pointID'] = split_column[0]
        points_gdf['date'] = pd.to_datetime(split_column[1] + split_column[2] + split_column[3], format='%Y%m%d')
        points_gdf['filename'] = csv.split(".")[0]

    # append the processed data frame to the list
    processed_dfs.append(points_gdf)
    pbar.update(1)
pbar.close()

# concatenate all processed data frames
combined_df = pd.concat(processed_dfs, ignore_index=True)

# save the result
combined_df.to_csv(export_csv_name, index=False)

print(f">> Finish arranging all tables in given folder.")
