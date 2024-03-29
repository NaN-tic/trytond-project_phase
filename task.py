# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from datetime import timedelta, datetime
from sql import Column
from sql.conditionals import Coalesce
from sql.functions import Now, DateTrunc
from sql.aggregate import Max
from trytond.model import ModelView, ModelSQL, fields, sequence_ordered
from trytond.pool import PoolMeta
from trytond.pyson import Eval, Bool, If
from trytond.transaction import Transaction
from trytond.i18n import gettext
from trytond.exceptions import UserError

def round_timedelta(td):
    return timedelta(seconds=round(td.total_seconds() / 60) * 60)


class WorkStatus(metaclass=PoolMeta):
    __name__ = 'project.work.status'
    comment = fields.Text('Comment')
    workflows = fields.Many2Many('project.work.workflow.line', 'status',
        'workflow', 'Workflows')
    required_effort = fields.Many2Many(
        'project.work.status-project.work.tracker', 'status',
        'tracker', 'Required Effort On')

    @classmethod
    def copy(cls, statuses, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()
        default.setdefault('workflows', None)
        default.setdefault('required_effort', None)
        return super().copy(statuses, default)


class WorkStatusTracker(ModelSQL):
    'Status - Tracker'
    __name__ = 'project.work.status-project.work.tracker'
    status = fields.Many2One('project.work.status', 'Status',
        ondelete='CASCADE', required=True)
    tracker = fields.Many2One('project.work.tracker', 'Tracker',
        ondelete='CASCADE', required=True)


class Work(metaclass=PoolMeta):
    __name__ = 'project.work'
    _history = True
    active = fields.Function(fields.Boolean("Active"), 'get_active',
        searcher='search_active')
    closing_date = fields.DateTime('Closing Date', readonly=True)
    since_status = fields.Function(fields.TimeDelta('Since Status'),
        'get_since_status', searcher='search_since_status')
    times_status = fields.Function(fields.Integer('Times Status'),
        'get_times_status')
    time_status = fields.Function(fields.TimeDelta('Time Status'),
        'get_time_status')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        readonly = cls.status.states.get('readonly', True)
        cls.status.states['readonly'] = readonly & ~Bool(Eval('tracker'))
        cls.status.depends.add('tracker')
        cls.status.depends.add('type')
        cls.status.domain += [If(Eval('type') == 'task',
                ('workflows.trackers', 'in', [Eval('tracker')]),
                ())]
        cls._buttons.update({
                'next_status': {
                    'icon': 'tryton-forward',
                    },
                'previous_status': {
                    'icon': 'tryton-back',
                    },
                })

    @classmethod
    @ModelView.button
    def next_status(cls, works):
        for work in works:
            found = False
            for line in work.tracker.workflow.lines:
                if found:
                    break
                if line.status == work.status:
                    found = True
            else:
                continue
            work.status = line.status
            work.on_change_status()
        cls.save(works)

    @classmethod
    @ModelView.button
    def previous_status(cls, works):
        for work in works:
            previous = None
            for line in work.tracker.workflow.lines:
                if line.status == work.status:
                    break
                previous = line.status
            else:
                continue
            if previous:
                work.status = previous
                work.on_change_status()
        cls.save(works)

    def get_active(self, name):
        if self.type == 'project':
            return self.status.progress != 1
        return True

    @classmethod
    def search_active(cls, name, clause):
        pos = ['OR', [
                ('type', '=', 'task')
                ], [
                ('type', '=', 'project'),
                    ['OR',
                        ('status.progress', '=', None),
                        ('status.progress', '!=', 1),
                        ],
                ]
            ]
        neg = ['OR', [
                ('type', '=', 'task')
                ],[
                    ('type', '=', 'project'),
                    ('status.progress', '=', 1),
                ]
            ]
        operator = clause[1]
        operand = clause[2]
        res = []
        if operator == 'in':
            if True in operand and False in operand:
                res = ['OR', pos, neg]
            elif True in operand:
                res = pos
            elif False in operand:
                res = neg
        elif operator in ('=', '!='):
            operator = operator == '=' and 1 or -1
            operand = operand and 1 or -1
            sign = operator * operand

            if sign > 0:
                res = pos
            else:
                res = neg
        if not res:
            res = pos
        return res

    @classmethod
    def get_total(cls, works, names):
        # allow function fields get values in case is not active
        with Transaction().set_context(active_test=False):
            return super().get_total(works, names)

    @classmethod
    def get_since_query(cls, ids=None):
        # Use two joins with the history table. The first finds the first
        # previous record that had a different status, whereas the second join
        # finds the immediately next record that already had the current value
        task = cls.__table__()
        history = cls.__table_history__()
        history2 = cls.__table_history__()

        interval = DateTrunc('minute', Now() - Max(Coalesce(history2.write_date,
                    history2.create_date)))

        query = task.join(history, condition=(task.id == history.id) &
            (task.status != history.status))
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
    def get_since_status(cls, works, name):
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
    def search_since_status(cls, name, clause):
        query, interval = cls.get_since_query()
        _, operator, value = clause
        Operator = fields.SQL_OPERATORS[operator]
        query.having = Operator(interval, value)
        query.columns = [query.columns[0]]
        return [('id', 'in', query)]

    def get_times_status(self, name):
        if not self.status:
            return 1
        history = self.__table_history__()
        cursor = Transaction().connection.cursor()
        cursor.execute(*history.select(history.status,
                where=history.id == self.id,
                order_by=[Column(history, '__id').desc]))
        count = 1
        flap = False
        for record in cursor.fetchall():
            if record[0] != self.status.id:
                flap = True
            elif flap:
                count += 1
                flap = False
        return count

    def get_time_status(self, name):
        if not self.status:
            return timedelta()
        history = self.__table_history__()
        cursor = Transaction().connection.cursor()
        cursor.execute(*history.select(history.status,
                Coalesce(history.write_date, history.create_date),
                where=history.id == self.id,
                order_by=[Column(history, '__id').desc]))
        end = datetime.now()
        elapsed = timedelta()
        for record in cursor.fetchall():
            start = record[1]
            if record[0] == self.status.id:
                elapsed += end - start
            end = start
        return round_timedelta(elapsed)

    def check_required_effort(self):
        if (self.status and self.tracker and
                self.tracker in self.status.required_effort):
            duration = self.effort_duration or timedelta()
            if (not duration > timedelta(seconds=0)):
                raise UserError(gettext('project_phase.required_effort',
                        work=self.rec_name))

    @classmethod
    def validate(cls, works):
        super().validate(works)
        for work in works:
            work.check_required_effort()

    @classmethod
    def create(cls, vlist):
        works = super(Work, cls).create(vlist)
        cls.set_closing_date(works)
        return works

    @classmethod
    def write(cls, *args):
        super(Work, cls).write(*args)
        works = cls.browse(sum(args[::2], []))
        cls.set_closing_date(works)

    @classmethod
    def set_closing_date(cls, works):
        for work in works:
            if work.closing_date is None and work.status.progress == 1:
                work.closing_date = datetime.now().replace(microsecond=0)
            elif work.closing_date and work.status.progress != 1:
                work.closing_date = None
        cls.save(works)


class Workflow(ModelSQL, ModelView):
    'Project Workflow'
    __name__ = 'project.work.workflow'
    name = fields.Char('Name', required=True, translate=True)
    lines = fields.One2Many('project.work.workflow.line', 'workflow',
        'Statuses')
    trackers = fields.One2Many('project.work.tracker', 'workflow', 'Trackers')

    @classmethod
    def copy(cls, workflows, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()
        default.setdefault('trackers', None)
        return super().copy(workflows, default=None)


class Tracker(metaclass=PoolMeta):
    __name__ = 'project.work.tracker'
    workflow = fields.Many2One('project.work.workflow', 'Workflow',
        required=True)


class WorkflowLine(sequence_ordered(), ModelSQL, ModelView):
    'Project Workflow Line'
    __name__ = 'project.work.workflow.line'
    workflow = fields.Many2One('project.work.workflow', 'Workflow',
        required=True)
    status = fields.Many2One('project.work.status', 'Status', required=True)
