#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval

__all__ = ['TaskPhase', 'WorkType', 'Work']
__metaclass__ = PoolMeta


class TaskPhase(ModelSQL, ModelView):
    'Project Phase'
    __name__ = 'project.work.task_phase'

    name = fields.Char('Name', required=True, select=True)
    comment = fields.Text('comment')

class WorkType:
    __name__ = 'project.work.tracker'

    weight = fields.Integer('Weight', required=True)

class Work:
    __name__ = 'project.work'

    project_phase = fields.Function(fields.Char('Project Phase',
        states={
            'invisible': Eval('type') == 'task',
            }, depends=['type'] ), 'get_project_phase')
    task_phase = fields.Many2One('project.work.task_phase', 'Task Phase',
        states={
            'required': Eval('type') == 'task',
            'invisible': Eval('type') != 'task',
            }, depends=['type'])

    @classmethod
    def get_project_phase(cls, works, name):
        values={}
        for work in works:
            weight=0
            values[work.id] = 'unknown'
            for child in work.children:
                if child.tracker and child.tracker.weight > weight:
                    values[work.id] = child.tracker.rec_name
                    weight=child.tracker.weight
        return values




