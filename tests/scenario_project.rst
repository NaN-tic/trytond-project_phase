================
Project Scenario
================

Imports::

    >>> import datetime
    >>> from proteus import Model
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company

Activate project::

    >>> config = activate_modules('project_phase')

Create a company::

    >>> _ = create_company()

Create status::

    >>> WorkStatus = Model.get('project.work.status')
    >>> open, = WorkStatus.find([('name', '=', "Open")])
    >>> done, = WorkStatus.find([('name', '=', "Done")])

Create workflow::

   >>> Workflow = Model.get('project.work.workflow')
   >>> workflow = Workflow()
   >>> workflow.name = 'Task'
   >>> line = workflow.lines.new()
   >>> line.status = open
   >>> line = workflow.lines.new()
   >>> line.status = done
   >>> workflow.save()

Create tracker::

   >>> Tracker = Model.get('project.work.tracker')
   >>> tracker = Tracker()
   >>> tracker.name = 'Task'
   >>> tracker.workflow = workflow
   >>> tracker.save()

Create a project with a task::

    >>> Work = Model.get('project.work')

    >>> project = Work(type='project', name="Project")
    >>> project.tracker = tracker
    >>> project.status == open
    True
    >>> project.save()
    >>> project, = Work.find([('type', '=', 'project')])
    >>> project.status == open
    True
    >>> task = project.children.new(name="Task")
    >>> task.tracker = tracker
    >>> task.status == open
    True

    >>> project.save()
    >>> task, = project.children
    >>> task, = Work.find([('type', '=', 'task')])

Check task closing_date and active::

    >>> task.closing_date is None
    True
    >>> task.active
    True
    >>> task.status = done
    >>> task.save()
    >>> task.closing_date.date() == datetime.date.today()
    True
    >>> task.active
    True
    >>> task.status = open
    >>> task.save()
    >>> task.closing_date is None
    True
    >>> task.active
    True

Check project active::

    >>> project.active
    True
    >>> project, = Work.find([('type', '=', 'project')])
    >>> project.name
    'Project'
    >>> project.status = done
    >>> project.status.progress == 1
    True
    >>> project.save()
    >>> project.active
    False

Check next/previous status buttons::

    >>> project = Work(type='project', name="Project")
    >>> project.tracker = tracker
    >>> project.status == open
    True
    >>> project.save()
    >>> project.click('previous_phase')  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    UserError: ('UserError', ('The "Open" status is the previous status of the "Project".', ''))
    >>> project.progress = 1
    >>> project.save()
    >>> project.click('next_phase')
    >>> project.status == done
    True
    >>> project.click('next_phase')  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    UserError: ('UserError', ('The "Done" status is the latest status of the "Project".', ''))