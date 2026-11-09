import io
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from sportsmatrix.server import create_app
from sportsmatrix.selection import choose, duration

class ControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "settings.json"
        self.app = create_app(self.path)
        self.client = self.app.test_client()
    def tearDown(self): self.temp.cleanup()
    def test_registry(self):
        response = self.client.get('/api/v1/leagues')
        self.assertEqual(response.status_code, 200)
        by_key = {x['key']: x for x in response.json['leagues']}
        self.assertTrue(by_key['nhl']['enabled'])
        self.assertFalse(by_key['wnba']['enabled'])
    def test_auth(self):
        self.assertEqual(self.client.put('/api/v1/settings', json={'league':'nhl'}).status_code, 401)
    def test_health(self): self.assertTrue(self.client.get('/healthz').json['ok'])
    def test_validation(self):
        import os
        os.environ['SPORTSMATRIX_API_TOKEN']='test-secret'
        app=create_app(self.path)
        client=app.test_client()
        headers={'Authorization':'Bearer test-secret'}
        self.assertEqual(client.put('/api/v1/settings',json={'league':'wnba'},headers=headers).status_code,400)
        self.assertEqual(client.put('/api/v1/settings',json={'brightness':0},headers=headers).status_code,400)
        self.assertEqual(client.put('/api/v1/settings',json={'league':'nhl','brightness':70},headers=headers).status_code,200)
        self.assertEqual(client.get('/api/v1/status').json['state']['brightness'],70)
        os.environ.pop('SPORTSMATRIX_API_TOKEN',None)
    def test_previews(self):
        for league in ('nhl','nfl','cfb','golf'):
            for profile,expected in [('compact_64x32',(64,32)),('enhanced_128x64',(128,64))]:
                response=self.client.get(f'/api/v1/preview.png?league={league}&profile={profile}')
                self.assertEqual(response.status_code,200,league)
                self.assertEqual(Image.open(io.BytesIO(response.data)).size,expected)
    def test_favorites(self):
        game=lambda abbr,state:{'competitions':[{'competitors':[{'team':{'abbreviation':abbr}}]}],'status':{'type':{'state':state}},'date':'2026-11-07T10:00:00Z'}
        sharks=game('SJ','pre'); others=game('BUF','in')
        self.assertEqual(choose([others,sharks],{'mode':'only','favorite_team':'SJ'}),[sharks])
        self.assertEqual(duration(sharks,{'mode':'prefer','favorite_team':'SJ','favorite_seconds':90}),90)
if __name__=='__main__': unittest.main()
