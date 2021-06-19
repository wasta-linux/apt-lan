import psutil
import subprocess
import tempfile
import unittest

from pathlib import Path

from apt_lan import client

# Assert*() methods here:
# https://docs.python.org/3/library/unittest.html?highlight=pytest#unittest.TestCase

class Basic(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @unittest.skip("incomplete test")
    def test_verify_rsync_folder(self):
        # TODO: Need to create a temporary rsync share for this test.
        #   But, creating a temporary rsync share seems a little fiddly.
        r_temp = Path('/tmp/rsync_temp_dir')
        r_temp.mkdir()
        r_temp_config = Path('/tmp/rsync_temp_config')

        name = 'rsync-temp'
        port = 9999
        contents = f"port = {port}\n\n[{name}]\npath = {r_temp}\n"
        r_temp_config.write_text(contents)

        cmd = ['rsync', '--daemon', '--no-detach', f'--config={r_temp_config}']
        r_svc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        uri = f'rsync://localhost/{name}'
        cmd = ['rsync', uri, '--list-only']
        r_ck = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(r_ck.stdout)
        print(r_ck.stderr)

        self.assertTrue(client.verify_rsync_folder(uri))

        r_svc.kill()
        r_temp_config.unlink()
        r_temp.unlink()
