import fiona
import numpy as np

from rasterio.enums import Resampling
from rasterio.warp import reproject
from rasterio.features import shapes
from shapely.geometry import shape, mapping
from pyproj import CRS, Transformer
from math import sqrt
from tqdm import tqdm


def create_shapefile(src, data, data_type, longitude_in_meter,
                     latitude_in_meter, transform, target_resolution,
                     path_to_export, prefix_to_export, file_name):
    data_array, new_transform = resample_data(
        src=src,
        data=data,
        lon_m=longitude_in_meter,
        lat_m=latitude_in_meter,
        transform=transform,
        crs=src.crs,
        target_resolution=target_resolution,
    )
    # extract the forest class
    if data_type == "CLCD":
        forest_mask = data_array == 2
    elif data_type == "GP":
        # select band values not equal to 0
        forest_mask = data_array != 0
    else:
        forest_mask = get_selection_criteria(data_array)
    # convert the mask to polygons
    print(">> Reading shapes of pixels in target class...")
    results = (
        {'properties': {'raster_val': v}, 'geometry': s}
        for i, (s, v) in enumerate(
            shapes(forest_mask.astype(np.uint8), mask=forest_mask, transform=new_transform))
    )
    # define schema for the shapefile
    schema = {
        'geometry': 'Polygon',
        'properties': {'raster_val': 'int'}
    }
    print(">> Ready to start conversion..")
    # initialize progress bar
    total_polygons = np.sum(forest_mask)
    # check if any polygons to be output
    if total_polygons == 0:
        print(f"-! There is no plantation polygon detected in {file_name}.")
        return
    else:
        pbar = tqdm(total=total_polygons, desc="Converting polygons")
        # write the polygons to a shapefile
        if prefix_to_export is not None:
            path_to_export = f"{path_to_export}/{prefix_to_export}_{file_name}.shp"
        with fiona.open(path_to_export, 'w', driver='ESRI Shapefile', crs=src.crs, schema=schema) as out:
            for elem in results:
                out.write({
                    'geometry': mapping(shape(elem['geometry'])),
                    'properties': {'raster_val': elem['properties']['raster_val']}
                })
                pbar.update(1)
        pbar.close()  # close progress bar when done


def degrees_to_meters(latitude, longitude, latitude_resolution, longitude_resolution):
    """
    Converts resolution from degrees to meters at the given latitude and longitude.
    :param latitude:
    :param longitude:
    :param latitude_resolution:
    :param longitude_resolution:
    :return:
    """

    # define WGS84 coordinate system
    wgs84 = CRS.from_epsg(4326)
    # define a local UTM zone coordinate system
    utm_zone = get_utm_zone(longitude)
    utm = CRS.from_proj4(f"+proj=utm +zone={utm_zone} +datum=WGS84")

    transformer = Transformer.from_crs(wgs84, utm, always_xy=True)

    # convert latitude and longitude resolution to meters
    lon1, lat1 = transformer.transform(longitude, latitude)
    lon2, _ = transformer.transform(longitude + longitude_resolution, latitude)
    _, lat3 = transformer.transform(longitude, latitude_resolution + latitude)

    longitude_res_in_meter = sqrt((lon2 - lon1) ** 2)
    latitude_res_in_meter = sqrt((lat3 - lat1) ** 2)

    return longitude_res_in_meter, latitude_res_in_meter


def get_raster_type():
    print("-- Please select the following pre-defined types of your input raster:")
    print("   [A] CLCD images (albert, 30m), [B] Global Plantation Products (WGS84, 0.0003deg), [C] Others.")
    choice = input('   A/B/C: ').strip().upper()
    if choice == "A":
        print(">> CLCD product selected.")
        tif_type = "CLCD"
        return tif_type
    elif choice == "B":
        print(">> Global Plantation product selected.")
        tif_type = "GP"
        return tif_type
    elif choice == "C":
        print(">> Not pre-defined product. Please set up the criteria for shapefile creation later.")
        tif_type = "others"
        return tif_type
    else:
        print("!! Invalid input. Please enter letter A, B or C.")
        return get_raster_type()


def get_resample_info(src, raster_type):
    # read the first band only
    data = src.read(1)
    # display current resolution
    lon_m, lat_m = get_resolution(src, raster_type)
    print(f"-- Current resolution: {lon_m:.2f} meters x {lat_m:.2f} meters.")
    # ask if perform resampling
    resample = input("   Resample the raster? (yes/no): ").strip().lower()
    if resample == 'yes':
        print(">> Setting up the profile for resampling...")
        # ask for the target resolution
        target_resolution = float(input("-- Target resolution (in meters): ").strip())
    else:
        print(">> No resampling selected.")
        target_resolution = None

    return data, lon_m, lat_m, target_resolution


