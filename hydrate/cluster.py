"""Kubernetes Cluster API Class."""
from kubernetes import client, config
from .component import Component


class Cluster():
    """Define Cluster data and methods."""

    def __init__(self, kubeconfig):
        """Instantiate Cluster object.

        Args:
            kubeconfig: credential file for cluster

        """
        self.kubeconfig = kubeconfig
        self.apps_v1_api = None
        self.core_v1_api = None
        self.namespaced_pods = {}

    def connect_to_cluster(self):
        """Connect to the cluster. Set API attributes."""
        config.load_kube_config(self.kubeconfig)
        self.apps_v1_api = client.AppsV1Api()
        self.core_v1_api = client.CoreV1Api()

    def get_components(self):
        """Query the cluster for components.

        Returns:
            sorted dictionary of components in the cluster

        """
        components = []
        namespaces = self.get_namespaces()
        namespaces = self.remove_defaults(namespaces)
        # Scenario where cluster contains namespaces other than default ones
        if namespaces:
            components = [namespace for namespace in namespaces]
            components = [get_first_word(comp) for comp in components]
            components = [Component(name) for name in components]
        # Scenario where cluster applications all live in the default namespace
        else:
            pods = self.get_namespaced_pods("default")
            components = self.process_cluster_objects(pods)
        return components

    def get_namespaces(self):
        """Query the cluster for namespaces."""
        ret = self.core_v1_api.list_namespace()
        namespace_list = []
        for i in ret.items:
            namespace_list.append(i.metadata.name)
        return namespace_list

    def get_namespaced_pods(self, namespace):
        """Store the list of pods in the namespace.

        Args:
            namespace: The namespace to look in.

        Return:
            pod_list: list of pods found in the namespace.
        """
        if namespace in self.namespaced_pods:
            return self.namespaced_pods[namespace]
        else:
            namespaced_pods = self.core_v1_api.list_namespaced_pod(namespace)
            pod_list = []
            for i in namespaced_pods.items:
                pod_list.append(i.metadata.name)
            self.namespaced_pods[namespace] = pod_list
            return pod_list

    def get_pods_for_all_namespaces(self):
        """Return list of dicts of pod info.

        Returns:
            pod_list: list of dicts

        """
        pod_list = []
        ret = self.core_v1_api.list_pod_for_all_namespaces(watch=False)
        for i in ret.items:
            d = dict()
            d["ip"] = i.status.pod_ip
            d["name"] = i.metadata.name
            d["namespace"] = i.metadata.namespace
            pod_list.append(d)

        return pod_list

    def get_deployments_for_all_namespaces(self):
        """Return list of dicts of deployment info.

        Returns:
            deployment_list: list of dicts

        """
        deployment_list = []
        ret = self.apps_v1_api.list_deployment_for_all_namespaces(watch=False)
        for i in ret.items:
            d = dict()
            d["name"] = i.metadata.name
            d["namespace"] = i.metadata.namespace
            d["replicas"] = i.spec.replicas

            container_list = []
            for container in i.spec.template.spec.containers:
                container_list.append(container.image)

            d["containers"] = container_list
            deployment_list.append(d)

        return deployment_list

    def process_cluster_objects(self, object_list):
        """Process a list of kubernetes objects.

        Args:
            object_list: list of object names

        Returns:
            comp_list: component names sorted by value in desc. order

        """
        comp_list = count_first_word(object_list)
        comp_list = sort_dict_by_value(comp_list)
        # Take just the component name, not the frequency
        comp_list = [Component(component[0]) for component in comp_list]
        return comp_list

    def remove_defaults(self, namespaces):
        """Remove the default and kubernetes namespaces.

        Returns:
            ret_list: list of namespaces

        """
        ret_list = []
        ignore_set = {"default", "kube-public", "kube-system"}
        for namespace in namespaces:
            if namespace not in ignore_set:
                ret_list.append(namespace)
        return ret_list


def get_first_word(string, delimiter="-"):
    """Return the first word of a string, split by a delimiter.

    Args:
        string: string input
        delimiter: separator between words (default:"-")

    Returns:
        words[0]: first word of input string

    """
    words = string.split(delimiter)
    return words[0]


def count_first_word(str_list):
    """Count the first word of each string in the list.

    Args:
        str_list: List of strings

    Returns:
        list[(word, count), ...] sorted by value desc. order

    """
    ret_count = dict()
    for phrase in str_list:
        words = phrase.split("-")
        ret_count[words[0]] = ret_count.get(words[0], 0) + 1
    return ret_count


def sort_dict_by_value(d):
    """Sorts a dictionary by value.

    Args:
        d: Dictionary

    Returns:
        list: List of (key, value) sorted by value in descending order

    """
    return [(k, d[k]) for k in sorted(d, key=d.get, reverse=True)]
