#!/usr/bin/env python3
'''
This software was created by United States Government employees at 
The Center for Cybersecurity and Cyber Operations (C3O) 
at the Naval Postgraduate School NPS.  Please note that within the 
United States, copyright protection is not available for any works 
created  by United States Government employees, pursuant to Title 17 
United States Code Section 105.   This software is in the public 
domain and is not subject to copyright. 
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:
  1. Redistributions of source code must retain the above copyright
     notice, this list of conditions and the following disclaimer.
  2. Redistributions in binary form must reproduce the above copyright
     notice, this list of conditions and the following disclaimer in the
     documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
'''
import sys
import os
import argparse
sys.path.append('../scripts/labtainer-student/bin')
import RemoteBase
import LocalBase
import InspectLocalReg
import InspectRemoteReg
import LabtainerLogging
import ParseLabtainerConfig
'''
Force the test_registry named in labtainer.config to match the content of the
default registry, e.g., DockerHub.  NOTE: this is only intended to be run when
the premaster branch is broken an you want to return to clean premaster.  This
script should only be called from another script that coordinates that.
'''
def pull_push(image, remote_registry, local_registry):
    with_registry = '%s/%s' % (remote_registry, image)
    cmd = 'docker pull %s' % with_registry
    print(cmd)
    os.system(cmd)
    cmd = 'docker tag %s/%s %s/%s' % (remote_registry, image, local_registry, image)
    print(cmd)
    os.system(cmd)
    cmd = 'docker push %s/%s' % (local_registry, image)
    print(cmd)
    os.system(cmd)

def refreshLab(labdir, lab, role, remote_reg, local_reg, logger, no_copy):
    ''' force local to match remote '''
    docker_dir = os.path.join(labdir, lab, 'dockerfiles')
    if not os.path.isdir(docker_dir):
        return
    df_list = [f for f in os.listdir(docker_dir) if os.path.isfile(os.path.join(docker_dir, f))]
    for df in df_list:
        if df.endswith('.swp'):
            continue
        try:
            parts = df.split('.')
            image = '%s.%s.%s' % (parts[1], parts[2], role)
            container = parts[2]
        except:
            print('could not get image from %s' % df);
            continue
        with_reg = '%s/%s' % (remote_reg, image)
        remote_created, remote_user, remote_version, tag = InspectRemoteReg.inspectRemote(with_reg, logger, no_pull=True)

        if remote_created is not None:
            local_created, local_user, local_version, tag, base  = InspectLocalReg.inspectLocal(image, logger, local_reg)
            if local_created != remote_created:
                print('DIFFERENT: %s:%s local created/version %s/%s  remote: %s/%s' % (lab, container, local_created, 
                      local_version, remote_created, remote_version))
                logger.debug('DIFFERENT: %s:%s local created/version %s/%s  remote: %s/%s' % (lab, container, local_created, 
                      local_version, remote_created, remote_version))
                tags = InspectRemote.getTags(with_reg, token)
                pull_push(image, remote_reg, local_reg)
            else:
                logger.debug('refreshLab, no diff for %s' % image)
        else:
            print('ERROR, no remote info for image %s' % image)
            exit(1)

def updateLab(labdir, lab, role, remote_reg, local_reg, logger, no_copy):
    ''' push local lab containers to remote, i.e., as part of a release '''
    docker_dir = os.path.join(labdir, lab, 'dockerfiles')
    if not os.path.isdir(docker_dir):
        return
    df_list = [f for f in os.listdir(docker_dir) if os.path.isfile(os.path.join(docker_dir, f))]
    for df in df_list:
        if df.endswith('.swp'):
            continue
        try:
            parts = df.split('.')
            image = '%s.%s.%s' % (parts[1], parts[2], role)
            container = parts[2]
        except:
            print('could not get image from %s' % df);
            continue
        local_created, local_user, local_version, tag, base  = InspectLocalReg.inspectLocal(image, logger, local_reg)

        if local_created is not None:
            with_reg = '%s/%s' % (remote_reg, image)
            remote_created, remote_user, remote_version, tag = InspectRemoteReg.inspectRemote(with_reg, logger, no_pull=True)
            if local_created != remote_created:
                print('DIFFERENT: %s:%s local created/version %s/%s  remote: %s/%s' % (lab, container, local_created, 
                      local_version, remote_created, remote_version))
                logger.debug('DIFFERENT: %s:%s local created/version %s/%s  remote: %s/%s' % (lab, container, local_created, 
                      local_version, remote_created, remote_version))
                tags = InspectRemote.getTags(with_reg, token)
                pull_push(image, local_reg, remote_reg)
            else:
                logger.debug('updateLab, no diff for %s' % image)
        else:
            print('ERROR, no local info for image %s' % image)
            exit(1)


   
