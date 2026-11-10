---
title: Linux/Debian on a MacBook Air 7,2
date: 2015-12-07
categories: [Debian, Linux, Mac]
---

First of all let's do some safety moves:

- To be sure to have the right model on MacOS console just type `sysctl hw.model`
- Download the Recovery Disk Assistant from [here](https://support.apple.com/kb/DL1433?locale=en_US).
- Use a >1 GB USB key to create a bootable MacOS (the tool is very easy to use).

Now prepare the partition from MacOS:

- Open Disk Utility, go on the hard drive and press the “Partition” button, resize MacOS to ~200 GB (or what you want).
- A second partition of ~300 GB is created (assuming you have a 512 GB hard drive).

From a Linux box I created a bootable Debian (testing) USB stick, it's very easy and the procedure is [here](https://www.debian.org/releases/stable/i386/ch04s03.html.en). Reboot and press the “alt” button so to enter the EFI menu. Then choose to boot from the USB stick. Follow the initial standard procedure, add 8 GB of swap space and set up the other partitions (MacOS has 3 partitions set up: the EFI partition for booting, the system partition and a rescue partition, keep them untouched). Install GRUB by acknowledging that it might not work :). Reboot and linux should load properly, also X should immediately work.

Now let's install a nice & comfortable booting tool: rEFInd. Reboot and keep the “alt” button pressed, boot MacOS and download the last version of rEFInd [here](http://sourceforge.net/projects/refind/). rEFInd is extremely simple to install and saves a lot of headaches; in fact, it scans the EFI partition and makes all the images it finds “bootable” adding a nice interface for free. On the MacAir rEFInd complains that the SIP is active and it cannot proceed with the installation, reboot in safe mode (holding cmd+R), open a terminal and install rEFInd from there (it will still complain but you can ignore the warning and continue). rEFInd is also available for Linux [here](http://www.rodsbooks.com/refind/installing.html).

Now reboot in Debian from your new fancy rEFInd interface.

**Keyboard**

Fix the wrong keys (~ ` € and german characters) using this ~/.Xmodmap:

```
!! ~
keycode 94 = grave asciitilde
!! "
keycode 48 = apostrophe quotedbl

!! euro and german letters
keysym e = e E EuroSign
keysym b = b B ssharp
keysym u = u U udiaeresis Udiaeresis
keysym o = o O odiaeresis Odiaeresis
keysym a = a A adiaeresis Adiaeresis

!! mela
keycode 133 = Mode_switch
keycode 134 = Mode_switch
keycode 64 = Alt_L
keycode 108 = Alt_R

clear Mod1
add Mod1 = Alt_L Alt_R

clear mod2
add mod2 = Num_Lock

clear mod3
clear mod4
clear mod5
```

**WiFi**

You need to use the proprietary driver. Install the broadcom-sta-dkms deb, then do:

```
modprobe -r b44 b43 b43legacy ssb brcmsmac
modprobe wl
```

**Color profile**

If you want a much nicer color on your graphic interface just download [this](/media/CustomMacRumors.icc.gz) color profile and run `xcalib CustomMacRumors.icc`.

**Backlight**

Backlight was quite of a problem as the keyboard keys do not work out of the box and when the laptop is resumed from a suspend the backlight is set at the minimum. A solution is to use the kernel module gently provided [here](https://github.com/patjak/mba6x_bl). At the moment of writing the deb package that is on that site does not support kernel 4.3. I solved by downloading that deb and replacing the code with the last git version and repackaging it.

**Other stuff**

- Suspend seems to work fine
- also bluetooth as far as I can tell from the log but I haven't tested it yet.
- ~~The package “macchanger” helps avoiding the annoying log “ERROR @wl_cfg80211_get_station : Wrong Mac address”.~~ The problem seems to appear only in some networks.

[![Debian on the MacBook Air](/media/macbook-air.jpg){: .narrow }](/media/macbook-air.jpg)
