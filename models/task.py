from odoo import models, fields, api
import json
import logging

_logger = logging.getLogger(__name__)

class ProjectTask(models.Model):
    _inherit = 'project.task'

    responsaveis_setores = fields.Text(
        string="Responsáveis pelos Setores",
        help="Responsáveis atribuídos aos setores em formato JSON",
    )

    setores_task = fields.Many2many(
        'project.sector', 
        string='Setores Responsáveis',
        help="Selecione os setores responsáveis.",
    )

    @api.model
    def create(self, vals):
        return super(ProjectTask, self).create(vals)

    def write(self, vals):
        stage_em_andamento = self.env['project.task.type'].search([('name', '=', 'Em andamento')], limit=1)
        stage_finalizado = self.env['project.task.type'].search([('name', '=', 'Finalizados')], limit=1)

        if stage_em_andamento or stage_finalizado:
            new_stage_id = vals.get('stage_id')
            
            if new_stage_id == stage_em_andamento.id:
                for task in self:
                    self.criar_subtarefas(task)

        result = super(ProjectTask, self).write(vals)

        if 'stage_id' in vals:
            for task in self:
                if task.parent_id: 
                    self._verificar_subtarefas_finalizadas(task.parent_id)
        
        return result

    def criar_subtarefas(self, record):
        responsaveis_por_setor = {}
        for setor in record.setores_task:
            usuarios = self.env['res.users'].search([('sector_ids', '=', setor.id)])
            
            if usuarios:
                if setor.name not in responsaveis_por_setor:
                    responsaveis_por_setor[setor.name] = []
                for usuario in usuarios:
                    responsaveis_por_setor[setor.name].append(usuario.id)  # Salvando apenas o ID do usuário

        record.responsaveis_setores = json.dumps(responsaveis_por_setor)

        for setor, usuarios_ids in responsaveis_por_setor.items():
            estagio_setor = self.env['project.task.type'].search([('name', '=', setor)], limit=1)
            if estagio_setor:
                self._criar_subtarefa(
                    'Subtarefa de %s - %s' % (record.name, setor), 
                    record, 
                    usuarios_ids, 
                    estagio_setor
                )

    def _criar_subtarefa(self, nome_subtarefa, record, responsaveis_ids, estagio):
        subtarefa = self.env['project.task'].create({
            'name': nome_subtarefa,
            'parent_id': record.id,
            'project_id': record.project_id.id,
            'user_ids': [(6, 0, responsaveis_ids)], 
            'stage_id': estagio.id,
        })
        self.agendar_atividade(subtarefa)

    def agendar_atividade(self, subtarefa):
        model_id = self.env['ir.model']._get('project.task').id

        if not subtarefa.user_ids:
            raise ValueError('A subtarefa não tem responsáveis atribuídos.')

        self.env['mail.activity'].create({
            'res_model_id': model_id,
            'res_id': subtarefa.id,
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'summary': 'Acompanhar subtarefa',
            'user_id': subtarefa.user_ids[0].id,
            'date_deadline': fields.Date.today(),
        })

    def _verificar_subtarefas_finalizadas(self, parent_task):
        _logger.info("Verificando subtarefas finalizadas para a tarefa principal: %s", parent_task.name)
        
        subtasks = self.env['project.task'].search([('parent_id', '=', parent_task.id)])
        
        if not subtasks:
            _logger.warning("Nenhuma subtarefa encontrada para a tarefa principal %s", parent_task.name)
        
        all_finalized = False
        for subtask in subtasks:
            _logger.info("Subtarefa '%s' está no estágio: %s", subtask.name, subtask.stage_id.name)
            if subtask.stage_id.name == 'Finalizados':
                all_finalized = True
                _logger.info(subtask.stage_id.name, subtask.name)
        
        if all_finalized:
            _logger.info("Todas as subtarefas estão finalizadas. Criando atividade para o responsável da tarefa principal.")
            self._criar_atividade_para_responsavel(parent_task)
        else:
            _logger.info("Nem todas as subtarefas estão finalizadas. Não criando atividade para o responsável.")


    def _criar_atividade_para_responsavel(self, task):
        if task.user_ids:
            user_responsavel = task.user_ids[0]
            _logger.info("Criando atividade para o responsável: %s", user_responsavel.name)
        else:
            raise ValueError("A tarefa não tem um responsável atribuído.")
        
        self.env['mail.activity'].create({
            'res_model_id': self.env['ir.model'].search([('model', '=', 'project.task')]).id,
            'res_id': task.id,
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,  # Tipo de atividade (lembrar ou tarefa)
            'summary': 'Todas as subtarefas de: ' + task.name + 'foram finalizadas',
            'user_id': user_responsavel.id,
            'date_deadline': fields.Date.today(),
        })
