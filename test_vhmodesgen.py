#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
#
# Tests for vhmodesgen.py and modes_frame.py.
#   python3 -m unittest -v test_vhmodesgen
# The pyModeS cross-checks run only if pyModeS (3.x) is installed.

import unittest

import modes_frame as mf
import vhmodesgen as vg

try:
    import pyModeS
    HAVE_PYMODES = hasattr(pyModeS, "decode")
except ImportError:
    HAVE_PYMODES = False

# Known registration / address pairs. AWM matches a public lookup (sprinkle.com).
KNOWN = {"VH-TKV": "7c61ad", "VH-BMX": "7c06d7", "VH-AWM": "7c0324",
         "VH-AAA": "7c0000", "VH-ZZZ": "7c822d", "VH-999": "7cb63f"}


class TestConversion(unittest.TestCase):
    def test_known_pairs(self):
        for reg, addr in KNOWN.items():
            self.assertEqual(vg.convert_to_mode_s(reg), addr)
            self.assertEqual(vg.convert_to_vh(addr), reg)

    def test_mark_forms(self):
        for form in ("VH-TKV", "vh-tkv", "VHTKV", "TKV", "tkv"):
            self.assertEqual(vg.convert_to_mode_s(form), "7c61ad")

    def test_invalid_marks(self):
        for bad in ("VH-T_V", "VH-TK", "VH-TKVV", "", "ZK-TKV"):
            self.assertEqual(vg.convert_to_mode_s(bad), "")

    def test_vh_address_range(self):
        self.assertTrue(vg.is_vh_address("7c0000"))
        self.assertTrue(vg.is_vh_address("0x7CB63F"))
        for not_vh in ("7cb640", "7cf7ca", "7d0000", "4840d6", "zz"):
            self.assertFalse(vg.is_vh_address(not_vh))

    def test_main_exit_codes(self):
        self.assertEqual(vg.main(["--vh", "VH-TKV"]), 0)
        self.assertEqual(vg.main(["--vh", "VH-T_V"]), 1)
        self.assertEqual(vg.main(["-s", "7d0000"]), 1)


class TestFrames(unittest.TestCase):
    def test_crc_known_frame(self):
        # KLM1023, from The 1090 Megahertz Riddle
        self.assertEqual(mf.recovered_address("8D4840D6202CC371C32CE0576098"), 0)

    def test_examples_match_registration(self):
        frames = mf.example_frames("VH-TKV")
        for name in ("ident", "ident_vh", "df4", "df5", "df11", "pos_even"):
            self.assertIn("MATCHES", mf.check(frames[name], "VH-TKV"), name)
            self.assertIn("does not match", mf.check(frames[name], "VH-BMX"), name)

    def test_ap_recovery(self):
        frames = mf.example_frames("VH-TKV")
        self.assertEqual(mf.recovered_address(frames["df5"]), 0x7C61AD)
        # one changed hex digit gives a different, plausible-looking address
        corrupted = frames["df5"][:-1] + "0"
        self.assertNotEqual(mf.recovered_address(corrupted), 0x7C61AD)

    def test_icao_to_vh(self):
        self.assertEqual(mf.icao_to_vh(0x7C61AD), "VH-TKV")
        self.assertIsNone(mf.icao_to_vh(0x7CF7CA))
        self.assertIsNone(mf.icao_to_vh(0x4840D6))


@unittest.skipUnless(HAVE_PYMODES, "pyModeS 3.x not installed")
class TestAgainstPyModeS(unittest.TestCase):
    def test_round_trip(self):
        lat, lon = -34.0403, 150.6872
        f = mf.example_frames("VH-TKV", lat, lon, 1500)
        d = lambda k, **kw: dict(pyModeS.decode(f[k], **kw))

        ident = d("ident")
        self.assertEqual((ident["icao"], ident["callsign"], ident["category"]), ("7C61AD", "TKV", 1))
        self.assertTrue(ident["crc_valid"])
        self.assertEqual(d("ident_vh")["callsign"], "VHTKV")

        for k in ("pos_even", "pos_odd"):
            p = d(k, reference=(lat, lon))
            self.assertEqual(p["altitude"], 1500)
            self.assertAlmostEqual(p["latitude"], lat, places=3)
            self.assertAlmostEqual(p["longitude"], lon, places=3)
        self.assertEqual(d("pos_nic0", reference=(lat, lon))["typecode"], 18)

        v = d("velocity")
        self.assertEqual((v["groundspeed"], v["track"], v["vertical_rate"], v["nac_v"]), (110, 225.0, -512, 1))

        s = d("opstat_tabs_example")
        self.assertEqual((s["version"], s["nac_p"], s["sil"]), (2, 9, 1))
        s = d("opstat_no_integrity")
        self.assertEqual((s["nac_p"], s["sil"]), (0, 0))

        self.assertEqual(d("df4")["altitude"], 1500)
        self.assertEqual(d("df5")["squawk"], "1200")
        for k in ("df4", "df5", "df11"):
            self.assertEqual(d(k)["icao"], "7C61AD")


if __name__ == "__main__":
    unittest.main()
