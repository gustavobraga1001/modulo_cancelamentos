{
    'name': 'Custom Task Management',
    'version': '1.0',
    'category': 'Project',
    'author': 'Gustavo Braga',
    'depends': ['project', 'mail', 'base'],
    'data': [
        'security/ir.model.access.csv',
        'views/project_task_view.xml',
        'views/project_sector_view.xml',
        'views/project_sector_menu.xml'
    ],
    'installable': True,
    'application': True,
}
