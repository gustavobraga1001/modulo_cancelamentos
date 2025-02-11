from odoo import models, fields

class ProjectSector(models.Model):
    _name = 'project.sector'
    _description = 'Setor do Projeto'

    name = fields.Char(string='Nome do Setor', required=True)
    user_ids = fields.Many2many(
        'res.users', 
        'project_sector_user_rel',  # Tabela intermediária
        'sector_id', 'user_id',  # Campos de relação
        string='Usuários'
    )
