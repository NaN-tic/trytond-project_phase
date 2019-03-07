# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from datetime import timedelta, datetime
from sql import Column
from sql.conditionals import Coalesce
from sql.functions import Now, DateTrunc
from sql.aggregate import Max
from trytond.model import ModelView, ModelSQL, fields, sequence_ordered
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Bool
from trytond.transaction import Transaction
from trytond.i18n import gettext
from trytond.exceptions import UserError

__all__ = ['TaskPhase', 'TaskPhaseTracker', 'Work', 'Workflow', 'WorkflowLine',
    'Tracker']

def round_timedelta(td):
    return timedelta(seconds=round(td.total_seconds() / 60) * 60)

class TaskPhase(sequence_ordered(), ModelSQL, ModelView):
    'Project Phase'
    __name__ = 'project.work.task_phase'
    name = fields.Char('Name', required=True, translate=True, select=True)
    type = fields.Selection([
            (None, ''),
            ('initial', 'Initial'),
            ('final', 'Final'),
            ], 'Type')
    comment = fields.Text('Comment')
    workflows = fields.Many2Many('project.work.workflow.line', 'phase',
        'workflow', 'Workflows')
    required_effort = fields.Many2Many(
        'project.work.task_phase-project.work.tracker', 'task_phase',
        'tracker', 'Required Effort On')

    @classmethod
    def copy(cls, phases, default=None):
        if default is None:
            default = {}
        default.setdefault('workflows', None)
        default.setdefault('required_effort', None)
        return super(cls, TaskPhase).copy(phases, default)


class TaskPhaseTracker(ModelSQL):
    'TaskPhase - Tracker'
    __name__ = 'project.work.task_phase-project.work.tracker'
    task_phase = fields.Many2One('project.work.task_phase', 'Task Phase',
        ondelete='CASCADE', required=True, select=True)
    tracker = fields.Many2One('project.work.tracker', 'Tracker',
        ondelete='CASCADE', required=True, select=True)


class Work(metaclass=PoolMeta):
    __name__ = 'project.work'
    _history = True
    task_phase = fields.Many2One('project.work.task_phase', 'Task Phase',
        domain=[('workflows.trackers', 'in', [Eval('tracker')])],
        states={
            'readonly': ~Bool(Eval('tracker')),
            'required': Eval('type') == 'task',
            'invisible': Eval('type') != 'task',
            }, depends=['type', 'tracker'])
    since_phase = fields.Function(fields.TimeDelta('Since Phase'),
        'get_since_phase', searcher='search_since_phase')
    times_phase = fields.Function(fields.Integer('Times Phase'),
        'get_times_phase')
    time_phase = fields.Function(fields.TimeDelta('Time Phase'),
        'get_time_phase')

    @staticmethod
    def default_task_phase():
        Phase = Pool().get('project.work.task_phase')
        phases = Phase.search([('type', '=', 'initial')])
        if len(phases) == 1:
            return phases[0].id

    def get_closed_states(self):
        return ['done']

    @classmethod
    def get_since_query(cls, ids=None):
        # Use two joins with the history table. The first finds the first
        # previous record that had a different phase, whereas the second join
        # finds the immediately next record that already had the current value
        task = cls.__table__()
        history = cls.__table_history__()
        history2 = cls.__table_history__()

        interval = DateTrunc('minute', Now() - Max(Coalesce(history2.write_date,
                    history2.create_date)))

        query = task.join(history, condition=(task.id == history.id) &
            (task.task_phase != history.task_phase))
        query = query.select(history.id,
            Max(Column(history, '__id')).as_('__id'),
            group_by=[history.id])

        if ids:
            query.where = history.id.in_(ids)

        query = query.join(history2, condition=(query.id == history2.id)
            & (Column(query, '__id') < Column(history2, '__id')))
        query = query.select(history2.id, interval, group_by=[history2.id])
        return query, interval

    @classmethod
    def get_since_phase(cls, works, name):
        cursor = Transaction().connection.cursor()
        res = dict([(x.id, datetime.now() - x.create_date) for x in works])
        query, _ = cls.get_since_query(ids=[x.id for x in works])
        cursor.execute(*query)
        res = dict(cursor.fetchall())
        now = datetime.now()
        for work in works:
            if not work.id in res:
                res[work.id] = round_timedelta(now - work.create_date)
        return res

    @classmethod
    def search_since_phase(cls, name, clause):
        query, interval = cls.get_since_query()
        _, operator, value = clause
        Operator = fields.SQL_OPERATORS[operator]
        query.having = Operator(interval, value)
        query.columns = [query.columns[0]]
        return [('id', 'in', query)]

    def get_times_phase(self, name):
        if not self.task_phase:
            return 1
        history = self.__table_history__()
        cursor = Transaction().connection.cursor()
        cursor.execute(*history.select(history.task_phase,
                where=history.id == self.id,
                order_by=[Column(history, '__id').desc]))
        count = 1
        flap = False
        for record in cursor.fetchall():
            if record[0] != self.task_phase.id:
                flap = True
            elif flap:
                count += 1
                flap = False
        return count

    def get_time_phase(self, name):
        if not self.task_phase:
            return timedelta()
        history = self.__table_history__()
        cursor = Transaction().connection.cursor()
        cursor.execute(*history.select(history.task_phase,
                Coalesce(history.write_date, history.create_date),
                where=history.id == self.id,
                order_by=[Column(history, '__id').desc]))
        end = datetime.now()
        elapsed = timedelta()
        for record in cursor.fetchall():
            start = record[1]
            if record[0] == self.task_phase.id:
                elapsed += end - start
            end = start
        return round_timedelta(elapsed)

    def check_phase(self):
        if (self.type != 'project' and
                self.state in self.get_closed_states() and self.task_phase
                and self.task_phase.type != 'final'):
            raise UserError(gettext('project_phase.invalid_phase',
                    work=self.rec_name,
                    phase=self.task_phase.rec_name ))

    def check_required_effort(self):
        if (self.task_phase and self.tracker and
                self.tracker in self.task_phase.required_effort):
            duration = self.effort_duration or timedelta()
            if (not duration > timedelta(seconds=0)):
                raise UserError(gettext('project_phase.required_effort',
                        work=self.rec_name))

    @classmethod
    def validate(cls, works):
        super(Work, cls).validate(works)
        for work in works:
            work.check_phase()
            work.check_required_effort()


class Workflow(ModelSQL, ModelView):
    'Project Workflow'
    __name__ = 'project.work.workflow'
    name = fields.Char('Name', required=True, translate=True)
    lines = fields.One2Many('project.work.workflow.line', 'workflow', 'Phases')
    trackers = fields.One2Many('project.work.tracker', 'workflow', 'Trackers')

    @classmethod
    def copy(cls, workflows, default=None):
        if default is None:
            default = {}
        default.setdefault('trackers', None)
        return super(Workflow, cls).copy(workflows, default=None)


class Tracker(metaclass=PoolMeta):
    __name__ = 'project.work.tracker'
    workflow = fields.Many2One('project.work.workflow', 'Workflow',
        required=True)


class WorkflowLine(sequence_ordered(), ModelSQL, ModelView):
    'Project Workflow Line'
    __name__ = 'project.work.workflow.line'
    workflow = fields.Many2One('project.work.workflow', 'Workflow',
        required=True)
    phase = fields.Many2One('project.work.task_phase', 'Phase', required=True)
