import ee
from brdfCorrect import brdf_correct


def mask_landsat7_sr(image):
    """
    Creates bit masks for cloud shadow and cirrus from the band QA_PIXEL,
    and applies the mask to retain clear pixels only.

    :param image: ee.Image
    :return: ee.Image
    """
    cloud_shadow_bit_mask = (1 << 3)
    cloud_bit_mask = (1 << 5)
    qa = image.select('QA_PIXEL')
    mask = qa.bitwiseAnd(cloud_shadow_bit_mask).eq(0).And(qa.bitwiseAnd(cloud_bit_mask).eq(0))
    return image.updateMask(mask)


def apply_scaleing_offset(image):
    """
    Scales and offsets specified bands in a Landsat 7 image.
    :param image: ee.Image
    :return: ee.Image
    """
    bands_to_modify = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2']
    scale = ee.Number(2.75e-05)
    offset = ee.Number(-0.2)

    def scale_band(band_name):
        band = image.select(band_name)
        return band.multiply(scale).add(offset).rename(band_name)

    # scale and offset each specified band
    scaled_bands = [scale_band(band_name) for band_name in bands_to_modify]
    scaled_image = ee.ImageCollection(scaled_bands).toBands()
    original_names = ee.List(bands_to_modify)
    renamed_scaled_image = scaled_image.rename(original_names)

    # combine scaled bands with the original bands
    modified_image = image.select(image.bandNames().removeAll(bands_to_modify)) \
        .addBands(renamed_scaled_image)

    return modified_image


def get_ndvi(image):
    """
    Calculates normalized difference vegetation index (NDVI) from Landsat 7 image.
    :param image: ee.Image
    :return: ee.Image
    """
    ndvi = image.expression(
        '(nir - red) / (nir + red)', {
            'nir': image.select('nir'),
            'red': image.select('red')
        }).rename('ndvi').toFloat()
    return image.addBands(ndvi)


def get_nirv(image):
    """
    Calculates Near-Infrared Reflectance of Vegetation (NIRv) from Landsat 7 image.
    :param image: ee.Image
    :return: ee.Image
    """
    nirv = image.expression(
        '((nir - red) / (nir + red)) * nir', {
            'nir': image.select('nir'),
            'red': image.select('red')
        }).rename('nirv').toFloat()
    return image.addBands(nirv)


def get_vi_time_series(feature, image_collection, start_date, end_date, target='ndvi'):
    """
    Calculate the time series of mean pixel-based vegetation index over the given feature,
    using the longitude and latitude of the feature centroid to mark the location.
    :param feature: ee.Feature, the region of interest.
    :param image_collection: ee.ImageCollection, the image collection to map over.
    :param start_date: string, the start date of image, in format 'YYYY-MM-dd'.
    :param end_date: string, the end date of image, in format 'YYYY-MM-dd'.
    :param target: string, ndvi or nirv, default to ndvi.
    :return: ee.FeatureCollection, containing centroid location and VI values in each feature.
    """
    # get centroid location of the given feature
    centroid = feature.geometry().centroid()
    lon = centroid.coordinates().get(0)
    lat = centroid.coordinates().get(1)
    # filter images by date and location, and apply pre-process on images
    ic_filtered = image_collection \
        .filterBounds(feature.geometry()) \
        .filterDate(start_date, end_date) \
        .map(mask_landsat7_sr) \
        .map(apply_scaleing_offset) \
        .map(brdf_correct) \
        .map(get_ndvi) \
        .map(get_nirv)

    def calc_mean_vi(image, vi):
        return ee.Image(image).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=feature.geometry(),
            scale=30,
            maxPixels=1e9
        ).get(vi)

    def convert_list_to_feature(element):
        return ee.Feature(None, {
            'lon': lon,
            'lat': lat,
            'prop': element
        })

    # create a list of image and extract mean NDVI values from each image
    image_list = ic_filtered.toList(ic_filtered.select(target).size())
    vi_list = [calc_mean_vi(img, target) for img in image_list]
    id_list = ic_filtered.aggregate_array('system:index')
    # join all lists
    values = id_list.zip(vi_list)

    return ee.FeatureCollection([convert_list_to_feature(ele) for ele in values])
