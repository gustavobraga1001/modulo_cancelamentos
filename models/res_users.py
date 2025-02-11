from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    sector_ids = fields.Many2many(
        'project.sector',  # Modelo do setor
        'project_sector_user_rel',  # Tabela intermediária
        'user_id', 'sector_id',  # Campos de relação
        string='Setores'
    )
