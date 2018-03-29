# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import task


def register():
    Pool.register(
        task.TaskPhase,
        task.TaskPhaseTracker,
        task.Work,
        task.Workflow,
        task.WorkflowLine,
        task.Tracker,
        module='project_phase', type_='model')
