---
title: Latest available Linux kernel
date: 2012-10-03
categories: [Kernel, Linux]
---

Here is how to obtain the latest available Linux kernel:

1. Go to [kernel.org](http://kernel.org), navigate till the directory containing the last kernel versions, up to today (Oct. 2012) it is pub/linux/kernel/v3.x. Go to the “testing” sub-directory and look for the latest patch available, in my case it is: patch-3.6-rc7.
2. Download the patch and the relative kernel, be aware that patch 3.6-rc7 is the 7th release candidate (rc) for the 3.6 kernel and the patch should be applied on top of the 3.5 kernel source, so that version is the one you need.

Following <http://www.kernel.org/doc/Documentation/applying-patches.txt>, here there are two examples of how to apply these patches.

An example of moving from 3.5 to 3.6-rc3:

```
$ cd ~/linux-3.5                    # change into the 3.5 source dir
$ patch -p1 < ../patch-3.6-rc3      # apply the 3.6-rc3 patch
$ cd ..; mv linux-3.5 linux-3.6-rc3 # rename the source dir
```

Now move from 3.6-rc3 to 3.6-rc5:

```
$ cd ~/linux-3.6-rc3                    # change into the 3.6-rc3 dir
$ patch -p1 -R < ../patch-3.6-rc3       # revert the 3.6-rc3 patch
$ patch -p1 < ../patch-3.6-rc5          # apply the new 3.6-rc5 patch
$ cd ..; mv linux-3.6-rc3 linux-3.6-rc5 # rename the source dir
```
