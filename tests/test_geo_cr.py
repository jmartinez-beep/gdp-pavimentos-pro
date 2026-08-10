from geo_cr import crtm05_to_wgs84, is_plausible_costa_rica_wgs84, wgs84_to_crtm05


def test_roundtrip_wgs84_crtm05():
    lon0, lat0 = -84.0907, 9.9281
    easting, northing = wgs84_to_crtm05(lon0, lat0)
    lon1, lat1 = crtm05_to_wgs84(easting, northing)
    assert abs(lon1 - lon0) < 1e-8
    assert abs(lat1 - lat0) < 1e-8


def test_crtm05_values_are_metric_and_plausible():
    easting, northing = wgs84_to_crtm05(-84.0907, 9.9281)
    assert 300000 < easting < 700000
    assert 800000 < northing < 1300000


def test_costa_rica_plausibility_guard():
    assert is_plausible_costa_rica_wgs84(-84.1, 9.93)
    assert not is_plausible_costa_rica_wgs84(-70.0, 9.93)
