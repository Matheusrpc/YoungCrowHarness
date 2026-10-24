"""Check the managed block and the import line install and undo without touching other text."""
from itertools import product
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from youngcrow.blocks import (  # noqa: E402
    GITIGNORE_END, GITIGNORE_START, IMPORT_LINE, MD_END, MD_START,
    ManagedBlockError, ensure_line, remove_block, remove_line, upsert_block,
)


class ManagedBlockTests(unittest.TestCase):
    def test_constants_match_the_global_constraints(self):
        self.assertEqual(MD_START, '<!-- youngcrow:start -->')
        self.assertEqual(MD_END, '<!-- youngcrow:end -->')
        self.assertEqual(GITIGNORE_START, '# youngcrow:start')
        self.assertEqual(GITIGNORE_END, '# youngcrow:end')
        self.assertEqual(IMPORT_LINE, '@.youngcrow/HARNESS.md')

    def test_upsert_is_idempotent(self):
        once = upsert_block('# Mine\n', 'rules', MD_START, MD_END)
        self.assertEqual(upsert_block(once, 'rules', MD_START, MD_END), once)
        self.assertEqual(once.count(MD_START), 1)

    def test_crlf_without_final_newline_round_trips(self):
        original = '# Mine\r\nline'
        added = ensure_line(original, IMPORT_LINE)
        self.assertIn('\r\n' + IMPORT_LINE + '\r\n', added)
        self.assertEqual(remove_line(added, IMPORT_LINE), original)

    def test_block_round_trips_exact_bytes(self):
        original = 'a\n\nb\n'
        self.assertEqual(remove_block(upsert_block(original, 'x', MD_START, MD_END), MD_START, MD_END), original)

    def test_start_without_end_refuses(self):
        with self.assertRaises(ManagedBlockError):
            upsert_block(f'{MD_START}\nold\n', 'new', MD_START, MD_END)

    def test_remove_refuses_start_without_end(self):
        with self.assertRaises(ManagedBlockError):
            remove_block(f'a\n{MD_START}\nold\n', MD_START, MD_END)

    def test_end_without_start_refuses(self):
        text = f'old\n{MD_END}\n'
        with self.assertRaises(ManagedBlockError):
            upsert_block(text, 'new', MD_START, MD_END)
        with self.assertRaises(ManagedBlockError):
            remove_block(text, MD_START, MD_END)

    def test_repeated_marker_refuses(self):
        for text in (
            f'{MD_START}\na\n{MD_END}\n{MD_START}\nb\n{MD_END}\n',
            f'{MD_START}\na\n{MD_START}\n{MD_END}\n',
            f'{MD_START}\na\n{MD_END}\n{MD_END}\n',
        ):
            with self.subTest(text=text):
                with self.assertRaises(ManagedBlockError):
                    upsert_block(text, 'new', MD_START, MD_END)
                with self.assertRaises(ManagedBlockError):
                    remove_block(text, MD_START, MD_END)

    def test_end_before_start_refuses(self):
        text = f'{MD_END}\nold\n{MD_START}\n'
        with self.assertRaises(ManagedBlockError):
            upsert_block(text, 'new', MD_START, MD_END)

    def test_refusal_names_the_marker(self):
        with self.assertRaises(ManagedBlockError) as caught:
            upsert_block(f'{MD_START}\nold\n', 'new', MD_START, MD_END)
        self.assertIn(MD_START, str(caught.exception))
        self.assertIn(MD_END, str(caught.exception))

    def test_remove_without_a_block_changes_nothing(self):
        for text in ('', 'a', 'a\r\nb\r\n'):
            with self.subTest(text=text):
                self.assertEqual(remove_block(text, MD_START, MD_END), text)

    def test_upsert_replaces_only_the_block_body(self):
        text = f'top\n\n{MD_START}\nold\n{MD_END}\nuser tail'
        updated = upsert_block(text, 'new', MD_START, MD_END)
        self.assertEqual(updated, f'top\n\n{MD_START}\nnew\n{MD_END}\nuser tail')

    def test_upsert_keeps_a_missing_final_newline_after_the_block(self):
        text = f'top\n\n{MD_START}\nold\n{MD_END}'
        self.assertEqual(upsert_block(text, 'new', MD_START, MD_END), f'top\n\n{MD_START}\nnew\n{MD_END}')

    def test_block_lines_follow_the_text_line_ending(self):
        added = upsert_block('# Mine\r\n', 'one\ntwo\n', MD_START, MD_END)
        self.assertEqual(added, f'# Mine\r\n\r\n{MD_START}\r\none\r\ntwo\r\n{MD_END}\r\n')
        self.assertEqual(added.count('\n'), added.count('\r\n'))

    def test_empty_text_gets_the_block_alone(self):
        added = upsert_block('', 'x', GITIGNORE_START, GITIGNORE_END)
        self.assertEqual(added, f'{GITIGNORE_START}\nx\n{GITIGNORE_END}\n')
        self.assertEqual(remove_block(added, GITIGNORE_START, GITIGNORE_END), '')

    def test_marker_text_inside_a_line_is_not_a_marker(self):
        text = f'Docs mention {MD_START} and {MD_END} inline.\n'
        added = upsert_block(text, 'x', MD_START, MD_END)
        self.assertTrue(added.startswith(text))
        self.assertEqual(remove_block(added, MD_START, MD_END), text)

    def test_content_added_after_the_block_survives_removal(self):
        added = upsert_block('a\n', 'x', MD_START, MD_END) + 'later\n'
        self.assertEqual(remove_block(added, MD_START, MD_END), 'a\n\nlater\n')

    def test_block_round_trips_for_every_short_text(self):
        for text in short_texts():
            with self.subTest(text=text):
                added = upsert_block(text, 'x\ny', MD_START, MD_END)
                self.assertEqual(upsert_block(added, 'x\ny', MD_START, MD_END), added)
                self.assertEqual(remove_block(added, MD_START, MD_END), text)


