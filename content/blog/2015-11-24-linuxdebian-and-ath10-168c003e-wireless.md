---
title: Linux/Debian and ath10 168c:003e wireless
date: 2015-11-24
categories: [Debian, Drivers, Linux]
---

It took me a while to install properly the driver for the **Killer dual band Wireless 1525**. There are apparently different versions of it and some of the instructions online do not work with my version.

What I did:

- I put the newest driver available on [this site](https://github.com/kvalo/ath10k-firmware/pull/2) in my /lib/firmware/ath10k/QCA6174/
- I noticed that although I have a “1525” the kernel was trying to load the driver from the hw3.0 instead that from the hw2.1
- I made a

  ```
  ln -s firmware-4.bin firmware-5.bin
  ```

  in the hw3.0 directory as the kernel was looking for firmware-5.bin.
- At this point the driver loads but I had the problem that it just says: “failed to enable adaptive qcs: -11”. You can now read in the log “ath10k_pci 0000:03:00.0: qca6174 hw3.2 (0x05030000, 0x00340aff, 168c:003e…”. Which might explain why hw2.1 and hw3.0 do not work.
- I got the file “/Windows/System32/drivers/eeprom_ar6320_3p0_NFA364xp.bin” from Windows 10 and I put it into the hw3.0 directory calling it “board.bin”.

The wireless finally works.

**Update**: with kernel 4.5.2 and following [these](https://bugs.launchpad.net/ubuntu/+source/linux-firmware/+bug/1520343) instructions the wifi works fairly easily.
