import ee
import math


def brdf_correct(image):
    """
    Performs BRDF correction to Landsat images.
    Codes created by Daniel Wiell & Erik Lindquist of the UNFAO
    shared at https://code.earthengine.google.com/3a6761dea6f1bf54b03de1b84dc375c6
    Methods published in Roy DP et al. A general method to normalize Landsat reflectance data
      to narid BRDF adjusted reflectance. Remote Sensing of Environment. 2016, 176: 255-271.
    :param image:
    :return:
    """
    # Functions
    def view_angles(image, corners):
        max_distance_to_scene_edge = 1000000
        max_satellite_zenith = 7.5
        upper_center = point_between(corners['upperLeft'], corners['upperRight'])
        lower_center = point_between(corners['lowerLeft'], corners['lowerRight'])
        slope = slope_between(lower_center, upper_center)
        slope_perp = ee.Number(-1).divide(slope)
        set_image(image, 'viewAz', ee.Image(ee.Number(math.pi / 2).subtract(slope_perp.atan())), {})

        left_line = to_line(corners['upperLeft'], corners['lowerLeft'])
        right_line = to_line(corners['upperRight'], corners['lowerRight'])
        left_distance = ee.FeatureCollection(left_line).distance(max_distance_to_scene_edge)
        right_distance = ee.FeatureCollection(right_line).distance(max_distance_to_scene_edge)
        view_zenith = right_distance.multiply(max_satellite_zenith * 2) \
            .divide(right_distance.add(left_distance)) \
            .subtract(max_satellite_zenith)
        set_image(image, 'viewZen', view_zenith.multiply(math.pi).divide(180), {})

    def solar_position(image, constants):
        date = ee.Date(ee.Number(image.get('system:time_start')))
        seconds_in_hour = 3600

        set_image(image, 'longDeg', ee.Image.pixelLonLat().select('longitude'), {})
        set_image(image, 'latRad', ee.Image.pixelLonLat().select('latitude').multiply(constants['pi']).divide(180), {})
        set_image(image, 'hourGMT', ee.Number(date.getRelative('second', 'day')).divide(seconds_in_hour), {})
        set_image(image, 'jdp', date.getFraction('year'), {})
        set_image(image, 'jdpr', 'i.jdp * 2 * {pi}', constants)
        set_image(image, 'meanSolarTime', 'i.hourGMT + i.longDeg / 15', constants)
        set_image(image, 'localSolarDiff', '(0.000075 + 0.001868 * cos(i.jdpr) - 0.032077 * sin(i.jdpr) ' +
                  '- 0.014615 * cos(2 * i.jdpr) - 0.040849 * sin(2 * i.jdpr)) * 12 * 60 / {pi}', constants)
        set_image(image, 'trueSolarTime', 'i.meanSolarTime + i.localSolarDiff / 60 - 12', constants)
        set_image(image, 'angleHour', 'i.trueSolarTime * 15 * {pi} / 180', constants)
        set_image(image, 'delta',
                  '0.006918 - 0.399912 * cos(i.jdpr) + 0.070257 * sin(i.jdpr) - 0.006758 * cos(2 * i.jdpr) ' +
                  '+ 0.000907 * sin(2 * i.jdpr) - 0.002697 * cos(3 * i.jdpr) + 0.001480 * sin(3 * i.jdpr)', constants)
        set_image(image, 'cosSunZen', 'sin(i.latRad) * sin(i.delta) + cos(i.latRad) * cos(i.delta) * cos(i.angleHour)',
                  constants)
        set_image(image, 'sunZen', 'acos(i.cosSunZen)', constants)
        set_image(image, 'sinSunAzSW',
                  to_image(image, 'cos(i.delta) * sin(i.angleHour) / sin(i.sunZen)', constants).clamp(-1, 1), constants)
        set_image(image, 'cosSunAzSW',
                  '(-cos(i.latRad) * sin(i.delta) + sin(i.latRad) * cos(i.delta) * cos(i.angleHour)) / sin(i.sunZen)',
                  constants)
        set_image(image, 'sunAzSW', 'asin(i.sinSunAzSW)', constants)
        set_if(image, 'sunAzSW', 'i.cosSunAzSW <= 0', '{pi} - i.sunAzSW', 'sunAzSW', constants)
        set_if(image, 'sunAzSW', 'i.cosSunAzSW > 0 and i.sinSunAzSW <= 0', '2 * {pi} + i.sunAzSW', 'sunAzSW', constants)
        set_image(image, 'sunAz', 'i.sunAzSW + {pi}', constants)
        set_if(image, 'sunAz', 'i.sunAz > 2 * {pi}', 'i.sunAz - 2 * {pi}', 'sunAz', constants)

    def sun_zen_out(image, constants):
        set_image(image, 'centerLat',
                  ee.Number(
                      ee.Geometry(image.get('system:footprint')).bounds().centroid(30).coordinates().get(0)).multiply(
                      constants['pi']).divide(180), {})
        set_image(image, 'sunZenOut', '(31.0076 - 0.1272 * i.centerLat + 0.01187 * pow(i.centerLat, 2) ' +
                  '+ 2.40E-05 * pow(i.centerLat, 3) - 9.48E-07 * pow(i.centerLat, 4) - 1.95E-09 * pow(i.centerLat, 5) ' +
                  '+ 6.15E-11 * pow(i.centerLat, 6)) * {pi}/180', constants)

    def ross_thick(image, band_name, sun_zen, view_zen, relative_sun_view_az, constants):
        args = {'sunZen': sun_zen, 'viewZen': view_zen, 'relativeSunViewAz': relative_sun_view_az}
        cos_phase_angle(image, 'cosPhaseAngle', sun_zen, view_zen, relative_sun_view_az, constants)
        set_image(image, 'phaseAngle', 'acos(i.cosPhaseAngle)', constants)
        set_image(image, band_name, '(({pi}/2 - i.phaseAngle) * i.cosPhaseAngle + sin(i.phaseAngle)) ' +
                  '/ (cos({sunZen}) + cos({viewZen})) - {pi}/4', {**args, **constants})

    def li_thin(image, band_name, sun_zen, view_zen, relative_sun_view_az, constants):
        args = {'sunZen': sun_zen, 'viewZen': view_zen, 'relativeSunViewAz': relative_sun_view_az, 'h/b': 2}
        angle_prime(image, 'sunZenPrime', sun_zen, constants)
        angle_prime(image, 'viewZenPrime', view_zen, constants)
        cos_phase_angle(image, 'cosPhaseAnglePrime', 'i.sunZenPrime', 'i.viewZenPrime', relative_sun_view_az, constants)
        set_image(image, 'distance', 'sqrt(pow(tan(i.sunZenPrime), 2) + pow(tan(i.viewZenPrime), 2) ' +
                  '- 2 * tan(i.sunZenPrime) * tan(i.viewZenPrime) * cos({relativeSunViewAz}))', args)
        set_image(image, 'temp', '1/cos(i.sunZenPrime) + 1/cos(i.viewZenPrime)', constants)
        set_image(image, 'cosT', to_image(image,
                                          '{h/b} * sqrt(pow(i.distance, 2) + pow(tan(i.sunZenPrime) * tan(i.viewZenPrime) '
                                          '* sin({relativeSunViewAz}), 2)) ' +
                                          '/ i.temp', args).clamp(-1, 1), constants)
        set_image(image, 't', 'acos(i.cosT)', constants)
        set_image(image, 'overlap', '(1/{pi}) * (i.t - sin(i.t) * i.cosT) * (i.temp)', constants)
        set_if(image, 'overlap', 'i.overlap > 0', 0, 'overlap', constants)
        set_image(image, band_name,
                  'i.overlap - i.temp + (1/2) * (1 + i.cosPhaseAnglePrime)'
                  ' * (1/cos(i.sunZenPrime)) * (1/cos(i.viewZenPrime))',
                  constants)

    def angle_prime(image, name, angle, constants):
        args = {'b/r': 1, 'angle': angle}
        set_image(image, 'tanAnglePrime', '{b/r} * tan({angle})', args)
        set_if(image, 'tanAnglePrime', 'i.tanAnglePrime < 0', 0, 'tanAnglePrime', constants)
        set_image(image, name, 'atan(i.tanAnglePrime)', constants)

    def cos_phase_angle(image, name, sun_zen, view_zen, relative_sun_view_az, constants):
        args = {'sunZen': sun_zen, 'viewZen': view_zen, 'relativeSunViewAz': relative_sun_view_az}
        set_image(image, name, to_image(image,
                                        'cos({sunZen}) * cos({viewZen})'
                                        ' + sin({sunZen}) * sin({viewZen}) * cos({relativeSunViewAz})',
                                        args).clamp(-1, 1), constants)

    def adjust_bands(image, coefficients_by_band, constants):
        for band_name, coefficients in coefficients_by_band.items():
            apply_c_factor(image, band_name, coefficients, constants)

    def apply_c_factor(image, band_name, coefficients, constants):
        brdf(image, 'brdf', 'kvol', 'kgeo', coefficients, constants)
        brdf(image, 'brdf0', 'kvol0', 'kgeo0', coefficients, constants)
        set_image(image, 'cFactor', 'i.brdf0 / i.brdf', coefficients)
        set_image(image, band_name, '{bandName} * i.cFactor', {**coefficients, 'bandName': 'i.' + band_name})

    def brdf(image, band_name, kvol_band, kgeo_band, coefficients, constants):
        args = {**coefficients, 'kvol': '3 * i.' + kvol_band,
                'kgeo': 'i.' + kgeo_band}  # Note the multiplication factor
        set_image(image, band_name, '{fiso} + {fvol} * {kvol} + {fgeo} * {kvol}', args)

    def find_corners(image):
        footprint = ee.Geometry(image.get('system:footprint'))
        bounds = ee.List(footprint.bounds().coordinates().get(0))
        coords = footprint.coordinates()

        xs = coords.map(lambda item: x(item))
        ys = coords.map(lambda item: y(item))

        def find_corner(target_value, values):
            diff = values.map(lambda value: ee.Number(value).subtract(target_value).abs())
            min_value = diff.reduce(ee.Reducer.min())
            idx = diff.indexOf(min_value)
            return coords.get(idx)

        lower_left = find_corner(x(bounds.get(0)), xs)
        lower_right = find_corner(y(bounds.get(1)), ys)
        upper_right = find_corner(x(bounds.get(2)), xs)
        upper_left = find_corner(y(bounds.get(3)), ys)

        return {
            'upperLeft': upper_left,
            'upperRight': upper_right,
            'lowerRight': lower_right,
            'lowerLeft': lower_left
        }

    def x(point):
        return ee.Number(ee.List(point).get(0))

    def y(point):
        return ee.Number(ee.List(point).get(1))

    def point_between(point_a, point_b):
        return ee.Geometry.LineString([point_a, point_b]).centroid().coordinates()

    def slope_between(point_a, point_b):
        return (y(point_a).subtract(y(point_b))).divide(x(point_a).subtract(x(point_b)))

    def to_line(point_a, point_b):
        return ee.Geometry.LineString([point_a, point_b])

    def set_image(image, name, to_add, args):
        to_add = to_image(image, to_add, args)
        image = image.addBands(to_add.rename(name), None, True)

    def set_if(image, name, condition, true_value, false_value, constants):
        condition = to_image(image, condition, constants)
        true_masked = to_image(image, true_value, constants).mask(to_image(image, condition, constants))
        false_masked = to_image(image, false_value, constants).mask(invert_mask(to_image(image, condition, constants)))
        value = true_masked.unmask(false_masked)
        set_image(image, name, value, constants)

    def invert_mask(mask):
        return mask.multiply(-1).add(1)

    def to_image(image, band, args):
        if isinstance(band, str):
            if '.' in band or ' ' in band or '{' in band:
                band = image.expression(format_expression(band, args), {'i': image})
            else:
                band = image.select(band)
        return ee.Image(band)

    def format_expression(s, args):
        all_args = {**constants, **args}
        result = s.format(**all_args)
        while '{' in result:
            result = result.format(**all_args)
        return result

    # main process
    input_band_names = image.bandNames()

    constants = {
        'pi': math.pi
    }

    coefficients_by_band = {
        'blue': {'fiso': 0.0774, 'fgeo': 0.0079, 'fvol': 0.0372},
        'green': {'fiso': 0.1306, 'fgeo': 0.0178, 'fvol': 0.0580},
        'red': {'fiso': 0.1690, 'fgeo': 0.0227, 'fvol': 0.0574},
        'nir': {'fiso': 0.3093, 'fgeo': 0.0330, 'fvol': 0.1535},
        'swir1': {'fiso': 0.3430, 'fgeo': 0.0453, 'fvol': 0.1154},
        'swir2': {'fiso': 0.2658, 'fgeo': 0.0387, 'fvol': 0.0639}
    }

    corners = find_corners(image)

    view_angles(image, corners)
    solar_position(image, constants)
    sun_zen_out(image, constants)
    set_image(image, 'relativeSunViewAz', 'i.sunAz - i.viewAz', constants)
    ross_thick(image, 'kvol', 'i.sunZen', 'i.viewZen', 'i.relativeSunViewAz', constants)
    ross_thick(image, 'kvol0', 'i.sunZenOut', 0, 0, constants)
    li_thin(image, 'kgeo', 'i.sunZen', 'i.viewZen', 'i.relativeSunViewAz', constants)
    li_thin(image, 'kgeo0', 'i.sunZenOut', 0, 0, constants)
    adjust_bands(image, coefficients_by_band, constants)

    return image.select(input_band_names)
