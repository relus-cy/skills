from pathlib import Path
import json
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]

class ReleaseSmokeTests(unittest.TestCase):
    def test_full_command_workflow_in_disposable_repository(self):
        script=ROOT/'scripts/smoke_reviewed_workflow.py'
        self.assertTrue(script.is_file(),'missing executable workflow acceptance test')
        result=subprocess.run([sys.executable,str(script)],capture_output=True,text=True,timeout=45)
        self.assertEqual(result.returncode,0,result.stderr+result.stdout)
        report=json.loads(result.stdout)
        self.assertTrue(report['ok'])
        self.assertEqual(report['review_evidence'],'synthetic-fixture')
        self.assertEqual(report['apply_status'],'applied')
        self.assertEqual(report['repeat_status'],'already-applied')
        self.assertEqual(report['completion_status'],'contract-accepted')
        self.assertFalse(report['independent_model_evaluated'])
