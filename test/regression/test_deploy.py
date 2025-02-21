#!/usr/bin/python3

import argparse
import re
import subprocess  # nosec
import sys

import yaml

from checker import Checker
from cluster import Cluster
from utils import Logger, StopWatch


def verify_pods_in_namespace(checker, namespace):
    cmd = ['kubectl', 'get', 'pods', '-n', namespace, '--no-headers']
    # nosec
    child = subprocess.Popen(cmd, stdout=subprocess.PIPE)  # nosec
    stdout = child.communicate()[0].decode('utf-8')
    expected_pods = {
        'cortx-control': 0,
        'cortx-data': 0,
        'cortx-ha': 0,
        'cortx-server': 0
        }

    for line in stdout.splitlines():
        podname, _ = line.split(None, 1)
        m = re.match(r'(cortx-[\w]+)', podname)
        if m:
            if m.group(1) in expected_pods:
                expected_pods[m.group(1)] += 1

    checker.test(expected_pods['cortx-control'] == 1,
                 f'Verify one cortx-control pod deployed in namespace {namespace}')
    checker.test(expected_pods['cortx-ha'] == 1,
                 f'Verify one cortx-ha pod deployed in namespace {namespace}')
    checker.test(expected_pods['cortx-data'] >= 1,
                 f'Verify at least one cortx-data pod deployed in namespace {namespace}')
    checker.test(expected_pods['cortx-server'] >= 1,
                 f'Verify at least one cortx-server pod deployed in namespace {namespace}')

def run_deploy_test(cluster, logger, checker, shutdown=False):

    sw = StopWatch()

    logger.logheader('Generated Solution File for Test')
    logger.logfile(cluster.solution_file)

    logger.log('\n\n')
    logger.logheader('-'*80)
    logger.logheader('\n\n')
    logger.logheader('\nRunning prereq-cortx-cloud.sh on each node\n')
    logger.logheader('\n\n')
    logger.logheader('-'*80)
    logger.log('\n\n')
    sw.start()
    result = cluster.run_prereq()
    sw.stop()
    checker.test_equal(0, result, 'Run prereq-cortx-cloud.sh')
    logger.log(f'TIMING: Prereq: {sw.elapsed():.0f}s', color=Logger.OKBLUE)

    logger.log('\n\n')
    logger.logheader('-'*80)
    logger.logheader('\n\n')
    logger.logheader('\nRunning deploy-cortx-cloud.sh\n')
    logger.logheader('\n\n')
    logger.logheader('-'*80)
    logger.log('\n\n')
    sw.start()
    result = cluster.deploy()
    sw.stop()
    checker.test_equal(0, result, 'Run deploy-cortx-cloud.sh')
    logger.log(f'TIMING: Deploy: {sw.elapsed():.0f}s', color=Logger.OKBLUE)


    # Verify cortx pods running in expected namespace
    namespace = cluster.solution['namespace']
    logger.log(subprocess.Popen(['kubectl', 'get', 'all', '-n', namespace],  # nosec
                                stdout=subprocess.PIPE)
                         .communicate()[0].decode('utf-8'))
    verify_pods_in_namespace(checker, namespace)

    logger.log('\n\n')
    logger.logheader('-'*80)
    logger.logheader('\n\n')
    logger.logheader('\nRunning status-cortx-cloud.sh\n')
    logger.logheader('\n\n')
    logger.logheader('-'*80)
    logger.log('\n\n')
    sw.start()
    result = cluster.status()
    sw.stop()
    checker.test_equal(0, result, 'Run status-cortx-cloud.sh')
    logger.log(f'TIMING: Status: {sw.elapsed():.0f}s', color=Logger.OKBLUE)

    if shutdown:
        logger.log('\n\n')
        logger.logheader('-'*80)
        logger.logheader('\n\n')
        logger.logheader('\nRunning shutdown-cortx-cloud.sh\n')
        logger.logheader('\n\n')
        logger.logheader('-'*80)
        logger.log('\n\n')
        sw.start()
        result = cluster.shutdown()
        sw.stop()
        checker.test_equal(0, result, 'Run shutdown-cortx-cloud.sh')
        logger.log(f'TIMING: Status: {sw.elapsed():.0f}s', color=Logger.OKBLUE)

        logger.log('\n\n')
        logger.logheader('-'*80)
        logger.logheader('\n\n')
        logger.logheader('\nRunning start-cortx-cloud.sh\n')
        logger.logheader('\n\n')
        logger.logheader('-'*80)
        logger.log('\n\n')
        sw.start()
        result = cluster.start()
        sw.stop()
        checker.test_equal(0, result, 'Run start-cortx-cloud.sh')
        logger.log(f'TIMING: Status: {sw.elapsed():.0f}s', color=Logger.OKBLUE)

        # Verify cortx pods running in expected namespace
        verify_pods_in_namespace(checker, namespace)

    logger.log('\n\n')
    logger.logheader('-'*80)
    logger.logheader('\n\n')
    logger.logheader('\nRunning destroy-cortx-cloud.sh\n')
    logger.logheader('\n\n')
    logger.logheader('-'*80)
    logger.log('\n\n')
    sw.start()
    result = cluster.destroy()
    sw.stop()
    checker.test_equal(0, result, 'Run destroy-cortx-cloud.sh')
    logger.log(f'TIMING: Destroy: {sw.elapsed():.0f}s', color=Logger.OKBLUE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', dest='cluster')
    parser.add_argument('-s', dest='solution')
    parser.add_argument('--namespace', dest='namespace')
    parser.add_argument('--shutdown', action='store_true')
    parser.add_argument('--logdir', dest='logdir', default='.')
    args = parser.parse_args()

    # Update namespace if specified
    cluster_file = args.cluster
    if args.namespace:
        with open(args.cluster) as f:
            cluster_data = yaml.safe_load(f)
        cluster_data['namespace'] = args.namespace
        cluster_file = f'{args.namespace}.' + args.cluster
        # Note: This creates a new config file that is
        # note deleted by this test.  I am ok with that.
        # I prefer this than deleting a file that I might
        # want to inspect after the test runs.
        with open(cluster_file, 'w') as f:
            yaml.dump(cluster_data, f)

    logger = Logger()
    checker = Checker(logger)
    cluster = Cluster(args.solution, cluster_file)
    run_deploy_test(cluster, logger, checker, args.shutdown)

    sys.exit(checker.result())
