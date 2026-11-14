import io
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from sportsmatrix.configuration import ConfigStore
from sportsmatrix.preview import render_fixture
from sportsmatrix.registry import supported, LEAGUES
from sportsmatrix.selection import choose, duration

class CoreTests(unittest.TestCase):
    def test_config(self):
        with tempfile.TemporaryDirectory() as directory:
            store=ConfigStore(Path(directory)/'settings.json')
            self.assertEqual(store.update({'brightness':60})['brightness'],60)
            self.assertEqual(store.read()['brightness'],60)
            with self.assertRaises(ValueError):store.update({'brightness':101})
            with self.assertRaises(ValueError):store.update({'league':'invalid'})
            with self.assertRaises(ValueError):store.update({'sport_preferences':{'nhl':{'mode':'invalid'}}})
            self.assertEqual(store.read()['brightness'],60)
    def test_registry(self):
        self.assertIn('nhl',supported())
        self.assertIn('wnba',supported())
        self.assertNotIn('pll',supported())
        self.assertNotIn('pwhl',supported())
        self.assertIn('wnba',LEAGUES)
    def test_previews(self):
        for league in supported():
            for profile,expected in [('compact_64x32',(64,32)),('enhanced_128x64',(128,64))]:
                png=render_fixture(league,profile)
                self.assertEqual(Image.open(io.BytesIO(png)).size,expected)
    def test_favorites(self):
        def event(team,state):
            return {'competitions':[{'competitors':[{'team':{'abbreviation':team}}]}], 'status':{'type':{'state':state}},'date':'2026-11-07T10:00:00Z'}
        sharks=event('SJ','pre');other=event('BUF','in')
        self.assertEqual(choose([other,sharks],{'mode':'only','favorite_team':'SJ'}),[sharks])
        self.assertEqual(duration(sharks,{'mode':'prefer','favorite_team':'SJ','favorite_seconds':90}),90)

if __name__=='__main__':unittest.main()
