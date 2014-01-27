# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Contains methods related to formatting the progress reports sent back to Pulp
by all of the puppet plugins.
"""

import time
import traceback


def format_exception(e):
    """
    Formats the given exception to be included in the report.

    :return: string representation of the exception
    :rtype:  str
    """
    return str(e)


def format_traceback(tb):
    """
    Formats the given traceback to be included in the report.

    :return: string representation of the traceback
    :rtype:  str
    """
    if tb:
        return traceback.extract_tb(tb)
    else:
        return None


class Timer(object):
    """
    Timer object used to determine elapsed time.

    :ivar started: The stated timestamp.
    :type started; float
    :ivar stopped: The stopped timestamp.
    :type stopped: float
    """

    def __init__(self):
        self.started = 0
        self.stopped = 0

    def reset(self):
        """
        Rest the timer.
        """
        self.started = 0
        self.stopped = 0

    def start(self):
        """
        Start the timer.
        """
        self.reset()
        self.started = time.time()

    def stop(self):
        """
        Stop the timer.
        :return:
        """
        if self.running():
            self.stopped = time.time()

    def running(self):
        """
        Get whether the timer is running.

        :return: True if running.
        :rtype: bool
        """
        return self.started > 0 and self.stopped == 0

    def duration(self):
        """
        Get how long the timer has been running.
        Stop the timer is still running.

        :return: The time that has elapsed between the when the
            timer was started and stopped in seconds.
        :rtype: float
        """
        self.stop()
        return self.stopped - self.started
