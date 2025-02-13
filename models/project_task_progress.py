import json
from odoo import models, fields, api

class ProjectTask(models.Model):
    _inherit = 'project.task'

    responsible_sectors = fields.Text(
        string="Responsável do Setor",
        help="Responsible persons assigned to the sectors in JSON format",
    )

    task_sectors = fields.Many2many(
        'project.sector', 
        string='Setores Responsáveis',
        help="Select the responsible sectors.",
    )

    @api.model
    def create(self, vals):
        result = super(ProjectTask, self).create(vals)
        return result

    def write(self, vals):
        self = self.with_context(mail_notify_force_send=False)

        result = super(ProjectTask, self).write(vals)

        if 'stage_id' in vals:
            for task in self:
                if task.project_id.name == 'Retiradas e Cancelamento':
                    if task.stage_id.name == 'Em andamento':
                        task.validation_sectors(task)
                    if task.parent_id and task.stage_id.name == "Finalizados": 
                        self._check_completed_subtasks(task.parent_id)

        return result

    def validation_sectors(self, record):
        sector_responsibles = {}
        for sector in record.task_sectors:
            users = self.env['res.users'].search([('sector_ids', '=', sector.id)])
            
            if users:
                if sector.name not in sector_responsibles:
                    sector_responsibles[sector.name] = []
                for user in users:
                    sector_responsibles[sector.name].append(user.id) 

        record.responsible_sectors = json.dumps(sector_responsibles)

        for sector, user_ids in sector_responsibles.items():
            sector_stage = self.env['project.task.type'].search([('name', '=', sector)], limit=1)
            if sector_stage:
                self._create_subtask(
                    'Subtarefa de: %s - %s' % (record.name, sector), 
                    record, 
                    user_ids, 
                    sector_stage
                )
        
    def _create_subtask(self, subtask_name, record, responsible_ids, stage):
        subtask = self.env['project.task'].create({
            'name': subtask_name,
            'parent_id': record.id,
            'project_id': record.project_id.id,
            'user_ids': [(6, 0, responsible_ids)], 
            'stage_id': stage.id,
        })
        self.schedule_activity(subtask)

    def schedule_activity(self, subtask):
        model_id = self.env['ir.model']._get('project.task').id

        if not subtask.user_ids:
            raise ValueError('The subtask has no assigned responsible persons.')

        self.env['mail.activity'].create({
            'res_model_id': model_id,
            'res_id': subtask.id,
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'summary': 'Acompanhar a subtarefa',
            'user_id': subtask.user_ids[0].id,
            'date_deadline': fields.Date.today(),
        })

    def _check_completed_subtasks(self, parent_task):
        subtasks = self.env['project.task'].search([('parent_id', '=', parent_task.id)])
        
        all_finalized = False
        for subtask in subtasks:
            if subtask.stage_id.name == 'Finalizados':
                all_finalized = True
        
        if all_finalized:
            self._create_activity_for_responsible(parent_task)
                    
    def _create_activity_for_responsible(self, task):
        if task.user_ids:
            user_responsible = task.user_ids[0]
        else:
            raise ValueError("The task has no assigned responsible person.")
        
        self.env['mail.activity'].create({
            'res_model_id': self.env['ir.model'].search([('model', '=', 'project.task')]).id,
            'res_id': task.id,
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id, 
            'summary': 'Todas as tarefas de: ' + task.name + ' foram concluidas',
            'user_id': user_responsible.id,
            'date_deadline': fields.Date.today(),
        })
