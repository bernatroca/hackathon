import unittest

from suma import suma


class TestSuma(unittest.TestCase):
    def test_suma_positius(self):
        self.assertEqual(suma(2, 3), 5)

    def test_suma_zero(self):
        self.assertEqual(suma(-1, 1), 0)


if __name__ == "__main__":
    unittest.main()
