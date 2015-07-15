#!/usr/bin/env python
import sys, os, commands
import argparse
from os import path


cur_path = os.getcwd()
orig_path = path.dirname(path.abspath(__file__))

mode = ['start', 'status', 'restart', 'stop']

DOCKER_BUILD_CMD = "docker build -t %(NAME)s ."
DOCKER_RUN_CMD = "docker run -p %(PORT)d:%(PORT)d --name %(NAME)s -d %(NAME)s %(CMD)s"
DOCKER_STOP_CMD = "docker kill %(NAME)s; docker rm %(NAME)s"

XINETD_CMD = "%(PRELOAD)s socat tcp-listen:%(PORT)d,fork,reuseaddr exec:%(BINARY)s"
FORK_CMD = "%(PRELOAD)s %(BINARY)s"

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

def main(m):
    if m == 'start':
        parser = argparse.ArgumentParser(description="auto container build tool for pwn")
        parser.add_argument('binary', metavar='binary', help='binary file of problem')
        parser.add_argument('-t', '--type', metavar='type', default='xinetd',
                help='specify binary type: [xinetd | fork-server] (default: fork-server)')
        parser.add_argument('-p', '--port', dest='port', metavar='port', 
                help='if here is blank, port would be assigned automatically')
        parser.add_argument('-f', '--flag', dest='flag', 
                metavar='flag_path', default='flag',
                help='default file name of flag is "flag"')
        parser.add_argument('-l', '--libc', dest='libc', metavar='libc_path',
                help='default libc depends on docker image')
        parser.add_argument('-n', '--name', dest='name', metavar='prob_name',
                help='specify unique name of problem (this would be used as docker container id and user name)')
        parser.add_argument('--template', dest='template', 
                metavar='template_name', default='standard', 
                help='template of Dockerfile (under %s/template/)'%(orig_path))
        parser.add_argument('-i', '--image', dest='image',
                metavar='docker_image', default='ubuntu:14.04',
                help='base image of Dockerfile (defualt: ubuntu:14.04)')

        args = parser.parse_args()

        binary = args.binary
        binary_name = path.basename(binary)
        flag = args.flag
        flag_name = path.basename(flag)
        libc = args.libc
        libc_name = None
        name = path.basename(binary)
        template = args.template
        image = args.image
        port = get_port()

        build_path = orig_path+"/build/"+name
        
        if not os.path.exists(orig_path+"/build")
            os.mkdir(orig_path+"/build")

        if os.system("docker ps | grep %s:latest"%(name)) == 0:
            print "%s is already running at port %s"%(name, open(build_path+"/port").read())
            sys.exit(1)

        if not os.path.exists(build_path):
            os.mkdir(build_path)

        if args.port:
            port = get_port(int(args.port))

        if args.name:
            name = args.name

        optional = ""

        if libc:
            libc_name = path.basename(libc)
            optional += "ADD %(libc)s /home/%(name)s/%(libc)s"%{
                    "libc": libc_name, "name": name}
            os.system('cp %(src)s %(dst)s'%{
                    "src": libc, "dst": build_path+"/"+libc_name})
            assert check_elf(libc) == check_elf(args.binary), "binary and libc has wrong bit mode"

        dockerfile = open(orig_path+'/template/'+template).read()%{
            "DOCKER_IMAGE": image,
            "BINARY": binary_name,
            "FLAG": flag_name,
            "USER": name,
            "PORT": port,
            "OPTIONAL_RUN": optional
        }

        libc_preload = ""
        if libc:
            libc_preload = "LD_PRELOAD=/home/%(name)s/%(libc)s "%{"name": name, "libc": libc_name}

        open(build_path+'/Dockerfile', 'w').write(dockerfile)
        open(build_path+'/port', 'w').write(str(port))
        os.system('cp %(src)s %(dst)s'%{
                "src": binary, "dst": build_path+"/"+binary_name})
        os.system('cp %(src)s %(dst)s'%{
                "src": flag, "dst": build_path+"/"+flag_name})

        os.chdir(build_path)
        assert os.system(DOCKER_BUILD_CMD%{"NAME": name}) == 0, "error: docker build"
        if args.type == 'xinetd':
            assert os.system(DOCKER_RUN_CMD%{
                    "NAME": name, "PORT": port, "CMD": libc_preload + XINETD_CMD%{
                            "PORT": port, "BINARY": "/home/"+name+"/"+binary_name,
                            "PRELOAD": libc_preload
                            }}) == 0, "error: docker run"
        elif args.type == 'fork-server':
            assert os.system(DOCKER_RUN_CMD%{
                    "NAME": name, "PORT": port, "CMD": libc_preload + FORK_CMD%{
                            "BINARY": "/home/"+name+"/"+binary_name,
                            "PRELOAD": libc_preload
                            }}) == 0, "error: docker run"

        print "%(NAME)s is runnning at port %(PORT)d"%{"NAME": name, "PORT": port}

    elif m == 'status':
        if len(sys.argv) < 2:
            print " ".join(['usage:', sys.argv[0], m, 'name'])
            sys.exit(1)

        name = sys.argv[1]
        build_path = orig_path+"/build/"+name

        if os.system("docker ps -a | grep %s"%(name)) == 0:
            print "%s is running at port %s"%(name, open(build_path+"/port").read())
        else:
            print "%s is not running"%(name)
        sys.exit(1)
        
    elif m == 'stop':
        binary = sys.argv[1]
        name = path.basename(binary)

        if os.system("docker ps -a | grep %s"%(name)) != 0:
            print "%s is not running"%(name)
            sys.exit(1)

        assert os.system(DOCKER_STOP_CMD%{"NAME": name}) == 0, "error: docker stop"
        print "stopped %(NAME)s"%{"NAME": name}


if len(sys.argv) >= 2 and sys.argv[1] in mode:
    m = sys.argv.pop(1)
    main(m)
    sys.exit(1)
else:
    print " ".join(['usage:', sys.argv[0], "["+"|".join(mode)+"]"])
    sys.exit(1)


