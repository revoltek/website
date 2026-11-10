---
title: Dropbox with Debian
date: 2012-06-17
categories: [Debian, Linux]
---

I am writing my thesis. This has created in me a kind of compulsory need of backupping every byte of it more or less every minute. One never knows when his laptop could catch fire, be eaten by a crocodile, be hit by a meteorite or all the other scenarios that one imagines while he is writing his thesis. When the time spent backupping overcomes the time spent writing, this is the time for Dropbox. So

```
apt-get install nautilus-dropbox
```

(The gripping story of the package is described [here](http://raphaelhertzog.com/2011/06/06/official-debian-ubuntu-packages-for-nautilus-dropbox/).)

Once installed:

```
$ dropbox
Dropbox command-line interface

Note: use dropbox help <command> to view usage for a specific command.

 status       get current status of the dropboxd
 help         provide help
 puburl       get public url of a file in your dropbox
 stop         stop dropboxd
 running      return whether dropbox is running
 update       download latest version of dropbox
 start        start dropboxd
 filestatus   get current sync status of one or more files
 ls           list directory contents with current sync status
 autostart    automatically start dropbox at login
 exclude      ignores/excludes a directory from syncing
 lansync      enables or disables LAN sync
```

The first time you will run `dropbox start` you will be prompted for your dropbox login and passwd and you will be able to choose a directory to be synchronized with your online repository. Now simply create a symbolic link (`ln -s`) into this directory to the directory of your thesis et voilà, automatic on-line backup of each word you write.

If you decide to create an account on dropbox, please use this link: <http://db.tt/Amx0X80c>, it doesn't cost anything and it will give me some extra space 🙂