class ImportLineTests(unittest.TestCase):
    def test_ensure_line_is_idempotent(self):
        once = ensure_line('# Mine\n', IMPORT_LINE)
        self.assertEqual(ensure_line(once, IMPORT_LINE), once)
        self.assertEqual(once.count(IMPORT_LINE), 1)

    def test_line_the_user_already_has_is_left_alone(self):
        text = f'# Mine\n{IMPORT_LINE}\nmore\r\n'
        self.assertEqual(ensure_line(text, IMPORT_LINE), text)

    def test_empty_text_gets_the_line_alone(self):
        added = ensure_line('', IMPORT_LINE)
        self.assertEqual(added, IMPORT_LINE + '\n')
        self.assertEqual(remove_line(added, IMPORT_LINE), '')

    def test_remove_without_the_line_changes_nothing(self):
        for text in ('', 'a', 'a\r\nb\r\n'):
            with self.subTest(text=text):
                self.assertEqual(remove_line(text, IMPORT_LINE), text)

    def test_line_after_a_final_newline_is_set_apart_by_a_blank_line(self):
        self.assertEqual(ensure_line('# Mine\n', IMPORT_LINE), f'# Mine\n\n{IMPORT_LINE}\n')

    def test_content_added_after_the_line_survives_removal(self):
        added = ensure_line('a\n', IMPORT_LINE) + 'later\n'
        self.assertEqual(remove_line(added, IMPORT_LINE), 'a\n\nlater\n')

    def test_line_moved_to_the_middle_does_not_join_its_neighbours(self):
        self.assertEqual(remove_line(f'# Title\n{IMPORT_LINE}\ntext\n', IMPORT_LINE), '# Title\ntext\n')

    def test_repeated_line_refuses(self):
        with self.assertRaises(ManagedBlockError):
            remove_line(f'{IMPORT_LINE}\na\n{IMPORT_LINE}\n', IMPORT_LINE)

    def test_line_round_trips_for_every_short_text(self):
        for text in short_texts():
            with self.subTest(text=text):
                added = ensure_line(text, IMPORT_LINE)
                self.assertEqual(ensure_line(added, IMPORT_LINE), added)
                self.assertEqual(remove_line(added, IMPORT_LINE), text)


def short_texts():
    """Every text up to six characters from letters, both newline characters and a space."""
    for size in range(7):
        for chars in product('a\n\r ', repeat=size):
            yield ''.join(chars)


if __name__ == '__main__':
    unittest.main()
