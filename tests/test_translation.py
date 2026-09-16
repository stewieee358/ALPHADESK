import unittest
from types import SimpleNamespace
from unittest.mock import patch

from mini_bloomberg.core.translation import _translate


class TranslationTests(unittest.TestCase):
    def setUp(self):
        _translate.cache_clear()

    @patch('mini_bloomberg.core.translation._get_client')
    def test_success_cached_by_source_and_model(self, client):
        create = client.return_value.messages.create
        create.return_value = SimpleNamespace(
            content=[SimpleNamespace(type='text', text='English introduction')],
            stop_reason='end_turn',
        )
        self.assertEqual(_translate('原文', 'model'), 'English introduction')
        _translate('原文', 'model')
        self.assertEqual(create.call_count, 1)
        _translate('更新原文', 'model')
        self.assertEqual(create.call_count, 2)

    @patch('mini_bloomberg.core.translation._get_client')
    def test_incomplete_translation_is_not_cached(self, client):
        client.return_value.messages.create.return_value = SimpleNamespace(
            content=[SimpleNamespace(type='text', text='Partial')],
            stop_reason='max_tokens',
        )
        for _ in range(2):
            with self.assertRaises(ValueError):
                _translate('原文', 'model')
        self.assertEqual(client.return_value.messages.create.call_count, 2)
