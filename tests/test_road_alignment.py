import json
import unittest

from road_alignment import RoadAlignmentError, road_route


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class RoadAlignmentTests(unittest.TestCase):
    def test_returns_geojson_geometry_and_metrics(self):
        captured = {}

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            return _Response({
                "code": "Ok",
                "routes": [{
                    "distance": 321.4,
                    "duration": 45.0,
                    "geometry": {"coordinates": [[-84.1, 9.9], [-84.09, 9.91]]},
                }],
            })

        result = road_route([(-84.1, 9.9), (-84.09, 9.91)], opener=opener)

        self.assertEqual(result.coordinates, ((-84.1, 9.9), (-84.09, 9.91)))
        self.assertAlmostEqual(result.distance_m, 321.4)
        self.assertIn("-84.1000000,9.9000000;-84.0900000,9.9100000", captured["url"])
        self.assertIn("geometries=geojson", captured["url"])

    def test_rejects_missing_route(self):
        def opener(_request, timeout):
            return _Response({"code": "NoRoute", "message": "Impossible route"})

        with self.assertRaisesRegex(RoadAlignmentError, "Impossible route"):
            road_route([(-84.1, 9.9), (-84.09, 9.91)], opener=opener)

    def test_requires_two_points(self):
        with self.assertRaisesRegex(ValueError, "entre 2 y 25"):
            road_route([(-84.1, 9.9)])


if __name__ == "__main__":
    unittest.main()
