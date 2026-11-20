#!/usr/bin/python

import click
import os.path
from jinja2 import Template
import subprocess
import random
import string
import socket
import sys

__version__ = "1.3.1"

@click.group()
@click.version_option(__version__, prog_name="bolt")
@click.option('--debug/--no-debug', default=False, help="Enable verbose output")
def main(debug):
    """ Bolt is a command-line tool to help WHM system administrators quickly protect (lock) and un-protect (unlock) a Website public_html directory.

    Bolt works by creating the necessary Apache config files and placing them in apache userdata folders, this includes generating a random password and reloading apache service. Placing those files outside the user account prevents the user from unlocking the website on his own.

    Bolt also allows you to whitelist an IP address to be allowed to access a protected website without password authentication.

    Developed by: Libyan Spider

    License:BSD
    
    Documentation: https://github.com/shumbashi/bolt
    """
    global DEBUG
    DEBUG = debug
    if debug:
        click.echo('Debug mode is %s' % ('on'))

@main.command(help='Protect (Lock) domain public_html directory')
@click.argument('domain')
def lock(domain):
    s = Site(domain)
    s.lock()

@main.command(help='Remov Protection (Unlock) domain public_html directory')
@click.argument('domain')
def unlock(domain):
    s = Site(domain)
    s.unlock()

@main.command(help='Chekc domain locking status')
@click.argument('domain')
def status(domain):
    s = Site(domain)
    s.status()

@main.command(help='Whitelist IP Address for a protected (locked) domain public_html')
@click.argument('domain')
@click.argument('ip_address')
def whitelist(domain, ip_address):
    s = Site(domain, ip_address)
    s.whitelist()

