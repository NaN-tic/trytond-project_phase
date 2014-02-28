#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval

__all__ = ['TaskPhase', 'Work']
__metaclass__ = PoolMeta


class TaskPhase(ModelSQL, ModelView):
    'Project Phase'
    __name__ = 'project.work.task_phase'

    name = fields.Char('Name', required=True, select=True)
    comment = fields.Text('comment')

class Work:
    __name__ = 'project.work'

    task_phase = fields.Many2One('project.work.task_phase', 'Task Phase',
        states={
            'required': Eval('type') == 'task',
            'invisible': Eval('type') != 'task',
            }, depends=['type'])





