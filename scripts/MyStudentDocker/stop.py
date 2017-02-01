#!/usr/bin/env python

# Filename: stop.py
# Description:
# This is the stop script to be run by the student.
# Note:
# 1. It needs 'start.config' file, where
#    <labname> is given as a parameter to the script.
# 2. If the lab has multiple containers and/or multi-home
#    networking, then <labname>.network file is necessary
#

import getpass
import os
import re
import subprocess
import sys
import zipfile
import ParseMulti
import ParseStartConfig

# Error code returned by docker inspect
SUCCESS=0
FAILURE=1

# CreateCopyChownZip
def CreateCopyChownZip(mycwd, start_config, container_name, container_image):
    container_user = start_config.container_user
    host_home_xfer = start_config.host_home_xfer
    lab_master_seed = start_config.lab_master_seed

    # Run 'Student.py' - This will create zip file of the result
    #print "About to call Student.py"
    bash_command = "'cd ; . .profile ; Student.py'"
    command = 'docker exec -it %s script -q -c "/bin/bash -c %s" /dev/null' % (container_name, bash_command)
    #print "Command to execute is (%s)" % command
    result = subprocess.call(command, shell=True)
    #print "CreateCopyChownZip: Result of subprocess.call exec Student.py is %s" % result
    if result == FAILURE:
        sys.stderr.write("ERROR: CreateCopyChownZip Container %s fail on executing Student.py!\n" % container_name)
        sys.exit(1)

    username = getpass.getuser()
    command='docker exec -it %s cat /home/%s/.local/zip.flist' % (container_name, container_user)
    #print "Command to execute is (%s)" % command
    child = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    zip_filelist = child.stdout.read().strip()
    #print "CreateCopyChownZip: Result of subprocess.Popen exec cat zip.flist is %s" % zip_filelist
    if zip_filelist == None:
        sys.stderr.write("ERROR: CreateCopyChownZip Container %s fail on executing cat zip.flist!\n" % container_name)
        sys.exit(1)

    command = "docker cp %s:%s /home/%s/%s" % (container_name, zip_filelist, username, host_home_xfer)
    #print "Command to execute is (%s)" % command
    result = subprocess.call(command, shell=True)
    #print "CreateCopyChownZip: Result of subprocess.Popen exec cp zip file is %s" % result
    if result == FAILURE:
        sys.stderr.write("ERROR: CreateCopyChownZip Container %s fail on executing cp zip file!\n" % container_name)
        sys.exit(1)

    # Change ownership to defined user $USER
    command = "sudo chown %s:%s /home/%s/%s*.zip" % (username, username, username, host_home_xfer)
    #print "Command to execute is (%s)" % command
    result = subprocess.call(command, shell=True)
    #print "CreateCopyChownZip: Result of subprocess.Popen exec chown zip file is %s" % result
    if result == FAILURE:
        sys.stderr.write("ERROR: CreateCopyChownZip Container %s fail on executing chown zip file!\n" % container_name)
        sys.exit(1)


# Stop my_container_name container
def StopMyContainer(mycwd, start_config, container_name):
    command = "docker stop %s 2> /dev/null" % container_name
    #print "Command to execute is (%s)" % command
    result = subprocess.call(command, shell=True)
    #print "Result of subprocess.call StopMyContainer stop is %s" % result
    return result

# Check to see if my_container_name container has been created or not
def IsContainerCreated(mycontainer_name):
    command = "docker inspect -f {{.Created}} %s 2> /dev/null" % mycontainer_name
    #print "Command to execute is (%s)" % command
    result = subprocess.call(command, shell=True)
    #print "Result of subprocess.call IsContainerCreated is %s" % result
    return result

