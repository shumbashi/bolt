# Bolt 

Bolt is a command-line tool to help WHM system administrators quickly protect (lock) and un-protect (unlock) a Website public_html directory.

Bolt works by creating the necessary Apache config files and placing them in apache userdata folders, this includes generating a random password and reloading apache service. Placing those files outside the user account prevents the user from unlocking the website on his own.

Bolt also allows you to whitelist an IP address to be allowed to access a protected website without password authentication.

Developed by: [Libyan Spider](https://libyanspider.com)
License:Apache License Version 2.0

## Installation

```
cd ~
wget https://github.com/shumbashi/bolt/releases/download/v1.0/bolt_v1.0_linux_amd64 -O bolt_v1.0_linux_amd64
mv bolt_v1.0_linux_amd64 /usr/local/bin/bolt
chmod +x /usr/local/bin/bolt
```

## Usage

```
[root@server]# bolt --help

Usage: bolt.py [OPTIONS] COMMAND [ARGS]...

  Bolt is a command-line tool to help WHM system administrators quickly
  protect (lock) and un-protect (unlock) a Website public_html directory.

  Bolt works by creating the necessary Apache config files and placing them
  in apache userdata folders, this includes generating a random password and
  reloading apache service. Placing those files outside the user account
  prevents the user from unlocking the website on his own.

  Bolt also allows you to whitelist an IP address to be allowed to access a
  protected website without password authentication.

  Developed by: Libyan Spider

  License:BSD

  Documentation: https://github.com/shumbashi/bolt

Options:
  --debug / --no-debug  Enable verbose output
  --help                Show this message and exit.

Commands:
  lock       Protect (Lock) domain public_html directory
  status     Chekc domain locking status
  unlock     Remov Protection (Unlock) domain public_html directory
  whitelist  Whitelist IP Address for a protected (locked) domain

```

## Examples

### Check website status
```
[root@server]# bolt status mydomain.com

[+] Domain mydomain.com is UNLOCKED
```

### Protect (Lock) a website
```
[root@server]# bolt lock mydomain.com

[+] Domain mydomain.com is UNLOCKED
[+] Locking mydomain.com on port 80
[+] Locking mydomain.com on port 443
*************************************
[+] Username: mydomain
[+] Password: RANDOMPASSWORD
*************************************
```

### Whitelist an IP address for a locked website
```
[root@server]# bolt whitelist mydomain.com 10.22.33.44

[+] Whitelisting 11.22.33.44 for mydomain.com on port 80
[+] Whitelisting 11.22.33.44 for mydomain.com on port 443
```

### Remove Protection (Unlock) a locked website
```
[root@server]# bolt unlock mydomain.com

[+] Unlocking mydomain.com on port 80
[+] Unlocking mydomain.com on port 443
```

