"""A failed pilot must report its location without copying private error details."""
import contextlib
import io
import json
import sys
import unittest
from unittest.mock import patch

import smoke_public_pilot


class PilotDiagnosticsTests(unittest.TestCase):
    def test_failure_reports_location_and_keeps_private_details_out(self):
        output = io.StringIO()
        with patch.object(sys, 'argv', ['pilot', '--root', 'unused']), \
                patch.object(smoke_public_pilot, 'pilot', side_effect=ValueError('PRIVATE_VALUE')), \
                contextlib.redirect_stderr(output):
            code = smoke_public_pilot.main()
        self.assertEqual(code, 1)
        result = json.loads(output.getvalue())
        self.assertEqual(result['code'], 'public_pilot_smoke_failed')
        self.assertEqual(result['error_type'], 'ValueError')
        self.assertTrue(result['locations'])
        self.assertEqual(result['locations'][-1]['file'], 'smoke_public_pilot.py')
        self.assertNotIn('PRIVATE_VALUE', output.getvalue())
        self.assertNotIn(str(smoke_public_pilot.ROOT), output.getvalue())


if __name__ == '__main__':
    unittest.main()
