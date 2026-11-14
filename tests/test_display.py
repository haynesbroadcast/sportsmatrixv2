import time
import unittest
from sportsmatrix.display import frame_to_show

class DisplayTests(unittest.TestCase):
    def setUp(self):
        self.now = time.time()
        self.settings = {'league':'nhl','profile':'enhanced_128x64','brightness':50,'power':'on'}
        self.state = {'league':'nhl','profile':'enhanced_128x64','updated_at':self.now}
    def test_valid(self):
        self.assertEqual(frame_to_show(self.settings,self.state,self.now),('enhanced_128x64',50))
    def test_off(self):
        self.settings['power']='off'
        self.assertIsNone(frame_to_show(self.settings,self.state,self.now))
    def test_stale(self):
        self.state['updated_at'] -= 121
        self.assertIsNone(frame_to_show(self.settings,self.state,self.now))
    def test_mismatch(self):
        self.state['league']='golf'
        self.assertIsNone(frame_to_show(self.settings,self.state,self.now))
