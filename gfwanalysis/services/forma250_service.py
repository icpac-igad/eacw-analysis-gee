"""HANSEN SERVICE"""

import logging

import ee
from gfwanalysis.errors import FormaError
from gfwanalysis.config import SETTINGS
from gfwanalysis.utils.generic import get_region, squaremeters_to_ha


class Forma250Service(object):

    @staticmethod
    def forma250_all(geojson, start_date, end_date):
        """Forma info goes here
        """
        try:
            max_pixels = 9999999999
            scale = 231.65635826395828
            region = get_region(geojson)
            asset_id = SETTINGS.get('gee').get('assets').get('forma250GFW')
            logging.info(asset_id)
            ic=ee.ImageCollection(asset_id
                                  ).sort('system:time_start', False)
            latest = ee.Image(ic.first())
            alert_date_band = latest.select('alert_date')
            milisec_date_start = ee.Date(start_date).millis()
            milisec_date_end = ee.Date(end_date).millis()
            date_mask = alert_date_band.gte(milisec_date_start).And(
                            alert_date_band.lte(milisec_date_end))
            reduce_sum_args = {'reducer': ee.Reducer.sum().unweighted(),
                               'geometry': region,
                               'bestEffort': True,
                               'scale': scale,
                               'crs': "EPSG:4326",
                               'maxPixels': max_pixels}
            reduce_count_args = {'reducer': ee.Reducer.count().unweighted(),
                                 'geometry': region,
                                 'bestEffort': True,
                                 'scale': scale,
                                 'crs': "EPSG:4326",
                                 'maxPixels': max_pixels}
            area_m2 = latest.select('alert_delta').mask(date_mask).divide(100).multiply(
                        ee.Image.pixelArea()).reduceRegion(**reduce_sum_args).getInfo()
            # Below is where the E.E. requests are made
            alert_area_ha = squaremeters_to_ha(area_m2['alert_delta'])
            tmp_counts = latest.select('alert_delta').mask(
                            date_mask).reduceRegion(**reduce_count_args).getInfo()
            alert_counts = tmp_counts['alert_delta']
            logging.info(f"Number of alerts over time period = {alert_counts}")
            logging.info(f"Estimated area loss over time period = {alert_area_ha} ha")
            return {'area_ha':alert_area_ha, 'alert_counts':alert_counts}
        except Exception as error:
            logging.error(str(error))
            raise FormaError(message='Error in Forma250 Analysis')