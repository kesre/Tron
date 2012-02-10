import datetime
import logging
from logging import handlers
import os
import platform
import shutil
import StringIO
import tempfile

from testify import *
from tron.config_parse import *
from tron.utils import timeutils


BASE_CONFIG = """
working_dir: "/tmp"

ssh_options:
    agent: true
    identities:
        - tests/test_id_rsa

nodes:
    - name: node0
      hostname: 'batch0'
    - name: node1
      hostname: 'batch1'

node_pools:
    - name: NodePool
      nodes: [node0, node1]
"""


def syslog_address_for_platform():
    if platform.system() == 'Darwin':
        return '/var/run/syslog'
    elif platform.system() == 'Windows':
        return ['localhost', 514]
    else:
        return '/dev/log'


class OldConfigTest(TestCase):
    OLD_BASE_CONFIG = """
--- !TronConfiguration
working_dir: "/tmp"

ssh_options: !SSHOptions
    agent: true
    identities:
        - tests/test_id_rsa

nodes:
    - &node0 !Node
        hostname: 'batch0'
    - &node1
        hostname: 'batch1'
    - &nodePool !NodePool
        nodes: [*node0, *node1]
    """

    config = OLD_BASE_CONFIG + """

command_context:
    batch_dir: /tron/batch/test/foo
    python: /usr/bin/python

jobs:
    - &job0 !Job
        name: "test_job0"
        node: *node0
        schedule: "interval 20s"
        actions:
            - &intAction !Action
                name: "action0_0"
                command: "test_command0.0"
        cleanup_action: !CleanupAction
            command: "test_command0.1"

    - &job1
        name: "test_job1"
        node: *node0
        schedule: "daily 00:30:00 MWF"
        actions:
            - &intAction2
                name: "action1_0"
                command: "test_command1.0"
            - &actionBar
                name: "action1_1"
                command: "test_command1.1"
                requires: *intAction2

    - &job2
        name: "test_job2"
        node: *node1
        schedule: "daily 16:30:00"
        actions:
            - &actionFail !Action
                name: "action2_0"
                command: "test_command2.0"

    - &job3
        name: "test_job3"
        node: *node1
        schedule: "constant"
        actions:
            - &actionConstant0
                name: "action3_0"
                command: "test_command3.0"
            - &actionConstant1
                name: "action3_1"
                command: "test_command3.1"
            - &actionFollow
                name: "action3_2"
                node: *node0
                command: "test_command3.2"
                requires: [*actionConstant0, *actionConstant1]

    - &job4
        name: "test_job4"
        node: *nodePool
        all_nodes: True
        schedule: "daily"
        actions:
            - &actionDaily
                name: "action4_0"
                command: "test_command4.0"

services:
    -
        name: "service0"
        node: *nodePool
        command: "service_command0"
        count: 2
        pid_file: "/var/run/%(name)s-%(instance_number)s.pid"
        monitor_interval: 20
"""

    @setup
    def setup(self):
        self.test_dir = tempfile.mkdtemp()

    @teardown
    def teardown(self):
        shutil.rmtree(self.test_dir)

    def test_attributes(self):
        test_config = load_config(StringIO.StringIO(self.config))
        expected = TronConfig(
            working_dir='/tmp',
            syslog_address=None,
            command_context=FrozenDict(**{
                'python': '/usr/bin/python',
                'batch_dir': '/tron/batch/test/foo'
            }),
            ssh_options={'ciphers': None,
                         'macs': None,
                         'option': None,
                         'host-key-algorithms': None,
                         'user-authentications': None,
                         'noagent': 0,
                         'compress': 0,
                         'agent': True,
                         'known-hosts': None,
                         'user': None,
                         'reconnect': 0,
                         'logfile': None,
                         'port': None,
                         'identity': None,
                         'log': 0,
                         'nox11': 0,
                         'version': 0},
            notification_options=None,
            time_zone=None,
            nodes=FrozenDict(**{
                'batch0': ConfigNode(name='batch0', hostname='batch0'),
                'batch1': ConfigNode(name='batch1', hostname='batch1')
            }),
            node_pools=FrozenDict(**{
                'batch0_batch1': ConfigNodePool(nodes=['batch0', 'batch1'],
                                                name='batch0_batch1')
            }),
            jobs=FrozenDict(**{
                'test_job0': ConfigJob(
                    name='test_job0',
                    node='batch0',
                    schedule=ConfigIntervalScheduler(
                        timedelta=datetime.timedelta(0, 20)),
                    actions=FrozenDict(**{
                        'action0_0': ConfigAction(
                            name='action0_0',
                            command='test_command0.0',
                            requires=(),
                            node=None)
                    }),
                    queueing=True,
                    run_limit=50,
                    all_nodes=False,
                    cleanup_action=ConfigAction(
                        name='cleanup_action',
                        command='test_command0.1',
                        requires=(),
                        node=None)),
                'test_job1': ConfigJob(
                    name='test_job1',
                    node='batch0',
                    schedule=ConfigDailyScheduler(
                        start_time='00:30:00', days='MWF'),
                    actions=FrozenDict(**{
                        'action1_1': ConfigAction(
                            name='action1_1',
                            command='test_command1.1',
                            requires=('command', 'name'),
                            node=None),
                        'action1_0': ConfigAction(
                            name='action1_0',
                            command='test_command1.0',
                            requires=(),
                            node=None)
                    }),
                    queueing=True,
                    run_limit=50,
                    all_nodes=False,
                    cleanup_action=None),
                'test_job2': ConfigJob(
                    name='test_job2',
                    node='batch1',
                    schedule=ConfigDailyScheduler(
                        start_time='16:30:00', days=None),
                    actions=FrozenDict(**{
                        'action2_0': ConfigAction(
                            name='action2_0',
                            command='test_command2.0',
                            requires=(),
                            node=None)
                    }),
                    queueing=True,
                    run_limit=50,
                    all_nodes=False,
                    cleanup_action=None),
                'test_job3': ConfigJob(
                    name='test_job3',
                    node='batch1',
                    schedule=ConfigConstantScheduler(),
                    actions=FrozenDict(**{
                        'action3_1': ConfigAction(
                            name='action3_1',
                            command='test_command3.1',
                            requires=(),
                            node=None),
                        'action3_0': ConfigAction(
                            name='action3_0',
                            command='test_command3.0',
                            requires=(),
                            node=None),
                        'action3_2': ConfigAction(
                            name='action3_2',
                            command='test_command3.2',
                            requires=('action3_0', 'action3_1'),
                            node='batch0')
                    }),
                    queueing=True,
                    run_limit=50,
                    all_nodes=False,
                    cleanup_action=None),
                'test_job4': ConfigJob(
                    name='test_job4',
                    node='batch0_batch1',
                    schedule=ConfigDailyScheduler(start_time=None, days=None),
                    actions=FrozenDict(**{
                        'action4_0': ConfigAction(
                            name='action4_0',
                            command='test_command4.0',
                            requires=(),
                            node=None)}),
                    queueing=True,
                    run_limit=50,
                    all_nodes=True,
                    cleanup_action=None)
                }),
                services=FrozenDict(**{
                    'service0': ConfigService(
                        name='service0',
                        node='batch0_batch1',
                        pid_file='/var/run/%(name)s-%(instance_number)s.pid',
                        command='service_command0',
                        monitor_interval=20,
                        restart_interval=None,
                        count=2)
                }
            )
        )

        assert_equal(test_config, expected)


