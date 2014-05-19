#!/usr/bin/env python
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.

import sys
import os
DIR = os.path.abspath(os.path.normpath(os.path.join(__file__,
    '..', '..', '..', '..', '..', 'trytond')))
if os.path.isdir(DIR):
    sys.path.insert(0, os.path.dirname(DIR))

import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import test_view, test_depends
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT
from trytond.transaction import Transaction


class TestCase(unittest.TestCase):
    'Test module'

    def setUp(self):
        trytond.tests.test_tryton.install_module('project_phase')
        self.task_phase = POOL.get('project.work.task_phase')

    def test0005views(self):
        'Test views'
        test_view('project_phase')

    def test0006depends(self):
        'Test depends'
        test_depends()

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

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
