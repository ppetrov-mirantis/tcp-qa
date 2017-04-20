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

from devops.helpers import helpers

import yaml
from tcp_tests import logger
from tcp_tests.managers.k8s import cluster

LOG = logger.logger


class K8SManager(object):
    """docstring for K8SManager"""

    __config = None
    __underlay = None

    def __init__(self, config, underlay):
        self.__config = config
        self.__underlay = underlay
        self._api_client = None
        super(K8SManager, self).__init__()

    @property
    def api(self):
        k8s_nodes = self.__underlay.node_names()
        self.__config.k8s.kube_host = self.__underlay.host_by_node_name(k8s_nodes[1])
        if self._api_client is None:
            self._api_client = cluster.K8sCluster(
                user=self.__config.k8s.kube_admin_user,
                password=self.__config.k8s.kube_admin_pass,
                host=self.__config.k8s.kube_host,
                default_namespace='netchecker')
        return self._api_client

    def get_pod_phase(self, pod_name, namespace=None):
        return self.api.pods.get(
            name=pod_name, namespace=namespace).phase

    def wait_pod_phase(self, pod_name, phase, namespace=None, timeout=60):
        """Wait phase of pod_name from namespace while timeout

        :param str: pod_name
        :param str: namespace
        :param list or str: phase
        :param int: timeout

        :rtype: None
        """
        if isinstance(phase, str):
            phase = [phase]

        def check():
            return self.get_pod_phase(pod_name, namespace) in phase

        helpers.wait(check, timeout=timeout,
                     timeout_msg='Timeout waiting, pod {pod_name} is not in '
                                 '"{phase}" phase'.format(
                                     pod_name=pod_name, phase=phase))

    def check_pod_create(self, body, namespace=None, timeout=300, interval=5):
        """Check creating sample pod

        :param k8s_pod: V1Pod
        :param namespace: str
        :rtype: V1Pod
        """
        LOG.info("Creating pod in k8s cluster")
        LOG.debug(
            "POD spec to create:\n{}".format(
                yaml.dump(body, default_flow_style=False))
        )
        LOG.debug("Timeout for creation is set to {}".format(timeout))
        LOG.debug("Checking interval is set to {}".format(interval))
        pod = self.api.pods.create(body=body, namespace=namespace)
        pod.wait_running(timeout=300, interval=5)
        LOG.info("Pod '{}' is created".format(pod.metadata.name))
        return self.api.pods.get(name=pod.metadata.name, namespace=namespace)

    def wait_pod_deleted(self, podname, timeout=60, interval=5):
        helpers.wait(
            lambda: podname not in [pod.name for pod in self.api.pods.list()],
            timeout=timeout,
            interval=interval,
            timeout_msg="Pod deletion timeout reached!"
        )

    def check_pod_delete(self, k8s_pod, timeout=300, interval=5,
                         namespace=None):
        """Deleting pod from k8s

        :param k8s_pod: fuel_ccp_tests.managers.k8s.nodes.K8sNode
        :param k8sclient: fuel_ccp_tests.managers.k8s.cluster.K8sCluster
        """
        LOG.info("Deleting pod '{}'".format(k8s_pod.name))
        LOG.debug("Pod status:\n{}".format(k8s_pod.status))
        LOG.debug("Timeout for deletion is set to {}".format(timeout))
        LOG.debug("Checking interval is set to {}".format(interval))
        self.api.pods.delete(body=k8s_pod, name=k8s_pod.name,
                             namespace=namespace)
        self.wait_pod_deleted(k8s_pod.name, timeout, interval)
        LOG.debug("Pod '{}' is deleted".format(k8s_pod.name))

    def check_service_create(self, body, namespace=None):
        """Check creating k8s service

        :param body: dict, service spec
        :param namespace: str
        :rtype: K8sService object
        """
        LOG.info("Creating service in k8s cluster")
        LOG.debug(
            "Service spec to create:\n{}".format(
                yaml.dump(body, default_flow_style=False))
        )
        service = self.api.services.create(body=body, namespace=namespace)
        LOG.info("Service '{}' is created".format(service.metadata.name))
        return self.api.services.get(name=service.metadata.name)

    def check_ds_create(self, body, namespace=None):
        """Check creating k8s DaemonSet

        :param body: dict, DaemonSet spec
        :param namespace: str
        :rtype: K8sDaemonSet object
        """
        LOG.info("Creating DaemonSet in k8s cluster")
        LOG.debug(
            "DaemonSet spec to create:\n{}".format(
                yaml.dump(body, default_flow_style=False))
        )
        ds = self.api.daemonsets.create(body=body, namespace=namespace)
        LOG.info("DaemonSet '{}' is created".format(ds.metadata.name))
        return self.api.daemonsets.get(name=ds.metadata.name)

    def check_ds_ready(self, dsname, namespace=None):
        """Check if k8s DaemonSet is ready

        :param dsname: str, ds name
        :return: bool
        """
        ds = self.api.daemonsets.get(name=dsname, namespace=namespace)
        return (ds.status.current_number_scheduled ==
                ds.status.desired_number_scheduled)

    def wait_ds_ready(self, dsname, namespace=None, timeout=60, interval=5):
        """Wait until all pods are scheduled on nodes

        :param dsname: str, ds name
        :param timeout: int
        :param interval: int
        """
        helpers.wait(
            lambda: self.check_ds_ready(dsname, namespace=namespace),
            timeout=timeout, interval=interval)

    def create_objects(self, path):
        if isinstance(path, str):
            path = [path]
        params = ' '.join(["-f {}".format(p) for p in path])
        cmd = 'kubectl create {params}'.format(params=params)
        with self.__underlay.remote(
                host=self.__config.k8s.kube_host) as remote:
            LOG.info("Running command '{cmd}' on node {node}".format(
                cmd=cmd,
                node=remote.hostname)
            )
            result = remote.check_call(cmd)
            LOG.info(result['stdout'])

    def set_dns(self, k8s_settings):
        if 'nameservers' not in k8s_settings and \
                self.__config.underlay.nameservers:
            k8s_settings['nameservers'] = self.__config.underlay.nameservers
            LOG.info('Added custom DNS servers to the settings: '
                     '{0}'.format(k8s_settings['nameservers']))
        if 'upstream_dns_servers' not in k8s_settings and \
                self.__config.underlay.upstream_dns_servers:
            k8s_settings['upstream_dns_servers'] = \
                self.__config.underlay.upstream_dns_servers
            LOG.info('Added custom upstream DNS servers (dnsmasq) to the '
                     'settings: {0}'.format(k8s_settings['nameservers']))

    def get_running_pods(self, pod_name, namespace=None):
        pods = [pod for pod in self.api.pods.list(namespace=namespace)
                if (pod_name in pod.name and pod.status.phase == 'Running')]
        return pods

    def get_pods_number(self, pod_name, namespace=None):
        pods = self.get_running_pods(pod_name, namespace)
        return len(pods)

    def get_running_pods_by_ssh(self, pod_name, namespace=None):
        with self.__underlay.remote(
                host=self.__config.k8s.kube_host) as remote:
            result = remote.check_call("kubectl get pods --namespace {} |"
                                       " grep {} | awk '{{print $1 \" \""
                                       " $3}}'".format(namespace,
                                                       pod_name))['stdout']
            running_pods = [data.strip().split()[0] for data in result
                            if data.strip().split()[1] == 'Running']
            return running_pods

    def get_pods_restarts(self, pod_name, namespace=None):
        pods = [pod.status.container_statuses[0].restart_count
                for pod in self.get_running_pods(pod_name, namespace)]
        return sum(pods)
