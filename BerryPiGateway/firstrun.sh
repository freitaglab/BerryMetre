#!/bin/bash

set +e

CURRENT_HOSTNAME=`cat /etc/hostname | tr -d " \t\n\r"`
if [ -f /usr/lib/raspberrypi-sys-mods/imager_custom ]; then
   /usr/lib/raspberrypi-sys-mods/imager_custom set_hostname berrygateway
else
   echo berrygateway >/etc/hostname
   sed -i "s/127.0.1.1.*$CURRENT_HOSTNAME/127.0.1.1\tberrygateway/g" /etc/hosts
fi
FIRSTUSER=`getent passwd 1000 | cut -d: -f1`
FIRSTUSERHOME=`getent passwd 1000 | cut -d: -f6`
if [ -f /usr/lib/raspberrypi-sys-mods/imager_custom ]; then
   /usr/lib/raspberrypi-sys-mods/imager_custom enable_ssh -k 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC3bS1yBxXUogUjJVkt6C3IaJ9S5jreHTqz1YAM2ZvxDqbe7moKTmjBSIPM9opm0X0jMmZbtPkpUlsk8LPj/iskZws40sFAuoLGwURR9GcXAySCTkssvASdyCjBVw8V9Shz9bdIbQUUDhbK1Thm/Iu3stBz9tzpIe2arclgcgYjlA29pd2V8uGYYg7eJklZ0v2HtQd6aGJXXThWPhnHFViCtTSMtnLI7Bfugjj0BjcWwtEW0N/PJLAlA9/QhW14WRa2+J8AT13UMtakl02gyYZb20dsLKO585QweGfRsOM7ccu/bXByZyOKO2l4VqANcBb2IkmEIrfDfsm3Ue/5i9wq2mkk811Xc4IzdFVk0yZcljmN8507Zkz7ueM6qLYx5VNn99UJ7BAZxsfE409/uBE/thkVtr5xGV26uQ+ngH411p4PmbfgjZ5kuU0/wYM0uqOIGeg5LlXiNkexJgJTepMyTBLC1IL8Wx+gz3Xij9ylEnyLcYPTbN6Xqf7mTXTpXlNAilFrymsgSbeV8mAflFv3PiSOAm+0RBHEPXVqIi1eGHvZhO1jjUSMcCS+3tM+Vv15jugezQtpYQSw+MCtChAiZLGyCimlS0J4aTr3BEnG0Ncibl7B8RgLQ0gB+96IRwv7/VZ7S5IaZF5izTAkB8nkThaxHaQpxRk4MEwKj91lfQ== openpgp:0xCFDB4528'
else
   install -o "$FIRSTUSER" -m 700 -d "$FIRSTUSERHOME/.ssh"
   install -o "$FIRSTUSER" -m 600 <(printf "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC3bS1yBxXUogUjJVkt6C3IaJ9S5jreHTqz1YAM2ZvxDqbe7moKTmjBSIPM9opm0X0jMmZbtPkpUlsk8LPj/iskZws40sFAuoLGwURR9GcXAySCTkssvASdyCjBVw8V9Shz9bdIbQUUDhbK1Thm/Iu3stBz9tzpIe2arclgcgYjlA29pd2V8uGYYg7eJklZ0v2HtQd6aGJXXThWPhnHFViCtTSMtnLI7Bfugjj0BjcWwtEW0N/PJLAlA9/QhW14WRa2+J8AT13UMtakl02gyYZb20dsLKO585QweGfRsOM7ccu/bXByZyOKO2l4VqANcBb2IkmEIrfDfsm3Ue/5i9wq2mkk811Xc4IzdFVk0yZcljmN8507Zkz7ueM6qLYx5VNn99UJ7BAZxsfE409/uBE/thkVtr5xGV26uQ+ngH411p4PmbfgjZ5kuU0/wYM0uqOIGeg5LlXiNkexJgJTepMyTBLC1IL8Wx+gz3Xij9ylEnyLcYPTbN6Xqf7mTXTpXlNAilFrymsgSbeV8mAflFv3PiSOAm+0RBHEPXVqIi1eGHvZhO1jjUSMcCS+3tM+Vv15jugezQtpYQSw+MCtChAiZLGyCimlS0J4aTr3BEnG0Ncibl7B8RgLQ0gB+96IRwv7/VZ7S5IaZF5izTAkB8nkThaxHaQpxRk4MEwKj91lfQ== openpgp:0xCFDB4528") "$FIRSTUSERHOME/.ssh/authorized_keys"
   echo 'PasswordAuthentication no' >>/etc/ssh/sshd_config
   systemctl enable ssh
fi
if [ -f /usr/lib/userconf-pi/userconf ]; then
   /usr/lib/userconf-pi/userconf 'berrycells' '$5$/HC7xieWER$84Zb1ZL54vXVyCApVRNZfLN50HqhMtmqtHCqIqD61j1'
else
   echo "$FIRSTUSER:"'$5$/HC7xieWER$84Zb1ZL54vXVyCApVRNZfLN50HqhMtmqtHCqIqD61j1' | chpasswd -e
   if [ "$FIRSTUSER" != "berrycells" ]; then
      usermod -l "berrycells" "$FIRSTUSER"
      usermod -m -d "/home/berrycells" "berrycells"
      groupmod -n "berrycells" "$FIRSTUSER"
      if grep -q "^autologin-user=" /etc/lightdm/lightdm.conf ; then
         sed /etc/lightdm/lightdm.conf -i -e "s/^autologin-user=.*/autologin-user=berrycells/"
      fi
      if [ -f /etc/systemd/system/getty@tty1.service.d/autologin.conf ]; then
         sed /etc/systemd/system/getty@tty1.service.d/autologin.conf -i -e "s/$FIRSTUSER/berrycells/"
      fi
      if [ -f /etc/sudoers.d/010_pi-nopasswd ]; then
         sed -i "s/^$FIRSTUSER /berrycells /" /etc/sudoers.d/010_pi-nopasswd
      fi
   fi
fi
if [ -f /usr/lib/raspberrypi-sys-mods/imager_custom ]; then
   /usr/lib/raspberrypi-sys-mods/imager_custom set_keymap 'gb'
   /usr/lib/raspberrypi-sys-mods/imager_custom set_timezone 'Europe/London'
else
   rm -f /etc/localtime
   echo "Europe/London" >/etc/timezone
   dpkg-reconfigure -f noninteractive tzdata
cat >/etc/default/keyboard <<'KBEOF'
XKBMODEL="pc105"
XKBLAYOUT="gb"
XKBVARIANT=""
XKBOPTIONS=""

KBEOF
   dpkg-reconfigure -f noninteractive keyboard-configuration
fi
rm -f /boot/firstrun.sh
sed -i 's| systemd.run.*||g' /boot/cmdline.txt
exit 0