class Site(object):
    
    def __init__(self, domain, ip_address=None):
        self.domain = domain
        self.ip_address = ip_address
        self.protocols = {'80': 'std', '443': 'ssl'}
        self.password = ''
        self.password_generated = False
        self.found_vhosts = self._parse_apache_config()
        self.locking_status = self._check_status()

    def _parse_apache_config(self):
        """Collect the requested domain's virtual hosts while reading httpd.conf once."""
        matches = []
        port = None
        try:
            with open("/etc/apache2/conf/httpd.conf", 'r') as config:
                for line in config:
                    if '#' in line:
                        continue
                    fields = line.split(None, 1)
                    if not fields:
                        continue
                    directive = fields[0].lower()
                    if directive == '<virtualhost' and len(fields) == 2:
                        address = fields[1].split()[0].rstrip('>')
                        port = address.rpartition(':')[2] if ':' in address else '*'
                        servername = documentroot = None
                    elif directive == '</virtualhost>':
                        if port is not None and servername == self.domain and documentroot:
                            matches.append({
                                'domain': servername,
                                'port': port,
                                'username': documentroot.split('/')[2],
                                'documentroot': documentroot,
                            })
                        port = None
                    elif port is not None and len(fields) == 2:
                        if directive == 'servername':
                            servername = fields[1].split()[0]
                        elif directive == 'documentroot':
                            documentroot = fields[1].strip().strip('"')
        except IOError:
            click.secho('[!] Unable to read apache config file /etc/apache2/conf/httpd.conf...exiting', fg='red')
            sys.exit(1)

        if not matches:
            click.secho("[!] Domain %s is not found in apache config... exiting!" % self.domain, fg='red')
            sys.exit(1)
        return matches

    def _check_status(self):
        """ Function to check if there is a bolt.conf file under the respective domain user data and then check if the file has the string 'Reuire valid-user' in it """
        if DEBUG:
            click.secho('[+] Checking current status for %s' % self.domain, fg='green')
        locked = {}
        for vhost in self.found_vhosts:
            protocol = 'std' if vhost['port'] == '80' else 'ssl'
            try:
                file = '/etc/apache2/conf.d/userdata/'+protocol+'/2_4/'+vhost['username']+'/'+vhost['domain']+'/bolt.conf'
                if DEBUG:
                    click.secho('[D] Opening file %s' % file, fg='yellow')
                if not os.path.isfile(file):
                    if DEBUG:
                        click.secho('[D] File %s not found' % file, fg='yellow')
                    locked[protocol] = False
                else: 
                    with open(file, 'r') as config:
                        locked[protocol] = any(
                            '#' not in line and 'Require valid-user' in line for line in config
                        )
            except Exception as e:
                raise e
        return locked

    def _generate_random_password(self):
        """ Function to generate a random string with lower case letters """
        length = 10
        letters = string.ascii_lowercase
        self.password = ''.join(random.choice(letters) for i in range(length))
        return self.password

    def _rebuild_httpd_config(self):
        """ Function to run rebuild httpd config command """
        command = "/scripts/rebuildhttpdconf"
        if DEBUG:
            click.secho('[D] Attempting to rebuild httpd config', fg='yellow')
        result,error  = subprocess.Popen(command, universal_newlines=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        if error:
            click.secho('[!] An error has occured while rebuilding apache config, please fix the issue and try again: %s' % error, fg='red')
            sys.exit(1)
        if DEBUG:
            click.secho('[D] %s' % result, fg='yellow')
        return

    def _apply_apache_changes(self):
        self._rebuild_httpd_config()
        self._reload_apache()

    def _reload_apache(self):
        """ Function to reload apache service """
        command = "/bin/systemctl reload httpd.service"
        if DEBUG:
            click.secho('[D] Attempting to reload Apache service', fg='yellow')
        result,error  = subprocess.Popen(command, universal_newlines=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        if error:
            click.secho('[!] An error has occured while reloading apache, please fix the issue and try again: %s' % error, fg='red')
            sys.exit(1)
        if DEBUG:
            click.secho('[D] Apache service restarted successfully', fg='yellow')
        return

    def _update_config_file(self,documentroot, protocol, username, domain):
        """ Function to create or update bolt.conf file and directories """
        generated_template = self._render_template(documentroot,protocol,username,domain)
        path = "/etc/apache2/conf.d/userdata/" + protocol + "/2_4/" + username +"/" + domain +"/bolt.conf"

        # create directory tree if needed
        command = "mkdir -p /etc/apache2/conf.d/userdata/" + protocol + "/2_4/" + username +"/" + domain
        result,error  = subprocess.Popen(command, universal_newlines=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        if error:
            click.secho('[!] An error has occured while creating directory tree: %s' % error, fg='red')
        else:
            if DEBUG:
                click.secho('[D] Attempting to write into config file %s' % path, fg='yellow')
            try:
                f = open(path, 'w+')
                f.write(generated_template)
                if DEBUG:
                    click.secho('[D] Updating config file successded', fg='yellow')
            except:
                click.secho('[!] An error occured. Unable to open file %s' % path, fg='red')
                sys.exit(1)
            finally:
                f.close()
        return

    def _truncate_config_file(self,documentroot, protocol, username, domain):
        """ Function to truncate bolt.conf file to unlock domain """
        path = "/etc/apache2/conf.d/userdata/" + protocol + "/2_4/" + username +"/" + domain +"/bolt.conf"
        if DEBUG:
            click.secho('[D] Attempting to write into config file %s' % path, fg='yellow')
        try:
            f = open(path, 'w+')
            f.write('')
            if DEBUG:
                click.secho('[D] Updating config file successded', fg='yellow')
        except:
            click.secho('[!] An error occured. Unable to open file %s' % path, fg='red')
            sys.exit(1)
        finally:
            f.close()
        return

    def _whitelist_ip(self,documentroot, protocol, username, domain, ip_address):
        """ Function to add a whitelisted IP address to bolt.conf file """
        path = "/etc/apache2/conf.d/userdata/" + protocol + "/2_4/" + username +"/" + domain +"/bolt.conf"
        if DEBUG:
            click.secho('[D] Attempting to write into config file %s' % path, fg='yellow')
        try:
            with open(path, "r+") as f:
                content = f.readlines()
                line = 'Require ip '+ ip_address + '\n'
                # insert line before second row from bottom
                content.insert(-2,line)
                content = "".join(content)
                f.seek(0)
                f.write(content)
                f.truncate()
            if DEBUG:
                click.secho('[D] Updating config file successded', fg='yellow')
        except:
            click.secho('[!] An error occured. Unable to write to file %s' % path, fg='red')
            raise
            sys.exit(1)
        return   
        
    def _validate_ip_address(self, ip_address):
        """ Function to return true if the provided string is a valid IPv4 address """
        if DEBUG:
            click.secho('[D] Validating IP Address %s' % ip_address, fg='yellow')
        try:
            socket.inet_aton(ip_address)
            if len(ip_address.split('.')) == 4:
                return True
            else:
                if DEBUG:
                    click.secho("[!] Provided string '%s' is invalid IP Address" % ip_address, fg='red')
                return False
        except:
            return False

    def _generate_password_file(self,documentroot, protocol, username, domain):
        """ Function that creates/updates htpasswd file """
        # Check if we already have a password generated
        if self.password:
            password = self.password
        else: 
            # Generate random password
            password = self._generate_random_password()
            self.password_generated = True
        command = "htpasswd -c -b /etc/apache2/conf.d/userdata/" + protocol + "/2_4/" + username +"/" + domain +"/passwd " + username + " " + password
        result,error  = subprocess.Popen(command, universal_newlines=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        if error and 'Adding password' not in error:
            click.secho('[!] An error occured while trying to generate passwd file: %s' % error, fg='red')
            sys.exit(1)
        if DEBUG:
            click.secho('[D] Created passwd file successfully', fg='yellow')
        return result

    def _render_template(self,documentroot, protocol, username, domain):
        """ Function to generate bolt.conf file based on a Jinja2 template """
        tempalte = Template('''<Directory "{{documentroot}}">
AuthType Basic
AuthName "Locked"
AuthUserFile "/etc/apache2/conf.d/userdata/{{protocol}}/2_4/{{username}}/{{domain}}/passwd"
Require valid-user
</Directory>
''')
        generated_template = tempalte.render(documentroot=documentroot, protocol=protocol, username=username, domain=domain)
        if DEBUG:
            click.secho('[D] Generating template successded', fg='yellow')
        return generated_template

    def lock(self):
        self.status()
        changed = False
        for vhost in self.found_vhosts:
            vhost_protocol = self.protocols[vhost['port']]
            if self.locking_status[vhost_protocol] == False:
                click.secho('[+] Locking %s on port %s' % (self.domain, vhost['port']), fg='green')
                self._update_config_file(vhost['documentroot'],vhost_protocol,vhost['username'],vhost['domain'])
                self._generate_password_file(vhost['documentroot'],vhost_protocol,vhost['username'],vhost['domain'])
                changed = True
            else:
                click.secho('[+] Domain %s is already locked on port %s' % (self.domain, vhost['port']), fg='green')
        if changed:
            self._apply_apache_changes()
        if self.password_generated:
            click.secho('*************************************', fg='green')
            click.secho('[+] Username: %s' % vhost['username'], fg='green')
            click.secho('[+] Password: %s' % self.password, fg='green')
            click.secho('*************************************', fg='green')

    def unlock(self):
        changed = False
        for vhost in self.found_vhosts:
            vhost_protocol = self.protocols[vhost['port']]
            if self.locking_status[vhost_protocol] == True:
                click.secho('[+] Unlocking %s on port %s' % (self.domain, vhost['port']), fg='green')
                self._truncate_config_file(vhost['documentroot'],vhost_protocol,vhost['username'],vhost['domain'])
                changed = True
            else:
                click.secho('[+] Domain %s is already unlocked on port %s' % (self.domain, vhost['port']), fg='green')

        if changed:
            self._apply_apache_changes()

    def status(self):
        if any(self.locking_status.values()):
            click.secho('[+] Domain %s is LOCKED' % self.domain, fg='blue')
            if DEBUG:
                click.secho('[D] Domain %s locking status on std is %s' %(self.domain, self.locking_status.get('std', False)), fg='yellow')
                click.secho('[D] Domain %s locking status on ssl is %s' %(self.domain, self.locking_status.get('ssl', False)), fg='yellow')
        else:
            click.secho('[+] Domain %s is UNLOCKED' % self.domain, fg='green')
            if DEBUG:
                click.secho('[D] Domain %s locking status on std is %s' %(self.domain, self.locking_status.get('std', False)), fg='yellow')
                click.secho('[D] Domain %s locking status on ssl is %s' %(self.domain, self.locking_status.get('ssl', False)), fg='yellow')
        # click.echo('[+] Status of %s locking is %s' % (self.domain, self.locking_status))
    def whitelist(self):
        # Validate the provided string is a valid IP address
        if self._validate_ip_address(self.ip_address):
            changed = False
            # Invoke _whitelist_ip function on Locked domains only
            for vhost in self.found_vhosts:
                vhost_protocol = self.protocols[vhost['port']]
                if self.locking_status[vhost_protocol] == True:
                    click.secho('[+] Whitelisting %s for %s on port %s' % (self.ip_address, self.domain, vhost['port']), fg='green')
                    self._whitelist_ip(vhost['documentroot'],vhost_protocol,vhost['username'],vhost['domain'],self.ip_address)
                    changed = True
                else:
                    click.secho('[+] Domain %s is unlocked on port %s, cannot whitelist IP address for unlocked domain' % (self.domain, vhost['port']), fg='green')
            if changed:
                self._apply_apache_changes()
        else:
            click.secho("[!] Provided string '%s' is invalid IP Address" % self.ip_address, fg='red')


if __name__ == '__main__':
    main()
