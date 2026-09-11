import unittest
from xml.etree import ElementTree as ET
from musicanote_harness.kysing_study import classify, extract


class KysingStudyTest(unittest.TestCase):
    def test_unicode_lyrics_and_ambiguous_chords(self):
        for text in ['안녕하세요', 'こんにちは', '你好', 'مرحبا', 'bonjour']:
            self.assertEqual(classify(text), 'lexical')
        self.assertEqual(classify('♫♪'), 'symbol')
        self.assertEqual(classify('hello\ufffd'), 'corrupt')
        self.assertEqual(classify('Am'), 'chord_or_word')

    def test_lyrics_and_case_do_not_change_features(self):
        xml = '<score-partwise><part id="P1"><measure number="1"><attributes><divisions>3</divisions></attributes><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><lyric><text>Hello,</text></lyric></note><note><rest/><duration>1</duration></note><note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration></note></measure></part></score-partwise>'
        frames, targets, _, _ = extract(ET.fromstring(xml))
        lower, _, _, _ = extract(ET.fromstring(xml.replace('Hello,', 'hello')))
        removed, _, _, _ = extract(ET.fromstring(xml.replace('<lyric><text>Hello,</text></lyric>', '')))
        self.assertEqual(frames, lower)
        self.assertEqual(frames, removed)
        self.assertTrue(targets[0]['punctuation'])
        self.assertEqual(frames[1]['features']['voice_gap_before'], {'numerator': 1, 'denominator': 3})
