# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
import doctest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase
from trytond.tests.test_tryton import doctest_checker
from trytond.tests.test_tryton import doctest_teardown


class ProjectPhaseTestCase(ModuleTestCase):
    'Test Project Phase Module'
    module = 'project_phase'


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        ProjectPhaseTestCase))
    suite.addTests(doctest.DocFileSuite(
            'scenario_project.rst',
            tearDown=doctest_teardown, encoding='utf-8',
            checker=doctest_checker,
            optionflags=doctest.REPORT_ONLY_FIRST_FAILURE))
    return suite
