"""poll-tick.sh: the scheduler alone owns the poll stamps, and it records a
run's start, so the next poll never skips mail that arrived mid-run."""

import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest

DASH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@unittest.skipUnless(shutil.which("jq") and shutil.which("bash"), "needs jq and bash")
class TestTickStamps(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp()
        self.dash = os.path.join(self.t, "dash")
        os.makedirs(os.path.join(self.dash, "workspace"))
        bindir = os.path.join(self.t, "bin")
        os.makedirs(bindir)
        self.args = os.path.join(self.t, "args.txt")
        claude = os.path.join(bindir, "claude")
        # a poll that tries to plant a far-future stamp, then succeeds
        with open(claude, "w") as f:
            f.write('#!/bin/sh\nprintf "%%s\\n" "$@" > %s\n'
                    'echo \'{"general": 9999999999}\' > %s/poll-last-completed.json\nexit 0\n'
                    % (self.args, self.dash))
        os.chmod(claude, 0o755)
        with open(os.path.join(self.dash, "poll-config.json"), "w") as f:
            json.dump({"timezone": "UTC", "general": {"interval_min": 1, "start": "00:00", "end": "23:59"}}, f)
        with open(os.path.join(self.dash, "config.json"), "w") as f:
            json.dump({"poll_tools": "Read,Edit,Agent"}, f)
        self.env = dict(os.environ, CLAUDE_BIN=claude, COS_RUN_DIR=os.path.join(self.t, "run"), HOME=self.t)

    def tearDown(self):
        shutil.rmtree(self.t, ignore_errors=True)

    def test_the_stamp_is_the_runs_start_and_the_poll_cannot_edit_it(self):
        before = int(time.time())
        subprocess.run(["bash", os.path.join(DASH, "poll-tick.sh"), self.dash], env=self.env,
                       capture_output=True, text=True, timeout=120)
        after = int(time.time())
        with open(os.path.join(self.dash, "poll-last-completed.json")) as f:
            stamp = json.load(f)["general"]
        self.assertTrue(before <= stamp <= after, (before, stamp, after))   # overwrote the plant
        with open(self.args) as f:
            args = f.read().split("\n")
        deny = args[args.index("--disallowedTools") + 1]
        self.assertIn("poll-last-completed.json", deny)
        self.assertIn("poll-last-run.json", deny)


if __name__ == "__main__":
    unittest.main()
