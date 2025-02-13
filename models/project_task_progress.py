from odoo import models, fields, api
import json

class ProjectTask(models.Model):
    _inherit = 'project.task'

    responsible_departments = fields.Text(
        string="Responsável do Setor",
        help="Responsible persons assigned to the departments in JSON format",
    )

    task_departments = fields.Many2many(
        'project.sector', 
        string='Departamentos Responsáveis',
        help="Select the responsible departments.",
    )

    @api.model
    def create(self, vals):
        return super(ProjectTask, self).create(vals)

    def write(self, vals):
        cancellation_project = self.env['project.project'].search([('name', '=', 'Retiradas e Cancelamento')], limit=1)

        self = self.with_context(mail_notify_force_send=False)

        in_progress_stage = self.env['project.task.type'].search([
            ('name', '=', 'Em andamento'),
            ('project_ids', 'in', [cancellation_project.id])
            ], limit=1)        
        completed_stage = self.env['project.task.type'].search([
            ('name', '=', 'Finalizados'), 
            ('project_ids', 'in', [cancellation_project.id])
            ], limit=1)

        if in_progress_stage or completed_stage:
            new_stage_id = vals.get('stage_id')
            
            if new_stage_id == in_progress_stage.id:
                for task in self:
                    self.validation_departments(task)

        result = super(ProjectTask, self).write(vals)

        if 'stage_id' in vals:
            for task in self:
                if task.parent_id: 
                    self._check_completed_subtasks(task.parent_id)
        
        return result

    def validation_departments(self, record):
        department_responsibles = {}
        for department in record.task_departments:
            users = self.env['res.users'].search([('sector_ids', '=', department.id)])
            
            if users:
                if department.name not in department_responsibles:
                    department_responsibles[department.name] = []
                for user in users:
                    department_responsibles[department.name].append(user.id) 

        record.responsible_departments = json.dumps(department_responsibles)

        for department, user_ids in department_responsibles.items():
            department_stage = self.env['project.task.type'].search([('name', '=', department)], limit=1)
            if department_stage:
                self._create_subtask(
                    'Subtarefa de: %s - %s' % (record.name, department), 
                    record, 
                    user_ids, 
                    department_stage
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