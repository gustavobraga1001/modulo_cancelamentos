from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    sector_ids = fields.Many2many(
        'project.sector',  
        'project_sector_user_rel',  
        'user_id', 'sector_id',  
        string='Setores'
    )
