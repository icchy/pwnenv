#!/usr/bin/env python
import os, commands
import argparse
from os import path



cur_path = os.getcwd()
orig_path = path.dirname(path.abspath(__file__))

DOCKER_BUILD_CMD = "docker build -t %(NAME)s ."
DOCKER_RUN_CMD = "docker run -p %(PORT)d:%(PORT)d --name %(NAME)s -d %(NAME)s %(CMD)s"
DOCKER_STOP_CMD = "docker kill %(NAME)s; docker rm %(NAME)s"

LAUNCH_CMD = "socat tcp-listen:%(PORT)d,fork,reuseaddr exec:%(BINARY)s"

CPU = None
BIT = None


def check_cmd():
    required = ['docker']
    for cmd in required:
        assert os.system('which '+cmd) == 0, "%(cmd)s not found."%{"cmd": cmd}

def check_elf(elfbin):
    res = commands.getoutput('file '+elfbin)
    if 'ELF 32-bit LSB' in res: # 32bit
        return 32
    elif 'ELF 64-bit LSB' in res: # 64bit
        return 64
    else:
        assert False, 'unsupported binary'

def get_port(begin=10000):
    for p in range(begin, 65535):
        if os.system('netstat -ant | grep :%d'%p):
            return p

parser = argparse.ArgumentParser(description="auto container build tool for pwn")
parser.add_argument('op', metavar='operation',
        help='[start | stop]')
parser.add_argument('binary', metavar='binary')

parser.add_argument('-p', '--port', dest='port', metavar='port', 
        help='if here is blank, port would be assigned automatically')
parser.add_argument('-f', '--flag', dest='flag', 
        metavar='flag_path', default='flag',
        help='default file name of flag is "flag"')
parser.add_argument('-l', '--libc', dest='libc', metavar='libc_path',
        help='default libc depends on docker image')
parser.add_argument('-n', '--name', dest='name', metavar='prob_name',
        help='specify unique name of problem (this would be used as docker container id)')
parser.add_argument('-t', '--template', dest='template', 
        metavar='template_name', default='standard', 
        help='template of Dockerfile')
parser.add_argument('-i', '--image', dest='image',
        metavar='docker_image', default='ubuntu:14.04',
        help='base image of Dockerfile (defualt: ubuntu:14.04)')

args = parser.parse_args()

if args.op == "start":
    binary = args.binary
    flag = args.flag
    libc = args.libc
    name = path.basename(binary)
    template_name = args.template
    image = args.image
    port = get_port()

    if args.port:
        port = get_port(int(args.port))

    if args.name:
        name = path.basename(args.name)


    BIT = check_elf(args.binary)

    optional = ""

    if libc:
        optional += "ADD %(libc)s /home/%(name)s/%(libc)s"%{
                "libc": path.basename(libc), "name": name}

    template = open(orig_path+'/template/'+template_name).read()%{
        "DOCKER_IMAGE": image,
        "BINARY": binary,
        "BINARY_NAME": path.basename(binary),
        "USER": name,
        "FLAG": flag,
        "PORT": port,
        "OPTIONAL_RUN": optional
    }

    libc_prefix = ""
    if libc:
        libc_prefix = "LD_PRELOAD=/home/%(name)/%(libc)s "%{"name": name, "libc": path.basename(libc)}

    open('Dockerfile', 'w').write(template)
    assert os.system(DOCKER_BUILD_CMD%{"NAME": name}) == 0, "error: docker build"
    assert os.system(DOCKER_RUN_CMD%{
            "NAME": name, "PORT": port, "CMD": libc_prefix + LAUNCH_CMD%{
                    "PORT": port, "BINARY": "/home/"+name+"/"+path.basename(binary)}}) == 0, "error: docker run"
    print "%(NAME)s is runnning at port %(PORT)d"%{"NAME": name, "PORT": port}

elif args.op == "stop":
    binary = args.binary
    name = path.basename(binary)
    os.system(DOCKER_STOP_CMD%{"NAME": name})
    print "stopped %(NAME)s"%{"NAME": name}
else:
    print "unsupported operation: %s"%(args.op)
    sys.exit(1)
