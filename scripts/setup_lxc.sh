#!/bin/bash

GITHUB_REPO_URL=""
GITHUB_TOKEN=""
TEMPLATE_VMID=200
STARTING_VMID=205
RUNNER_VERSION="v2.303.0"

for i in $(seq 0 3); do
  # Create a new LXC container based on the template
  VMID=$((STARTING_VMID + i))
  echo $VMID
  pct clone $TEMPLATE_VMID $VMID --hostname linux-ci-runner-$VMID
  pct set $VMID -cores 2 -memory 8192

  # Enable nesting and KVM support for the LXC container
  echo "features: nesting=1" >> /etc/pve/lxc/${VMID}.conf
  echo "lxc.cgroup2.devices.allow: c 10:232 rwm" >> /etc/pve/lxc/${VMID}.conf
#  echo 'lxc.hook.autodev: sh -c "modprobe tun; cd ${LXC_ROOTFS_MOUNT}/dev; mkdir net; mknod net/tun c 10 200; chmod 0666 net/tun"' >> /etc/pve/lxc/${VMID}.conf

  # Start the LXC container
  pct start $VMID

  # Install necessary software and configure the GitHub Actions runner
  pct exec $VMID -- /bin/bash -c "export DEBIAN_FRONTEND=noninteractive; apt-get update && apt-get -y upgrade && apt-get install -y curl git vim qemu-system-x86 cpu-checker"
  pct exec $VMID -- /bin/bash -c "curl -L https://github.com/actions/runner/releases/download/v2.303.0/actions-runner-linux-x64-2.303.0.tar.gz -o /root/runner.tar.gz"
  pct exec $VMID -- /bin/bash -c "mkdir /opt/actions-runner && tar -xzf /root/runner.tar.gz -C /opt/actions-runner && rm /root/runner.tar.gz"
  pct exec $VMID -- /bin/bash -c "cd /opt/actions-runner; export RUNNER_ALLOW_RUNASROOT=1; ./config.sh --url $GITHUB_REPO_URL --token $GITHUB_TOKEN --name linux-ci-runner-${VMID}"
  pct exec $VMID -- /bin/bash -c "cd /opt/actions-runner; export RUNNER_ALLOW_RUNASROOT=1; ./run.sh &"
  pct exec $VMID -- /bin/bash -c "echo 'export RUNNER_ALLOW_RUNASROOT=1' >> /etc/rc.local && chmod +x /etc/rc.local"
done
