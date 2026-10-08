"""Run unittest with failure identifiers visible in GitHub Actions annotations."""
import os
import re
import unittest


class AnnotationRunner(unittest.TextTestRunner):
    def run(self, test):
        result = super().run(test)
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            failed = [case for case, _ in result.failures + result.errors]
            identifiers = set()
            for case in failed + result.unexpectedSuccesses:
                # Subtest IDs include parameter values; retain only the parent ID.
                if isinstance(case, unittest.case._SubTest):
                    case = case.test_case
                identifier = case.id()
                # Standard test IDs and class/module setup/teardown error holders.
                if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]*(?: \([A-Za-z_][A-Za-z0-9_.]*\))?', identifier):
                    identifier = 'test_identifier_unavailable'
                if identifier not in identifiers:
                    print(f'::error::{identifier}', flush=True)
                    identifiers.add(identifier)
        return result


if __name__ == '__main__':
    unittest.main(module=None, testRunner=AnnotationRunner)
