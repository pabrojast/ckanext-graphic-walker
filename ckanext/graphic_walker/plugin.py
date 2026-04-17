# encoding: utf-8
"""
CKAN plugin for interactive CSV visualization using Graphic Walker.
"""
import json
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import os

from .api import graphic_walker_api

PLUGIN_NAME = 'graphic_walker'


class GraphicWalkerPlugin(plugins.SingletonPlugin):
    """CKAN plugin for interactive CSV visualization using Graphic Walker."""

    def __init__(self, name=None):
        super().__init__()
        self.default_title = 'Data Explorer'
        self.supported_formats = {'csv'}
        self.max_rows = 50000
        self.site_url = ''

    plugins.implements(plugins.IConfigurer)
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')

    plugins.implements(plugins.IBlueprint)
    def get_blueprint(self):
        return graphic_walker_api

    plugins.implements(plugins.IConfigurable, inherit=True)
    def configure(self, config):
        self.site_url = config.get('ckan.site_url', '')
        self.default_title = config.get(
            f'ckanext.{PLUGIN_NAME}.default_title', 'Data Explorer'
        )
        formats_str = config.get(f'ckanext.{PLUGIN_NAME}.formats', 'csv')
        self.supported_formats = {f.strip().lower() for f in formats_str.split(',')}
        self.max_rows = int(config.get(f'ckanext.{PLUGIN_NAME}.max_rows', '50000'))

    plugins.implements(plugins.IResourceView, inherit=True)
    def info(self):
        ignore_missing = toolkit.get_validator('ignore_missing')
        return {
            'name': PLUGIN_NAME,
            'title': toolkit._('Graphic Walker'),
            'default_title': toolkit._(self.default_title),
            'icon': 'bar-chart-o',
            'always_available': False,
            'filterable': True,
            'iframed': False,
            'schema': {
                'chart_specs': [ignore_missing],
            },
        }

    def can_view(self, data_dict):
        resource = data_dict.get('resource', {})
        fmt = resource.get('format', '').lower().strip()
        return fmt in self.supported_formats

    def setup_template_variables(self, context, data_dict):
        resource = data_dict['resource']
        view = data_dict.get('resource_view', {})

        saved_specs = view.get('chart_specs', '')
        chart_specs = None
        if saved_specs and isinstance(saved_specs, str):
            try:
                chart_specs = json.loads(saved_specs)
            except (json.JSONDecodeError, TypeError):
                chart_specs = None

        user = context.get('user', '') or ''
        try:
            user = toolkit.c.user or ''
        except Exception:
            pass

        return {
            'resource_id': resource.get('id', ''),
            'resource_name': resource.get('name', 'Dataset'),
            'resource_format': resource.get('format', 'CSV'),
            'view_title': view.get('title', self.default_title),
            'view_id': view.get('id', ''),
            'max_rows': self.max_rows,
            'api_url': f'/api/graphic_walker/data/{resource.get("id", "")}',
            'chart_specs_json': json.dumps(chart_specs) if chart_specs else 'null',
            'user': user,
        }

    def view_template(self, context, data_dict):
        return 'graphic_walker.html'
