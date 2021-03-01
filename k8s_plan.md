
+ Installer type is configured in @hardware_config decorator
	+ The installer receives the entire base_config object (which includes syntax like base_config.clusters.cluster1)
	+ There could be hosts which dont define installer_type and devops should skip over it


Devops plugins:
	+ devops_gravity_installer - receives naked VM and installs k8s (gravity)
	+ devops_k8s_installer - installs data layer (memsql, postgres... )
	+ core_k8s_installer - Calls functions from devops_k8s installer and install devops and core product on k8s



K8s flow:
+ invoke pytest with relevant plugins (devops_proxy_container, devops_proxy_pod, devops_docker_installer, devops_k8s_installer)
  + Invoking all these plugins is problematic.. we will need to design a way for the plugins to deploy themselves based on conditions which are specified in hardware_reqs decorator?
  + Maybe the plugins need to get a host instead of base_config? So that way there is a manager who sends each host to the hook individually?
    + the manager needs to be in devops_repo, ie - infra just inits base_config and cluster structure and calls pytest_after_base_config(base_config, request), and then devops has a main plugin which parses the hardware_reqs and sends each host to relevant init hook...
        + yea that seems to make more sense so it would iterate over the hosts in base_config and invoke the various installers on each of them (could happen in parallel) depending on config of hardware_reqs decorator...
+ provision machines based on decorator:
	@hardware_config(hardware={"host1": {"hardware_type": "ai_camera", "base_image": "regular", "installer": "camera", "gpus": 1},
	                           "host2": {"hardware_type": "vm", "base_image": "k8s_base", "installer": "k8s"},
	                           "host3": {"hardware_type": "vm", "base_image": "k8s_base", "installer": "bt"}},
	                 grouping={"cluster1": {"hosts": ["host1", "host2"]}})
     + The host dictionary in the hardware_config decorator will have to specify details for both provisioning and for installing (which will obv have defaults for backwards compatibility of current details):
        + hardware_type: ai_camera, vm... anything else?
        + base_image: ubuntu_clean, gravity_base, docker-compose, .. anything else?
        + installer_type: do we need to specify this? or can it be derived from hardware_type/base_image combination?
        + what will happen in pytest_after_base_config is
            + firstofall will call a hook to find more installers
            + will iterate over hosts and send each host to the relevant installer based on hardware_config decorator which appears in the request.session.items[0].__hardware_reqs
     + We will need to specify base_image in this decorator otherwise we may not get the VM we expect...
     + currently we need to invoke proxy_container and docker_installer together ie the installer relies on the container bc they are chained hooks.
     	+ would be a good idea to invoke devops_proxy_container automatically if devops_docker_installer is invoked, and then same for k8s installer bc the installer doesnt stand alone, it implements devops_proxy_container hooks so if devops_proxy_container isnt invoked installer will never be triggered....
+ build base_config
+ init cluster structure
+ after this we support the following syntax:
	host1 = base_config.hosts.host1
	cluster1 = base_config.clusters.cluster1
+ call pytest_after_base_config(base_config,request)
+ pytest_devops_infra will be the "main" devops plugin which implements pytest_after_base_config
    + it will iterate over hosts in base_config and send each host to its own relevant installer
    + after it does that it will call pytest_after_devops_installer which pytest_core_infra will implement
    + pytest_core_infra can send each host to relevant installer as well?
+ How do we handle clean_between_tests?
    + currently infra calls pytest_clean_between_tests(host, item) at the end of runtest_setup hook
    + devops_proxy_container implements this hook with tryfirst=True so it gets called before core conftests..
    + it could instead be implemented by "main" devops plugin (pytest_devops_infra) which could send to the relevant hook.. that wouldn't be that easy...
    + currently clean does host.clear_plugins() (among other things)...


./run/aws.sh -p pytest_subprocessor /path/to/test_folder --sf="-p pytest_devops_infra --install"



cluster1.kubectl.get_pods()
cluster1.Memsql.fetchall(query)


To run k8s test:
+ request to provisioner with specific base_image
    + base image will have gravity + infra layer
