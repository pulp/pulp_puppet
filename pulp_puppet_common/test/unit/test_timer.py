# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from unittest import TestCase

from pulp_puppet.common.reporting import Timer


class TestTimer(TestCase):

    def test_constructor(self):
        timer = Timer()
        self.assertEqual(timer.started, 0)
        self.assertEqual(timer.stopped, 0)

    def test_reset(self):
        timer = Timer()
        timer.started = 100
        timer.stopped = 200
        timer.reset()
        self.assertEqual(timer.started, 0)
        self.assertEqual(timer.stopped, 0)

    def test_start(self):
        timer = Timer()
        timer.start()
        self.assertTrue(timer.started > 0)
        self.assertEqual(timer.stopped, 0)
        timer.stopped = 100
        timer.start()
        self.assertTrue(timer.started > 0)
        self.assertEqual(timer.stopped, 0)

    def test_running(self):
        timer = Timer()
        self.assertFalse(timer.running())
        timer.start()
        self.assertTrue(timer.running())

    def test_stop(self):
        timer = Timer()
        timer.start()
        timer.stop()
        self.assertTrue(timer.stopped > 0)
        stopped = timer.stopped
        timer.stop()
        self.assertEqual(timer.stopped, stopped)

    def test_duration(self):
        timer = Timer()
        self.assertEqual(timer.duration(), 0)
        timer.started = 10
        timer.stopped = 20
        self.assertEqual(timer.duration(), 10)