def DoStopSingle(start_config, mycwd, labname):
    #print "Do: STOP Single Container with default networking"
    container_name = start_config.container_name
    container_image = start_config.container_image
    haveContainer = IsContainerCreated(container_name)
    #print "IsContainerCreated result (%s)" % haveContainer

    # IsContainerCreated returned FAILURE if container does not exists
    # error: can't stop non-existent container
    if haveContainer == FAILURE:
        sys.stderr.write("ERROR: DoStopSingle Container %s does not exist!\n" % container_name)
        sys.exit(1)
    else:
        # Before stopping a container, run 'Student.py'
        # This will create zip file of the result
        CreateCopyChownZip(mycwd, start_config, container_name, container_image)
        # Stop the container
        StopMyContainer(mycwd, start_config, container_name)

    return 0

def DoStopMultiple(start_config, mycwd, labname):
    container_user = start_config.container_user
    host_home_xfer = start_config.host_home_xfer
    lab_master_seed = start_config.lab_master_seed
    #print "Do: STOP Multiple Containers and/or multi-home networking"

    networkfilename = '%s/%s.network' % (mycwd, labname)
    multi_config = ParseMulti.ParseMulti(networkfilename)

    for mycontainer_name in multi_config.containers:
        mycontainer_image = multi_config.containers[mycontainer_name].container_image
        haveContainer = IsContainerCreated(mycontainer_name)
        #print "IsContainerCreated result (%s)" % haveContainer

        # IsContainerCreated returned FAILURE if container does not exists
        # error: can't stop non-existent container
        if haveContainer == FAILURE:
            sys.stderr.write("ERROR: DoStopMultiple Container %s does not exist!\n" % container_name)
            sys.exit(1)
        else:
            # Before stopping a container, run 'Student.py'
            # This will create zip file of the result
            CreateCopyChownZip(mycwd, start_config, mycontainer_name, mycontainer_image)
            # Stop the container
            StopMyContainer(mycwd, start_config, mycontainer_name)

    return 0

# Check existence of /home/$USER/$HOST_HOME_XFER directory - create if necessary
def CreateHostHomeXfer(host_xfer_dir):
    # remove trailing '/'
    host_xfer_dir = host_xfer_dir.rstrip('/')
    #print "host_home_xfer directory (%s)" % host_xfer_dir
    if os.path.exists(host_xfer_dir):
        # exists but is not a directory
        if not os.path.isdir(host_xfer_dir):
            # remove file then create directory
            os.remove(host_xfer_dir)
            os.makedirs(host_xfer_dir)
        #else:
        #    print "host_home_xfer directory (%s) exists" % host_xfer_dir
    else:
        # does not exists, create directory
        os.makedirs(host_xfer_dir)

# Usage: stop.py <labname>
# Arguments:
#    <labname> - the lab to stop
def main():
    #print "stop.py -- main"
    if len(sys.argv) != 2:
        sys.stderr.write("Usage: stop.py <labname>\n")
        sys.exit(1)
    
    labname = sys.argv[1]
    mycwd = os.getcwd()
    myhomedir = os.environ['HOME']
    #print "current working directory for %s" % mycwd
    #print "current user's home directory for %s" % myhomedir
    #print "ParseStartConfig for %s" % labname
    startconfigfilename = '%s/start.config' % mycwd
    start_config = ParseStartConfig.ParseStartConfig(startconfigfilename, labname)

    # Check existence of /home/$USER/$HOST_HOME_XFER directory - create if necessary
    host_xfer_dir = '%s/%s' % (myhomedir, start_config.host_home_xfer)
    CreateHostHomeXfer(host_xfer_dir)

    networkfilename = '%s/%s.network' % (mycwd, labname)
    # If <labname>.network exists, do multi-containers/multi-home networking
    # else do single container with default networking
    if not os.path.exists(networkfilename):
        DoStopSingle(start_config, mycwd, labname)
    else:
        DoStopMultiple(start_config, mycwd, labname)

    # Inform user where results are stored
    print "Results stored in directory: %s" % host_xfer_dir

    return 0

if __name__ == '__main__':
    sys.exit(main())

