from pulp.client.commands.options import OPTION_REPO_ID
from pulp.client.commands.schedule import ListScheduleCommand, CreateScheduleCommand, \
    DeleteScheduleCommand, UpdateScheduleCommand, NextRunCommand

from pulp_puppet.devel import base_cli
from pulp_puppet.extensions.admin.repo import publish_schedules


class TestScheduleCommands(base_cli.ExtensionTests):

    def test_puppet_list_schedule_command(self):
        command = publish_schedules.PuppetListScheduleCommand(self.context)

        self.assertTrue(isinstance(command, ListScheduleCommand))
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertEqual(command.name, 'list')
        self.assertEqual(command.description, publish_schedules.DESC_LIST)

    def test_puppet_create_schedule_command(self):
        command = publish_schedules.PuppetCreateScheduleCommand(self.context)

        self.assertTrue(isinstance(command, CreateScheduleCommand))
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertEqual(command.name, 'create')
        self.assertEqual(command.description, publish_schedules.DESC_CREATE)

    def test_puppet_delete_schedule_command(self):
        command = publish_schedules.PuppetDeleteScheduleCommand(self.context)

        self.assertTrue(isinstance(command, DeleteScheduleCommand))
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertEqual(command.name, 'delete')
        self.assertEqual(command.description, publish_schedules.DESC_DELETE)

    def test_puppet_update_schedule_command(self):
        command = publish_schedules.PuppetUpdateScheduleCommand(self.context)

        self.assertTrue(isinstance(command, UpdateScheduleCommand))
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertEqual(command.name, 'update')
        self.assertEqual(command.description, publish_schedules.DESC_UPDATE)

    def test_puppet_next_run_command(self):
        command = publish_schedules.PuppetNextRunCommand(self.context)

        self.assertTrue(isinstance(command, NextRunCommand))
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertEqual(command.name, 'next')
        self.assertEqual(command.description, publish_schedules.DESC_NEXT_RUN)
