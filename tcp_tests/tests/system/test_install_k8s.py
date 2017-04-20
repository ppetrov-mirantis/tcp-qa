#    Copyright 2017 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import copy
import time

import pytest

from tcp_tests import settings
from tcp_tests.helpers import ext
from tcp_tests import logger
from tcp_tests.helpers import netchecker
LOG = logger.logger


@pytest.mark.deploy_k8s
class Testk8sInstall(object):
    """Test class for testing mcp10 vxlan deploy"""

    #salt_cmd = 'salt -l debug '  # For debug output
    #salt_call_cmd = 'salt-call -l debug '  # For debug output
    salt_cmd = 'salt --hard-crash --state-output=mixed --state-verbose=False '  # For cause only output
    salt_call_cmd = 'salt-call --hard-crash --state-output=mixed --state-verbose=False '  # For cause only output
    #salt_cmd = 'salt --state-output=terse --state-verbose=False '  # For reduced output
    #salt_call_cmd = 'salt-call --state-output=terse --state-verbose=False '  # For reduced output


    @pytest.mark.deploy_k8s
    def test_k8s_install(self, underlay, openstack_deployed,
                                     show_step):
        """Test for deploying an mcp environment and check it

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes

        """
        LOG.info("*************** DONE **************")

    @pytest.mark.deploy_k8s_calico
    def test_mcp11_k8s_calico_install(self, underlay, openstack_deployed,
                                       show_step):
        """Test for deploying an mcp environment and check it

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes

        """
        LOG.info("*************** DONE **************")


    @pytest.mark.deploy_k8s_calico
    def test_k8s_netchecker_calico(self, underlay, common_services_deployed,
                                   k8s_actions, config, show_step):
        """Test for deploying k8s environment with Calico plugin and check
           network connectivity between pods

        Scenario:
            1. Install k8s with Calico network plugin.
            2. Get network verification status. Check status is 'OK'.

        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8s_actions.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        netchecker.wait_check_network(config.k8s.kube_host, works=True)

    @pytest.mark.deploy_k8s_calico
    def test_k8s_netchecker(self, underlay,common_services_deployed,
                            k8s_actions, config, show_step):
        """Test for deploying an k8s environment with Calico and check
           connectivity between its networks

        Scenario:
            1. Install k8s.
            2. Get network verification status. Check status is 'OK'
            3. Randomly choose some k8s node, login to it via SSH, add blocking
               rule to the calico policy. Restart network checker server
            4. Get network verification status, Check status is 'FAIL'
            5. Recover calico profile state on the node
            6. Get network verification status. Check status is 'OK'

        Duration: 300 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8s_actions.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        netchecker.wait_running(config.k8s.kube_host, timeout=240)

        # STEP #2
        show_step(2)
        netchecker.wait_check_network(config.k8s.kube_host, works=True)

        # STEP #3
        show_step(3)
        target_node = underlay.get_random_node(list_range=[1, -1])
        netchecker.calico_block_traffic_on_node(underlay, target_node)

        # STEP #4
        show_step(4)
        netchecker.wait_check_network(config.k8s.kube_host, works=False)

        # STEP #5
        show_step(5)
        netchecker.calico_unblock_traffic_on_node(underlay, target_node)

        # STEP #6
        show_step(6)
        netchecker.wait_check_network(config.k8s.kube_host, works=True)

