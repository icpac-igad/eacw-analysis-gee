import ee
import logging
 
def divide_geometry(feature):
    """Divide feature geometry
    Split a features polygon geometry in 4 using its' center point
    @param {ee.Feature} A feature with a polygon geometry to split.
    @return {ee.FeatureCollection} Collection with 4 features per input feature.
    @example var aoi = Map.getBounds(); var fc = divideGeometry(aoi);
    """
    # Get coordinates of polygons bounds
    g = feature.geometry()
    l2 = g.bounds(1).coordinates().flatten()
    c2 = g.centroid(1).coordinates().flatten()
    # Create 4 cells dividing bounds at centroid
    t0 = ee.Feature(ee.Geometry.Polygon(
    [l2.get(0), l2.get(1),
    c2.get(0), l2.get(1),
    c2.get(0), c2.get(1),
    l2.get(0), c2.get(1),
    l2.get(0), l2.get(1),
    ]), {"name": "t0"})
    t1 = ee.Feature(ee.Geometry.Polygon(
    [c2.get(0), l2.get(3),
    l2.get(2), l2.get(3),
    l2.get(2), c2.get(1),
    c2.get(0), c2.get(1),
    c2.get(0), l2.get(3),
    ]), {"name": "t1"})
    t2 = ee.Feature(ee.Geometry.Polygon(
    [c2.get(0), c2.get(1),
    l2.get(4), c2.get(1),
    l2.get(4), l2.get(5),
    c2.get(0), l2.get(5),
    c2.get(0), c2.get(1),
    ]), {"name": "t2"})
    t3 = ee.Feature(ee.Geometry.Polygon(
    [l2.get(0), c2.get(1),
    c2.get(0), c2.get(1),
    c2.get(0), l2.get(7),
    l2.get(6), l2.get(7),
    l2.get(0), c2.get(1),
    ]), {"name": "t3"})
    # Make a featureCollection
    fc = ee.FeatureCollection([t0, t1, t2, t3,])
    # Map intersection with feature and return cell name
    def intersect(f):
        return ee.Feature(feature.geometry().intersection(f.geometry(), 1), {"name": f.get("name")})
    
    return fc.map(intersect)

def get_region(geom, divideGeom=False, nDivide=16):
    """Take a valid geojson object, iterate over all features in that object.
        Build up a list of EE Polygons, and finally return an EE Feature
        collection. New as of 19th Sep 2017 (needed to fix a bug where the old
        function ignored multipolys)
    """
    logging.info('Getting region')
    polygons = []
    for feature in geom.get('features'):
        shape_type = feature.get('geometry').get('type')
        coordinates = feature.get('geometry').get('coordinates')
        if shape_type == 'MultiPolygon':
            polygons.append(ee.Geometry.MultiPolygon(coordinates))
        elif shape_type == 'Polygon':
            polygons.append(ee.Geometry.Polygon(coordinates))
        else:
            pass
    fc = ee.FeatureCollection(polygons)
    if divideGeom:
        logging.info('Dividing geometries')
        tmp = fc.map(divide_geometry).flatten()
        tmp2 = tmp.map(divide_geometry).flatten()
        tmp3 = tmp2.map(divide_geometry).flatten()
        if nDivide == 4:
            fc = tmp
        if nDivide == 16:
            fc = tmp2
        if nDivide == 64:
            fc = tm3
        logging.info(f'Dividing geometries by: {fc.toList(1000).length().getInfo()}')    
    return fc

def sum_extent(im, fc, useMap=False, useBestEffort=False):
    """Apply sum area reducer to each feature in a featureCollection
    and return grand total"""
    if type(fc) != ee.FeatureCollection:
        raise HansenError(message='FeatureCollection required for sum_extent')
    # Convert binary image to area (m2)
    im = ee.Image(im).multiply(ee.Image.pixelArea())
    out = im.reduceRegions(fc, ee.Reducer.sum(), 30)
    logging.info('Applying reduceRegions')
    def map_reduceRegion(f):
            out = im.reduceRegion(**{
                'reducer': ee.Reducer.sum(),
                'geometry': f.geometry(),
                'bestEffort': useBestEffort,
                'maxPixels': 1e9,
                'scale': 30,
                'tileScale': 16
                }).values().get(0)
            return ee.Feature(None, {"sum": out})
    if useMap:
            output = fc.map(map_reduceRegion).aggregate_sum("sum")
    else: 
            output = out.aggregate_sum("sum")
    return output    

def squaremeters_to_ha(value):
    """Converts square meters to hectares, and gives val to 2 decimal places"""
    tmp = value/10000.
    return float('{0:4.2f}'.format(tmp))

def ee_squaremeters_to_ha(value):
    """Converts square meters to hectares, and gives val to 2 decimal places"""
    tmp = ee.Number(value).divide(10000)
    return ee.Number(tmp).format('%.2f')

def get_thresh_image(thresh, asset_id):
    """Renames image bands using supplied threshold and returns image."""
    image = ee.Image(asset_id)

    # Select out the gain band if it exists
    if 'gain' in asset_id:
        before = image.select('.*_' + thresh, 'gain').bandNames()
    else:
        before = image.select('.*_' + thresh).bandNames()

    after = before.map(
        lambda x: ee.String(x).replace('_.*', ''))

    image = image.select(before, after)
    return image


def dict_unit_transform(data, num):
    dasy = {}
    for key in data:
        dasy[key] = data[key]*num

    return dasy


