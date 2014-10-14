import logging
import os
import pipes
import random
import shutil
import string
import subprocess
import sys
import tempfile
import time
import urllib2
from optparse import OptionParser
from sys import stderr

no_of_slaves=int(sys.argv[2])
hadoop_major_version = str(sys.argv[3])
spark_version=str(sys.argv[4])
k=sys.argv[5]
key=str(k[0:len(k)-3]+"key")
service_name=str(sys.argv[1])

class UsageError(Exception):
    pass

def setup_cluster(master, slave,deploy_ssh_key):
    if deploy_ssh_key:
        print "Generating cluster's SSH key on master..."
        key_setup = """
          [ -f ~/.ssh/id_rsa ] ||
            (ssh-keygen -q -t rsa -N '' -f ~/.ssh/id_rsa &&
             cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys)
        """
        #print master
        #print slave
        ssh(master,key_setup)
        dot_ssh_tar = ssh_read(master, ['tar', 'c', '.ssh'])
        print "Transferring cluster's SSH key to slaves..."
        port=slave
        for sl in range(no_of_slaves):
            print sl
            ssh_write(port, ['tar', 'x'], dot_ssh_tar)
            port=int(port)+11
            port=str(port)
    modules = ['spark', 'shark', 'ephemeral-hdfs', 'persistent-hdfs',
        'mapreduce', 'spark-standalone', 'tachyon']
    if hadoop_major_version == "1":
        modules = filter(lambda x: x != "mapreduce", modules)
    # NOTE: We should clone the repository before running deploy_files to
    # prevent ec2-variables.sh from being overwritten
    ssh(master,"wget https://s3.amazonaws.com/sigmoidanalytics-data/Azure-spark.tar.gz")
    ssh(master,"tar -xzf Azure-spark.tar.gz")
    print "Deploying files to master..."
    deploy_files("deploy.generic", master, slave, modules)
    ssh(master, "mkdir root && cp -r /home/sigmoid/:/root/spark-ec2 /home/sigmoid/root/")
    ssh(master, "export JAVA_HOME=/usr/lib/jvm/java-7-openjdk-amd64")
    print "Deploying done!"
    print "Running setup on master..."
    setup_spark_cluster(master)
    print "Done!"
    
def setup_spark_cluster(master):
    ssh(master,"chmod u+x spark-ec2/setup.sh")
    ssh(master,"spark-ec2/setup.sh")
    print "Spark standalone cluster started at http://%s:8080" % service_name+".cloudapp.net"
    
def deploy_files(root_dir,master, slave, modules):
    hdfs_data_dirs = "/mnt/hadoop"
    mapred_local_dirs = "/mnt/hadoop/mrlocal"
    spark_local_dirs = "/mnt/spark"
    cluster_url = "%s:7077" % service_name+".cloudapp.net"
    spark_v = spark_version
    shark_v = ""
    sl=""
    for i in range(no_of_slaves):
        i=i+2
        sl+=service_name+"-"+str(i)+" "
    sl=sl[0:len(sl)-1]
    modules = filter(lambda x: x != "shark", modules)
    template_vars = {
        "master_list": service_name,
        "active_master": service_name,
        "slave_list": sl,
        "cluster_url": cluster_url,
        "hdfs_data_dirs": hdfs_data_dirs,
        "mapred_local_dirs": mapred_local_dirs,
        "spark_local_dirs": spark_local_dirs,
        "modules": '\n'.join(modules),
        "spark_version": spark_v,
        "shark_version": shark_v,
        "hadoop_major_version": hadoop_major_version,
    }
    tmp_dir = tempfile.mkdtemp()
    for path, dirs, files in os.walk(root_dir):
        if path.find(".svn") == -1:
            dest_dir = os.path.join('/', path[len(root_dir):])
            local_dir = tmp_dir + dest_dir
            if not os.path.exists(local_dir):
                os.makedirs(local_dir)
            for filename in files:
                if filename[0] not in '#.~' and filename[-1] != '~':
                    dest_file = os.path.join(dest_dir, filename)
                    local_file = tmp_dir + dest_file
                    with open(os.path.join(path, filename)) as src:
                        with open(local_file, "w") as dest:
                            text = src.read()
                            for key in template_vars:
                                text = text.replace("{{" + key + "}}", template_vars[key])
                            dest.write(text)
                            dest.close()
        # rsync the whole directory over to the master machine
    command = [
        'rsync', '-rv',
        '-e', stringify_command(ssh_command(master)),
        "%s/" % tmp_dir,
        "%s@%s:/" % ("sigmoid", service_name+".cloudapp.net:/home/sigmoid/")
    ]
    subprocess.check_call(command)
    # Remove the temp directory we created above
    shutil.rmtree(tmp_dir)

    
def stringify_command(parts):
    if isinstance(parts, str):
        return parts
    else:
        return ' '.join(map(pipes.quote, parts))


def ssh_args(port):
    parts = ['-o', 'StrictHostKeyChecking=no']
    parts += ['-i', key]
    parts += ['-p', port]
    return parts


def ssh_command(port):
    return ['ssh'] + ssh_args(port)

def ssh_read(port,command):
    return _check_output(
        ssh_command(port) + ['%s@%s' % ("sigmoid", service_name+".cloudapp.net"), stringify_command(command)])
    

# Run a command on a host through ssh, retrying up to five times
# and then throwing an exception if ssh continues to fail.
def ssh(port, command):
    tries = 0
    while True:
        try:
            return subprocess.check_call(
                ssh_command(port) + ['-t', '-t', '%s@%s' % ("sigmoid", service_name+".cloudapp.net"),
                                     stringify_command(command)])
        except subprocess.CalledProcessError as e:
            if tries > 5:
                # If this was an ssh failure, provide the user with hints.
                if e.returncode == 255:
                    raise UsageError(
                        "Failed to SSH to remote host {0}.\n" +
                        "Please check that you have provided the correct --identity-file and " +
                        "--key-pair parameters and try again.")
                else:
                    raise e
            print >> stderr, \
                "Error executing remote command, retrying after 30 seconds: {0}".format(e)
            time.sleep(30)
            tries = tries + 1
            
def ssh_write(port, command, arguments):
    tries = 0
    while True:
        proc = subprocess.Popen(
            ssh_command(port) + ['%s@%s' % ("sigmoid", service_name+".cloudapp.net"), stringify_command(command)],
            stdin=subprocess.PIPE)
        proc.stdin.write(arguments)
        proc.stdin.close()
        status = proc.wait()
        if status == 0:
            break
        elif tries > 5:
            raise RuntimeError("ssh_write failed with error %s" % proc.returncode)
        else:
            print >> stderr, \
                "Error {0} while executing remote command, retrying after 30 seconds".format(status)
            time.sleep(30)
            tries = tries + 1
            
# Backported from Python 2.7 for compatiblity with 2.6 (See SPARK-1990)
def _check_output(*popenargs, **kwargs):
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
    output, unused_err = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        raise subprocess.CalledProcessError(retcode, cmd, output=output)
    return output

def real_main():
    master_nodes="22"
    slave_nodes="44"
    setup_cluster(master_nodes, slave_nodes, True)

def main():
    try:
        real_main()
    except UsageError, e:
        print >> stderr, "\nError:\n", e
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig()
    main()