+ We get a machine
+ init base_config object
+ init cluster_structure - pytest structure, not cluster itself
+ after this we support the following syntax:
	host1 = base_config.hosts.host1
	cluster1 = base_config.clusters.cluster1
+ in order to init an actual k8s cluster, we need to start an initial machine, and then start the other machines and do a "join" operation, which takes ~5mins.
+ in order to deploy an actual cluster, from provisioning point of view we need to set AMI of 1 machine to an AMI which holds gravity base (the first one), and the others will be clean machines which afterwards join the cluster (may be different AMIs here as well for node type)
=======
devops_cluster_plugin plugin:
=======
+ Now we need to implement pytest plugin which will implement pytest_after_base_config and will actually configure k8s cluster according to hardware_config decorator.
    + in hardware_config decorator, we need to define roles for each machine in the cluster:
        + We will definitely have 1 gravity base which we will start from (who is also called master)
            + for gravity base:
              + if its a product tests (in order to save time) bc it was provisioned with the relevant AMI, the only thing to do is gravity change_ip and its ready
              + if its an installation test, we will need to provision a blank AMI and will need to run "1liner" to install (can take 1.5 hrs)
        + We can have 1 or more masters
            + sshdirect to gravity base to get ip and token of master
            + sshdirect execute gravity join in roll master
            + should only take ~5 mins
        + We can have 1 or more nodes, where each node can be 1 or more node types (memsql, postgres, pipe, seaweed)
            + sshdirect to gravity base to get ip and token of master
            + sshdirect execute gravity join with roll node (and node type)
            + sshdirect execute to node to label the node with whatever service it will be in the future (memsql, postgres, pipe, seaweed).
    + We will make template of standard cluster configurations which will cover most use cases for k8s cluster, for example:
        + AIO
        + HQ/HA - 3 masters
        + Master + 2 nodes of type pipe
================
At this point we have the machines provisioned, and the cluster set up in terms of kubernetes cluster. Rancher is up, from here on its rancher operations (via UI or CLI)
We have no services running, and therefore the logical "next step" is to deploy some service via rancher.
================
devops_k8s_installer plugin
===============
Install process:
    + base_config.clusters.cluster1.Rancher.install(bt_data)
    + base_config.clusters.cluster1.Memsql.install(bt_data)
    + Now I can run some memsql simple checks for example
    + base_config.clusters.cluster1.Rancher.install(bt_init)
    + I can check postgres/memsql schemas
    + base_config.clusters.cluster1.Rancher.install(bt_app)
    + You have a full running product
In order to init Rancher plugin, I need:
    + Ip:port (9443) - of master (or really of any node)
    + token - take it from kubectl command
This means I also need the kubectl plugin:
    + To init kubectl plugin:
        + we need to do 2 gravity operations, so we need gravity plugin:
To init Gravity plugin:
    + sshdirect execute to master node gravity command which adds master_ip to gravity auth gateway
    + get username/password detail via SshDirect command: gravity exec kubectl get-secret...
    + tsh login (gravity cli command) with ip:port of master node and username(admin)/password(kubectl get-secret)
        + this command creates ~/.kube/config file (or any other saved path and then specify location with --kubeconfig flag )
+ Once we did the gravity init plugin, we can create the kubectl because we have the kubeconfig file.


### v3 run tests command:
./containerize.sh python -m pytest -p pytest_subprocessor --sf=\"-p pytest_automation_infra -p pytest_devops_infra --install\" -s 
automation/devops_automation_infra/tests/test_temp.py

QUESTIONS:
+ do we feel comfortable leaving existing tests and conftests to function as they do? (devops and core tests?)
+ the pytest_devops_infra plugin will be in addition to the existing plugins and can be invoked instead of some of them in the use-case where we want to differentiate installation between hosts..
+ 

installers:
+ devops_docker - will setup proxy container, with --install flag will pull and up devops_docker_compose.yaml
+ core_docker - will setup proxy container, with --install flag will 
+ devops_k8s
+ core_k8s