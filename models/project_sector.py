from odoo import models, fields

class ProjectSector(models.Model):
    _name = 'project.sector'
    _description = 'Project Sector'

    name = fields.Char(string='Nome do Setor', required=True)
    user_ids = fields.Many2many(
        'res.users', 
        'project_sector_user_rel',  # Intermediate table
        'sector_id', 'user_id',  # Relation fields
        string='Usuários'
    )