def indicator_selector(row, indicator, begin, end):
    """Return Tons of biomass loss."""
    dasy = {}
    if indicator == 4:
        return row[2]['value']

    for i in range(len(row)):
        if row[i]['indicator_id'] == indicator and row[i]['year'] >= int(begin) and row[i]['year'] <= int(end):
            dasy[str(row[i]['year'])] = row[i]['value']

    return dasy

def dates_selector(data, begin, end):
    """Return Tons of biomass loss."""
    dasy = {}
    for key in data:
        if int(key) >= int(begin) and int(key) <= int(end):
            dasy[key] = data[key]

    return dasy


def sum_range(data, begin, end):
    return sum([data[key] for key in data if (int(key) >= int(begin)) and (int(key) < int(end))])


def admin_0_simplify(iso):
    """Check admin areas and return a relevant simplification or None"""
    #logging.info(f'[admin_0_simplify]: passed {iso}')
    admin_0_dic = {'ATA': 0.3,
                    'RUS': 0.3,
                    'CAN': 0.3,
                    'GRL': 0.3,
                    'USA': 0.3,
                    'CHN': 0.3,
                    'AUS': 0.1,
                    'BRA': 0.1,
                    'KAZ': 0.1,
                    'ARG': 0.1,
                    'IND': 0.1,
                    'MNG': 0.1,
                    'DZA': 0.1,
                    'MEX': 0.1,
                    'COD': 0.1,
                    'SAU': 0.1,
                    'IRN': 0.1,
                    'SWE': 0.1,
                    'LBY': 0.1,
                    'SDN': 0.1,
                    'IDN': 0.1,
                    'FIN': 0.01,
                    'NOR': 0.01,
                    'SJM': 0.01,
                    'ZAF': 0.01,
                    'UKR': 0.01,
                    'MLI': 0.01,
                    'TCD': 0.01,
                    'PER': 0.01,
                    'AGO': 0.01,
                    'NER': 0.01,
                    'CHL': 0.01,
                    'TUR': 0.01,
                    'EGY': 0.01,
                    'MRT': 0.01,
                    'BOL': 0.01,
                    'PAK': 0.01,
                    'ETH': 0.01,
                    'FRA': 0.01,
                    'COL': 0.01}
    simplification = admin_0_dic.get(iso, None)
    return simplification


def admin_1_simplify(iso, admin1):
    #logging.info(f'[admin_1_simplify]: passed {iso}/{admin1}')
    admin_1_dic = {'RUS': {60: 0.3,
                            35: 0.3,
                            12: 0.1,
                            80: 0.1,
                            18: 0.1,
                            28: 0.1,
                            30: 0.1,
                            4: 0.1,
                            40: 0.1,
                            32: 0.1,
                            24: 0.1,
                            83: 0.1,
                            3: 0.01,
                            69: 0.01,
                            9: 0.01,
                            46: 0.01,
                            26: 0.01,
                            45: 0.01,
                            66: 0.01,
                            55: 0.01,
                            50: 0.01},
                            'CAN': {8: 0.3,
                            6: 0.3,
                            11: 0.3,
                            9: 0.1,
                            2: 0.1,
                            1: 0.1,
                            3: 0.1,
                            12: 0.1,
                            13: 0.1,
                            5: 0.1},
                            'GRL': {2: 0.3, 3: 0.3, 5: 0.1},
                            'USA': {2: 0.3,
                            44: 0.1,
                            27: 0.01,
                            5: 0.01,
                            32: 0.01,
                            29: 0.01,
                            3: 0.01,
                            23: 0.01,
                            38: 0.01,
                            6: 0.01,
                            51: 0.01,
                            24: 0.01,
                            13: 0.01},
                            'AUS': {11: 0.3, 7: 0.3, 6: 0.1, 8: 0.1, 5: 0.1},
                            'CHN': {28: 0.3,
                            19: 0.1,
                            29: 0.1,
                            21: 0.1,
                            11: 0.1,
                            26: 0.01,
                            5: 0.01,
                            30: 0.01},
                            'BRA': {4: 0.1,
                            14: 0.1,
                            12: 0.1,
                            13: 0.01,
                            5: 0.01,
                            11: 0.01,
                            9: 0.01,
                            10: 0.01,
                            21: 0.01},
                            'NER': {1: 0.1},
                            'DZA': {41: 0.01, 1: 0.01, 22: 0.01},
                            'KAZ': {9: 0.01, 3: 0.01, 5: 0.01, 11: 0.01, 10: 0.01, 1: 0.01},
                            'SAU': {8: 0.01, 7: 0.01},
                            'MLI': {9: 0.01},
                            'LBY': {6: 0.01},
                            'EGY': {14: 0.01},
                            'ZAF': {8: 0.01},
                            'PAK': {2: 0.01},
                            'SDN': {10: 0.01, 8: 0.01},
                            'IND': {29: 0.01, 19: 0.01, 20: 0.01},
                            'ARG': {1: 0.01, 20: 0.01, 4: 0.01},
                            'PER': {17: 0.01},
                            'BOL': {8: 0.01},
                            'ETH': {8: 0.01, 9: 0.01},
                            'IDN': {23: 0.01},
                            'SJM': {2: 0.01}}
    try:
        admin1 = int(admin1)
    except:
        admin1 = -999
    simplification = None
    if admin_1_dic.get(iso):
        simplification = admin_1_dic.get(iso, None).get(admin1, None)
        logging.info(f'[admin_1_simplify]: {simplification}')
    return simplification