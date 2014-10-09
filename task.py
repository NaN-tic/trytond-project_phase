# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval

__all__ = ['TaskPhase', 'Work', 'TaskPhaseTracker']
__metaclass__ = PoolMeta


class TaskPhase(ModelSQL, ModelView):
    'Project Phase'
    __name__ = 'project.work.task_phase'

    name = fields.Char('Name', required=True, select=True)
    type = fields.Selection([(None, ''), ('initial', 'Initial'),
        ('final', 'Final')], 'Type')
    comment = fields.Text('comment')
    required_effort = fields.Many2Many(
        'project.work.task_phase-project.work.tracker', 'task_phase',
        'tracker', 'Required Effort On')


class TaskPhaseTracker(ModelSQL):
    'TaskPhase - Tracker'
    __name__ = 'project.work.task_phase-project.work.tracker'
    task_phase = fields.Many2One('project.work.task_phase', 'Task Phase',
        ondelete='CASCADE', required=True, select=True)
    tracker = fields.Many2One('project.work.tracker', 'Tracker',
        ondelete='CASCADE', required=True, select=True)


class Work:
    __name__ = 'project.work'

    task_phase = fields.Many2One('project.work.task_phase', 'Task Phase',
        states={
            'required': Eval('type') == 'task',
            'invisible': Eval('type') != 'task',
            }, depends=['type'])

    @classmethod
    def __setup__(cls):
        super(Work, cls).__setup__()
        cls._error_messages.update({
                'invalid_phase': ('Task "%(work)s" can not be closed on '
                    'phase "%(phase)s".'),
                'required_effort': ('Task "%(work)s" can not saved without set'
                    ' effort'),
                })

    @staticmethod
    def default_task_phase():
        Phase = Pool().get('project.work.task_phase')
        phase = Phase.search([('type', '=', 'initial')])
        if phase:
            return phase[0].id

    def get_closed_states(self):
        return ['done']

    def check_phase(self):
        if (self.type != 'project' and
                self.state in self.get_closed_states() and self.task_phase
                and self.task_phase.type != 'final'):
            self.raise_user_error('invalid_phase', {
                    'work': self.rec_name,
                    'phase': self.task_phase.rec_name,
                    })

    def check_required_effort(self):
        if self.tracker in self.task_phase.required_effort:
            if not self.effort > 0:
                self.raise_user_error('required_effort', {
                    'work': self.rec_name,
                    })

    @classmethod
    def validate(cls, works):
        super(Work, cls).validate(works)
        for work in works:
            work.check_phase()
            work.check_required_effort()







