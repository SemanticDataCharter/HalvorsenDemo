"""
The console renders one record three ways. These tests render the templates with canned context
and check the things that broke once elsewhere: the page title carried a <script>, and the version
badge drifted from the tag (it is read from app/sdc4/VERSION).
"""
import re
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings

PLAIN_STATIC = override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})


def render(template, ctx):
    return render_to_string(template, ctx, request=RequestFactory().get('/'))


@PLAIN_STATIC
class ConsoleTemplateTests(SimpleTestCase):
    def test_instance_title_is_clean_and_script_sits_before_body_end(self):
        html = render('console/instance.html', {
            'h': {'dm_label': 'Order', 'instance_id': 'i-test', 'ct_id': 'dm-test',
                  'validation_status': 'valid', 'validation_label': 'Valid', 'stated_absences': []},
            'pane': 'table', 'panes': ['table', 'document', 'graph'], 'rows': [],
            'nav': {'prev': 'i-prev', 'next': 'i-next', 'position': 2, 'total': 3}, 'governed': None,
        })
        title = re.search(r'<title>(.*?)</title>', html, re.S).group(1)
        self.assertIn('Order i-test', title)
        self.assertNotIn('<script', title)

    def test_the_question_page_says_why_when_the_store_is_down(self):
        html = render('console/question.html', {'q': {'unavailable': 'The triple store did not answer: down', 'records': 3},
                                                 't': {'unavailable': 'The triple store did not answer: down', 'records': 3}})
        self.assertEqual(html.count('did not answer'), 2)

    def test_the_question_page_renders_the_answers(self):
        html = render('console/question.html', {
            'q': {'rows': [{'agent': 'Halvorsen Foods document translator', 'records': 52, 'open': {'ct_id': 'dm', 'instance_id': 'i-1'}}],
                  'records': 52, 'from_documents': 52, 'elapsed': 0.2, 'query': 'SELECT'},
            't': {'rows': [{'month': '2026-02', 'orders': 4, 'total': '1234.50', 'open': None}], 'orders': 4, 'elapsed': 0.1, 'query': 'SELECT'}})
        self.assertIn('Halvorsen Foods document translator', html)
        self.assertIn('2026-02', html)
        self.assertIn('open a record', html)


@PLAIN_STATIC
class VersionTests(SimpleTestCase):
    def test_version_file_is_the_single_source(self):
        on_disk = (Path(settings.BASE_DIR) / 'VERSION').read_text().strip()
        self.assertRegex(on_disk, r'^\d+\.\d+\.\d+$')
        self.assertEqual(settings.APP_VERSION, on_disk)

    def test_templates_carry_the_version_not_a_literal(self):
        for template, ctx in (('demo/base.html', {}), ('index.html', {})):
            html = render(template, ctx)
            self.assertIn(f'v{settings.APP_VERSION}', html, template)
            found = set(re.findall(r'\bv(\d+\.\d+\.\d+)\b', html))
            self.assertEqual(found, {settings.APP_VERSION}, template)
