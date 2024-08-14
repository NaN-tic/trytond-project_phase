import datetime
import unittest

from proteus import Model
from trytond.modules.company.tests.tools import create_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        # Activate project
        activate_modules('project_phase')

        # Create a company
        _ = create_company()

        # Create status
        WorkStatus = Model.get('project.work.status')
        open, = WorkStatus.find([('name', '=', "Open")])
        done, = WorkStatus.find([('name', '=', "Done")])

        # Create workflow
        Workflow = Model.get('project.work.workflow')
        workflow = Workflow()
        workflow.name = 'Task'
        line = workflow.lines.new()
        line.status = open
        line = workflow.lines.new()
        line.status = done
        workflow.save()

        # Create tracker
        Tracker = Model.get('project.work.tracker')
        tracker = Tracker()
        tracker.name = 'Task'
        tracker.workflow = workflow
        tracker.save()

        # Create a project with a task
        Work = Model.get('project.work')
        project = Work(type='project', name="Project")
        project.tracker = tracker
        self.assertEqual(project.status, open)
        project.save()  ## AQUI
        project, = Work.find([('type', '=', 'project')])
        self.assertEqual(project.status, open)
        task = project.children.new(name="Task")
        task.tracker = tracker
        self.assertEqual(task.status, open)
        project.save()  ## ALLA
        task, = project.children
        task, = Work.find([('type', '=', 'task')])

        # Check task closing_date and active
        self.assertEqual(task.closing_date, None)
        self.assertEqual(task.active, True)
        task.status = done
        task.save()
        self.assertEqual(task.closing_date.date(), datetime.date.today())
        self.assertEqual(task.active, True)
        task.status = open
        task.save()
        self.assertEqual(task.closing_date, None)
        self.assertEqual(task.active, True)

        # Check project active
        self.assertEqual(project.active, True)
        project, = Work.find([('type', '=', 'project')])
        self.assertEqual(project.name, 'Project')
        project.status = done
        self.assertEqual(project.status.progress, 1)
        project.save()  ## MES ENLLA
        self.assertEqual(project.active, False)
