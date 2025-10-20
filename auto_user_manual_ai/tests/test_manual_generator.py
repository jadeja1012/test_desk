from odoo.tests.common import TransactionCase
from unittest.mock import patch

class TestManualGenerator(TransactionCase):

    def setUp(self):
        super().setUp()
        self.manual_model = self.env['manual.generator']
        # Use an existing module (avoids constraint issue)
        self.test_module = self.env['ir.module.module'].search([('name', '=', 'base')], limit=1)

    def test_create_manual_record(self):
        """Ensure a manual record can be created"""
        record = self.manual_model.create({
            'name': 'Test Manual',
            'module_ids': [(6, 0, [self.test_module.id])]
        })
        print("111111111111111111111",record)
        self.assertTrue(record.id)
        self.assertEqual(record.name, 'Test Manual')

    @patch('odoo.addons.auto_user_manual_ai.models.manual_generator.ManualGenerator.call_openrouter')
    def test_generate_manual(self, mock_call_openrouter):
        """Test generating manual content and PDF"""
        # Mock AI response
        mock_call_openrouter.return_value = "**Step 1:** Do something."

        record = self.manual_model.create({
            'name': 'AI Test Manual',
            'module_ids': [(6, 0, [self.test_module.id])]
        })

        record._generate_manual_ai()

        # Check HTML output
        self.assertIn('Step 1', record.content)

        # Check PDF file is generated
        self.assertTrue(record.manual_file)
        self.assertTrue(record.manual_filename.endswith('.pdf'))