class BadJobConfigTest(TestCase):
    @setup
    def build_env(self):
        self.test_dir = tempfile.mkdtemp()

    def test_no_actions(self):
        test_config = BASE_CONFIG + """
jobs:
    -
        name: "test_job0"
        node: node0
        schedule: "interval 20s"
        """
        assert_raises(ConfigError, load_config, test_config)

    def test_empty_actions(self):
        test_config = BASE_CONFIG + """
jobs:
    -
        name: "test_job0"
        node: node0
        schedule: "interval 20s"
        actions:
        """
        assert_raises(ConfigError, load_config, test_config)

    def test_dupe_names(self):
        test_config = BASE_CONFIG + """
jobs:
    -
        name: "test_job0"
        node: node0
        schedule: "interval 20s"
        actions:
            -
                name: "action0_0"
                command: "test_command0.0"
            -
                name: "action0_0"
                command: "test_command0.0"

        """
        assert_raises(ConfigError, load_config, test_config)

    def test_bad_requires(self):
        test_config = BASE_CONFIG + """
jobs:
    -
        name: "test_job0"
        node: node0
        schedule: "interval 20s"
        actions:
            -
                name: "action0_0"
                command: "test_command0.0"
            - &action0_1
                name: "action0_1"
                command: "test_command0.1"

    -
        name: "test_job1"
        node: node0
        schedule: "interval 20s"
        actions:
            -
                name: "action1_0"
                command: "test_command1.0"
                requires: action0_0

        """
        assert_raises(ConfigError, load_config, test_config)

    def test_config_cleanup_name_collision(self):
        test_config = BASE_CONFIG + """
jobs:
    -
        name: "test_job0"
        node: node0
        schedule: "interval 20s"
        actions:
            -
                name: "%s"
                command: "test_command0.0"

        """ % CLEANUP_ACTION_NAME
        assert_raises(ConfigError, load_config, test_config)

    def test_config_cleanup_name(self):
        test_config = BASE_CONFIG + """
jobs:
    -
        name: "test_job0"
        node: node0
        schedule: "interval 20s"
        actions:
            -
                name: "action0_0"
                command: "test_command0.0"
        cleanup_action:
            name: "gerald"
            command: "test_command0.1"
        """
        assert_raises(ConfigError, load_config, test_config)

    def test_config_cleanup_requires(self):
        test_config = BASE_CONFIG + """
jobs:
    -
        name: "test_job0"
        node: node0
        schedule: "interval 20s"
        actions:
            -
                name: "action0_0"
                command: "test_command0.0"
        cleanup_action:
            command: "test_command0.1"
            requires: [action0_0]
        """
        assert_raises(ConfigError, load_config, test_config)

    def test_job_in_services(self):
        test_config = BASE_CONFIG + """
services:
    -
        name: "test_job0"
        node: node0
        schedule: "interval 20s"
        actions:
            -
                name: "action0_0"
                command: "test_command0.0"
        cleanup_action:
            command: "test_command0.1"
"""
        assert_raises(ConfigError, load_config, test_config)

if __name__ == '__main__':
    run()

