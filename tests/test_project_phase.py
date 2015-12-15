# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT
from trytond.transaction import Transaction


class TestCase(ModuleTestCase):
    'Test module'
    module = 'project_phase'

    def setUp(self):
        super(TestCase, self).setUp()
        self.task_phase = POOL.get('project.work.task_phase')

    def test0010_create_phases(self):
        with Transaction().start(DB_NAME, USER,
                context=CONTEXT) as transaction:
            #This is needed in order to get default values for other test
            #executing in the same database
            self.task_phase.create([{
                    'name': 'Initial',
                    'type': 'initial',
                    }, {
                    'name': 'Final',
                    'type': 'final',
                    }])
            transaction.cursor.commit()


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCase))
    return suite
