import unittest

from musicanote_harness.harmony_label_taxonomy import classify_harmony_label


class HarmonyLabelTaxonomyTest(unittest.TestCase):
    def test_dominant_seventh_inversion(self):
        value = classify_harmony_label("V65")
        self.assertEqual(value["family"], "dominant_leading_tone")
        self.assertEqual(value["base_degree"], "V")
        self.assertEqual(value["inversion_figure"], "65")

    def test_applied_leading_tone_and_special_augmented_sixth(self):
        applied = classify_harmony_label("#viio65/ii")
        self.assertEqual(applied["family"], "applied_dominant_leading_tone")
        self.assertEqual(applied["applied_to"], "ii")
        self.assertEqual(applied["alteration_prefix"], "#")
        special = classify_harmony_label("Ger6")
        self.assertEqual(special["family"], "predominant_chromatic_augmented_sixth")
        self.assertEqual(special["special_type"], "Ger6")
        special_component = classify_harmony_label("Ger6/vi", {"special": "Ger"})
        self.assertEqual(special_component["family"], "predominant_chromatic_augmented_sixth")

    def test_no_chord_continuation_and_compound_path_stay_explicit(self):
        self.assertEqual(classify_harmony_label("@none")["parse_status"], "no_chord")
        self.assertTrue(classify_harmony_label("I\\")["continuation"])
        compound = classify_harmony_label("i.i")
        self.assertEqual(compound["parse_status"], "partial")
        self.assertEqual(compound["compound_path"], ["i", "i"])


if __name__ == "__main__":
    unittest.main()