def get_selection_criteria(d):
    criteria_type = input("Select a range or a specific band value? (value/range): ").strip().lower()
    if criteria_type == 'value':
        value = int(input("Please enter the band value to select: ").strip())
        return d == value
    elif criteria_type == 'range':
        min_val = float(input("Please enter the lower range of band value: ").strip())
        max_val = float(input("Please enter the upper range of band value: ").strip())
        return (d >= min_val) & (d <= max_val)
    else:
        print("Invalid input. Please enter 'value' or 'range'.")
        return get_selection_criteria(d)


def get_utm_zone(lon):
    """
    Calculate UTM zone from given longitude.
    :param (float) lon: Target longitude to estimate UTM zone.
    :return: (int) UTM zone ID.
    """
    return int((lon + 180) / 6) + 1


def get_resolution(data, data_type):
    if data_type == 'CLCD':
        lon_res_m, lat_res_m = data.res
    else:
        # calculate the resolution in meters
        lon_res, lat_res = data.res
        center_lat = (data.bounds.top + data.bounds.bottom) / 2
        center_lon = (data.bounds.left + data.bounds.right) / 2
        lon_res_m, lat_res_m = degrees_to_meters(center_lat, center_lon, lat_res, lon_res)
    return lon_res_m, lat_res_m


def reproject_in_chunk(source, destination, src_transform, src_crs, dst_transform, dst_crs,
                       method, chunk_size=250):
    height, width = source.shape
    for i in range(0, height, chunk_size):
        for j in range(0, width, chunk_size):
            window = ((i, min(i + chunk_size, height)), (j, min(j + chunk_size, width)))
            src_chunk = source[window[0][0]:window[0][1], window[1][0]:window[1][1]]

            # skip empty chunks (if sources chunk is None or all Zeros)
            if src_chunk is None or np.all(src_chunk == 0):
                continue

            dst_chunk = np.empty_like(src_chunk)
            try:
                reproject(
                    source=src_chunk,
                    destination=dst_chunk,
                    srctransform=src_transform,
                    src_crs=src_crs,
                    dsttransform=dst_transform,
                    dst_crs=dst_crs,
                    resampling=method
                )
                destination[window[0][0]:window[0][1], window[1][0]:window[1][1]] = dst_chunk
            except Exception as e:
                print(f"-! Error re-projecting chunk ({i}, {j}): {e}.")


def reproject_with_progress(source, destination, src_transform, src_crs, dst_transform, dst_crs, method):
    # create a progress bar
    total = source.size
    pbar = tqdm(total=total, desc="Resampling the raster")

    def update_progress(block_num, block_size, total_blocks):
        pbar.update(block_size)

    reproject(
        source=source,
        destination=destination,
        src_transform=src_transform,
        src_crs=src_crs,
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        resampling=method,
        num_threads=2,
        callback=update_progress
    )
    pbar.close()


def resample_data(src, data, lon_m, lat_m, transform, crs, target_resolution=None):
    try:
        if target_resolution:
            print(">> Getting ready for resampling...")
            # calculate new dimensions
            new_width = int((data.shape[1] * lon_m) / target_resolution)
            new_height = int((data.shape[0] * lat_m) / target_resolution)
            # calculate new transform
            scale_x = target_resolution / lon_m
            scale_y = target_resolution / lat_m
            new_transform = src.transform * src.transform.scale(scale_x, scale_y)
            # create a new array for the resampled data
            resampled_data = np.empty((new_height, new_width), dtype=data.dtype)

            # resample data to the target resolution
            print(">> Resampling the raster...")
            # reproject_with_progress(
            #     source=data,
            #     destination=resampled_data,
            #     src_transform=transform,
            #     src_crs=crs,
            #     dst_transform=new_transform,
            #     dst_crs=crs,
            #     method=Resampling.mode
            # )
            # reproject_in_chunk(
            #     source=data,
            #     destination=resampled_data,
            #     src_transform=transform,
            #     src_crs=crs,
            #     dst_transform=new_transform,
            #     dst_crs=crs,
            #     method=Resampling.mode,
            #     chunk_size=250*20
            # )
            reproject(
                source=data,
                destination=resampled_data,
                src_transform=transform,
                src_crs=crs,
                dst_transform=new_transform,
                dst_crs=crs,
                resampling=Resampling.mode
            )
            data = resampled_data
            print(">> Resample finished.")
            return data, new_transform
        else:
            new_transform = transform
            return data, new_transform

    except Exception as e:
        print(f"An unexpected error occurred while resampling the data: {e}.")


def whether_to_clip():
    clip_choice = input("-- Perform shapefile creation over mask? (yes / no): ").strip().lower()
    if clip_choice == "yes":
        path_for_mask = input("-- Path to the clip feature: ")
        path_for_export = input("-- Path to the folder for export file: ")
        prefix_for_export = input("-- Prefix for export files (output format: prefix_province.shp): ")
        return path_for_mask, path_for_export, prefix_for_export
    elif clip_choice == "no":
        path_for_mask = None
        path_for_export = input("-- Path to the export file (ends with .shp): ")
        prefix_for_export = None
        return path_for_mask, path_for_export, prefix_for_export
    else:
        print("!! Invalid input. Please enter letter yes or no.")
        return whether_to_clip()