def doUpdateOrRefresh(local_registry, remote_registry, args, lgr): 
    ''' either push local images to remote registry (an update, which is the default), or pull remote images into local registry (refresh). '''
    if not args.quiet:
        if not args.refresh:
            msg = 'The will push images from the %s registry to the %s registry. Continue? (y/n)' % (local_registry, remote_registry)
        else:
            msg = 'The will push images from the %s registry to the %s registry. Continue? (y/n)' % (remote_registry, local_registry)
        confirm = str(input(msg)).lower().strip()
        if confirm != 'y':
            print('aborting')
            exit(1)

    if not args.refresh:
        os.system('docker login -u %s' % remote_registry)

    ldir = os.getenv('LABTAINER_DIR')
    if ldir is None:
        print('LABTAINER_DIR not defined.')
        exit(1)
    labdir = os.path.join(ldir, 'labs')
    if args.lab is not None:
        if not args.refresh:
            updateLab(labdir, args.lab, 'student', remote_registry, local_registry, lgr, args.no_copy)
        else:
            refreshLab(labdir, args.lab, 'student', remote_registry, local_registry, lgr, args.no_copy)
    else:
        grader = 'labtainer.grader'
        if not args.refresh:
            pull_push(grader, local_registry, remote_registry)
        else:
            pull_push(grader, remote_registry, local_registry)
        skip = []
        with open('skip-labs') as fh:
           for line in fh:
               f = os.path.basename(line).strip()
               print('will skip [%s]' % f)
               skip.append(f)
    
        #lab_list = os.listdir(labdir)
        lab_list = [x[0] for x in os.walk(labdir)]
        for lab in sorted(lab_list):
            if lab not in skip:
                if not args.refresh:
                    updateLab(labdir, lab, 'student', remote_registry, local_registry, lgr, args.no_copy)
                else:
                    refreshLab(labdir, lab, 'student', remote_registry, local_registry, lgr, args.no_copy)
    
        base_names = ['base', 'network', 'firefox', 'wireshark', 'java', 'centos', 'centos.xtra', 'lamp', 'lamp.xtra', 'kali', 'metasploitable']
        print('Comparing base images in %s to  %s, and replacing content of %s if different' % (local_registry, remote_registry, local_registry))
        for base in base_names:
            full = 'labtainer.%s' % (base)
            with_registry = '%s/labtainer.%s' % (remote_registry, base)
            print(full)
            remote_created, remote_user = RemoteBase.inspectRemote(with_registry, lgr)
            local_created, local_user = LocalBase.inspectLocal(full, lgr, local_registry)
            if remote_created != local_created:
                print('Difference in %s,  local: %s  remote: %s' % (full, local_created, remote_created))
                if not args.no_copy:
                    if not args.refresh:
                        pull_push(full, local_registry, remote_registry)
                    else:
                        pull_push(full, remote_registry, local_registry)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Compare base images and replace if different')
    parser.add_argument('-n', '--no_copy', action='store_true', default=False, help='Do not modify registry, just report differences')
    parser.add_argument('-r', '--refresh', action='store_true', default=False, help='Force mirror to match remote')
    parser.add_argument('-q', '--quiet', action='store_true', default=False, help='Do not prompt for confirmation')
    parser.add_argument('-l', '--lab', action='store', help='only check this lab')
    args = parser.parse_args()
    
    config_file = '../config/labtainer.config'
    labtainer_config = ParseLabtainerConfig.ParseLabtainerConfig(config_file, None)
    lgr = LabtainerLogging.LabtainerLogging("refresh_mirror.log", 'none', config_file)
    
    local_registry = labtainer_config.test_registry
    remote_registry = labtainer_config.default_registry
    doUpdateOrRefresh(local_registry, remote_registry, args, lgr)