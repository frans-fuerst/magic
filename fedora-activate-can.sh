#!/usr/bin/env bash

set -e

KERNEL_VERSION_ARCH=$(uname -r)
KERNEL_VERSION=$(uname -r | cut -d '.' -f 1-4)
KERNEL_SHORT_VERSION=$(uname -r | cut -d '.' -f 1-2)
KERNEL_DIST_VERSION=$(uname -r | cut -d '.' -f 4)
KERNEL_ARCH=$(uname -m)
EXTRAVERSION="-$(uname -r | cut -d '-' -f 2)"
KERNEL_RPM_NAME="kernel-$KERNEL_VERSION.src.rpm"

set -x

# catch sudo privileges
sudo echo $USER

rm -rf rpmbuild
mkdir -p .oldkernels
find . -maxdepth 1 -name kernel-\*.rpm -type f -exec mv '{}' .oldkernels/ \;

rpmdev-setuptree

if [ -e .oldkernels/$KERNEL_RPM_NAME ]; then
    mv .oldkernels/$KERNEL_RPM_NAME .
else
    yumdownloader --source kernel
fi

if [ ! -e $KERNEL_RPM_NAME ]; then
    echo $KERNEL_RPM_NAME does not exist
    exit -1
fi

sudo yum-builddep $KERNEL_RPM_NAME

rpm -Uvh $KERNEL_RPM_NAME
mv $KERNEL_RPM_NAME .oldkernels

cd ~/rpmbuild/SPECS
rpmbuild -bp --target=$KERNEL_ARCH kernel.spec


cd ~/rpmbuild/BUILD/kernel-$KERNEL_SHORT_VERSION.$KERNEL_DIST_VERSION/linux-$KERNEL_VERSION_ARCH

pwd

sed -i "s%EXTRAVERSION =.*%EXTRAVERSION = $EXTRAVERSION%g" ./Makefile


cp /boot/config-$KERNEL_VERSION_ARCH .config
cp .config .config-backup

echo "" >> .config
echo "CONFIG_CAN=m" >> .config
echo "CONFIG_CAN_RAW=m" >> .config
echo "CONFIG_CAN_BCM=m" >> .config
echo "CONFIG_CAN_GW=m" >> .config
echo "CONFIG_CAN_VCAN=m" >> .config
echo "CONFIG_CAN_DEV=m" >> .config
echo "CONFIG_CAN_CALC_BITTIMING=y" >> .config
echo "CONFIG_CAN_PEAK_USB=m" >> .config

echo "# CONFIG_NET_EMATCH_CANID is not set" >> .config
echo "# CONFIG_CAN_SLCAN is not set" >> .config
echo "# CONFIG_CAN_LEDS is not set" >> .config
echo "# CONFIG_CAN_SJA1000 is not set" >> .config
echo "# CONFIG_CAN_C_CAN is not set" >> .config
echo "# CONFIG_CAN_M_CAN is not set" >> .config
echo "# CONFIG_CAN_CC770 is not set" >> .config
echo "# CONFIG_CAN_EMS_USB is not set" >> .config
echo "# CONFIG_CAN_ESD_USB2 is not set" >> .config
echo "# CONFIG_CAN_GS_USB is not set" >> .config
echo "# CONFIG_CAN_KVASER_USB is not set" >> .config
echo "# CONFIG_CAN_8DEV_USB is not set" >> .config
echo "# CONFIG_CAN_SOFTING is not set" >> .config
echo "# CONFIG_CAN_DEBUG_DEVICES is not set" >> .config

make modules_prepare

make M=net/can modules
make M=drivers/net/can modules

sudo make M=net/can modules_install
sudo make M=drivers/net/can modules_install
sudo depmod -a
sudo modprobe can
sudo modprobe vcan

