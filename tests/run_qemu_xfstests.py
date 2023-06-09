import pexpect
import sys
import re
import os

CONFIG = os.environ.get('CONFIG')
FS_TYPE = os.environ.get('FS_TYPE')
TESTPATH = f"fs/xfstests.py.data/{FS_TYPE}/{CONFIG}"

if (CONFIG == None or FS_TYPE == None):
    print(f"Usage: sudo FS_TYPE={FS_TYPE} CONFIG={CONFIG} python3 tests/run_qemu_xfstests.py")
    exit(1);

print(f"environ: FS: {FS_TYPE} with CONFIG: {CONFIG}, TESTPATH: {TESTPATH}")

#url = 'https://cloud-images.ubuntu.com/focal/current/focal-server-cloudimg-amd64.img'
#local_filename = 'focal-server-cloudimg-amd64.img'
#
#response = requests.get(url, stream=True)
#response.raise_for_status()  # Raise an exception if the download failed
#
#total_size = int(response.headers.get('content-length', 0))
#chunk_size = 8192
#
#with open(local_filename, 'wb') as f:
#    for chunk in tqdm(response.iter_content(chunk_size=chunk_size), total=total_size // chunk_size, unit='KB'):
#        f.write(chunk)

# Change this to the path of your downloaded Ubuntu cloud image
cloud_image_path = './jammy-server-cloudimg-amd64.img'

#                 -device virtio-net,netdev=vmnic \
#                 -netdev user,id=vmnic,hostfwd=tcp::12125-:22 \

if (not os.path.exists('/tmp/results')):
    os.mkdir('/tmp/results/')

# Create a pexpect object to run the QEMU command
qemu_command = f'''qemu-system-x86_64 \
                 -enable-kvm \
                 -smp 2 \
                 -nographic \
                 -m 8192 \
                 -kernel arch/x86/boot/bzImage \
                 -drive file={cloud_image_path},format=qcow2 \
                 -drive file=user-data.img,format=raw \
                 -monitor telnet:127.0.0.1:55555,server,nowait -serial mon:stdio \
                 -serial telnet:127.0.0.1:1234,server,nowait \
                 -fsdev local,id=shared_test_dev,path=/tmp/results,security_model=none \
                 -device virtio-9p-pci,fsdev=shared_test_dev,mount_tag=host_shared \
	             -net nic,model=virtio -net user,hostfwd=tcp:127.0.0.1:2001-:22 \
                 -append "console=ttyS0,115200n8 root=/dev/sda1'''
child = pexpect.spawn(qemu_command, timeout=360000, encoding="utf-8")
child.logfile = sys.stdout


#patterns = ["VFS: Cannot open root device", "ubuntu login:"]

# Log in to the system
#matched_idx = child.expect(patterns)
#if matched_idx == 0:
#    print("Failed run")
#    exit(-1)
child.expect('ubuntu login:')
child.sendline('qemu')
child.expect('Password:')
child.sendline('123')
child.expect('qemu@ubuntu.*$')

child.sendline('sudo su')
child.expect('root@ubuntu.*#')

child.sendline('cd /root/')
child.expect('root@ubuntu.*#')

# Execute the commands
commands = ['ls', 'df -h', 'lsblk', 'mount', 'uname -a']
for command in commands:
    child.sendline(command)
    child.expect('root@ubuntu.*#')
    #print(f'Output of \'{command}\':')
    #print(child.before)

child.sendline("sudo apt -y remove needrestart unattended-upgrades")
child.expect('root@ubuntu.*#')
child.sendline("apt-get update")
child.expect('root@ubuntu.*#')

child.sendline("apt-get install -y python3 python3-pip")
child.expect('root@ubuntu.*#')

child.sendline("pip3 install --user avocado-framework avocado-framework-plugin-varianter-yaml-to-mux")

child.expect('root@ubuntu.*#')

child.sendline("pip3 install avocado-framework avocado-framework-plugin-varianter-yaml-to-mux")
child.expect('root@ubuntu.*#')

child.sendline("parted /dev/sda resizepart 1 100% && sudo resize2fs /dev/sda1")
child.expect('root@ubuntu.*#')


child.sendline("df -h")
child.expect('root@ubuntu.*#')

child.sendline("rm -rf avocado-misc-tests")
child.expect('root@ubuntu.*#')


child.sendline("mkdir host_shared")
child.expect('root@ubuntu.*#')

child.sendline("mount -t 9p -o trans=virtio host_shared host_shared -oversion=9p2000.L")
child.expect('root@ubuntu.*#')

child.sendline("git clone https://github.com/riteshharjani/avocado-misc-tests.git")
child.expect('root@ubuntu.*#')

child.sendline("cd avocado-misc-tests")
child.expect('root@ubuntu.*#')

child.sendline("bash -c 'echo 9 > /proc/sys/kernel/printk'")
child.expect('root@ubuntu.*#')

child.sendline(f"avocado --show test run --job-results-dir /root/host_shared/ fs/xfstests.py -m {TESTPATH}.yaml --max-parallel-tasks 1")
child.expect('root@ubuntu.*#')
#patterns = ['root@ubuntu.*#', 'Call Trace:']
#matched_idx = child.expect(patterns)
#if (matched_idx == 1):
#    print("Error: Call Trace printed")
#    sys.exit(1)

print(child.before)

match = re.search(r"JOB LOG\s*:\s*(.+)", child.before)
if match:
    job_log_path = match.group(1)
    print("Job log path:", job_log_path)
else:
    job_log_path = ""
    print("Job log path not found")

#child.sendline(f"cat {job_log_path}")
#child.expect('root@ubuntu.*#')

# Exit QEMU
child.sendline('sudo poweroff')
child.expect(pexpect.EOF)

