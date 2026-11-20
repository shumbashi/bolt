# Bolt 

Bolt is a command-line tool to help WHM system administrators quickly protect (lock) and un-protect (unlock) a Website public_html directory.

Bolt works by creating the necessary Apache config files and placing them in apache userdata folders, this includes generating a random password and reloading apache service. Placing those files outside the user account prevents the user from unlocking the website on his own.

Bolt also allows you to whitelist an IP address to be allowed to access a protected website without password authentication.

Developed by: [Libyan Spider](https://libyanspider.com)
License:Apache License Version 2.0

## Installation

```
cd ~
wget https://github.com/shumbashi/bolt/releases/download/v1.2/bolt_v1.2_linux_amd64 -O bolt_v1.2_linux_amd64
mv bolt_v1.2_linux_amd64 /usr/local/bin/bolt
chmod +x /usr/local/bin/bolt
```

## Build a Linux binary

From the repository root, run this with Docker Buildx installed:

```sh
docker buildx build --platform linux/amd64 --output type=local,dest=dist .
```

Set `__version__` in `bolt.py` when preparing a release. Use a version
of the form `MAJOR.MINOR.PATCH`. The build exports
`dist/bolt_v<VERSION>_linux_amd64` and verifies that the executable's
`--version` output matches its filename.
Copy that executable to `/usr/local/bin/bolt` on the target WHM server.
It bundles Python and its packages and targets x86-64 Linux with glibc 2.28
or newer. Bolt still uses the server's cPanel scripts, Apache, systemctl,
and htpasswd.

Run this build as root. It extracts its bundled libraries under `/run/user/0`
so it can start on hosts with a `noexec` temporary directory. The extraction
location is set at build time and takes precedence over `TMPDIR`. It must be
writable by root and on a filesystem that permits executable mappings.

## Usage

Run `bolt --version` to check the installed release.

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
  --version             Show the version and exit.
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

