#!/usr/bin/python

import click
import re
import os.path
from jinja2 import Template
import subprocess
import random
import string
import socket
import sys

@click.group()
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
        self.parsed_vhosts = self._parse_apache_config()
        self.found_vhosts = self._find_vhosts_for_domain()
        self.locking_status = self._check_status()

    def _find_vhosts_for_domain(self):
        """ Function to extract vhost informatino from parsed apache config file """
        
        domain = self.domain
        vhosts = self.parsed_vhosts
        found_vhosts = []
        for vhost in vhosts:
            if vhost['domain'] == domain:
                found_vhosts.append(vhost)
        if not found_vhosts:
            click.secho("[!] Domain %s is not found in apache config... exiting!" % domain, fg='red')
            sys.exit(1)
        return found_vhosts

    def _parse_apache_config(self):
        """ Function to read file '/etc/apache2/conf/httpd.d' and parse virtual hosts sections to extract fields """

        try:
            f = open("/etc/apache2/conf/httpd.conf", 'r')
            data_all = f.readlines()
            f.close()
        except:
            click.secho('[!] Unable to read apache config file /etc/apache2/conf/httpd.conf...exiting', fg='red')
            sys.exit(1)

        data = filter( lambda i: re.search('^((?!#).)*$', i), data_all)

        ID = 0
        enable = False

        result = {}
        vhost = []
        while len(data) > 0:
            out = data.pop(0)

            # start of VirtualHost
            if "<VirtualHost" in out:
                if not '*' in out and not '::' in out:
                    ip_port = out.split()[1]
                    ip, port = ip_port.split(':')
                    port = port.replace('>', '')
                else:
                    ip = '*'
                    port = '*'
                vhost.append(ip)
                vhost.append(port)
                enable = True
                continue

            if "</VirtualHost>" in out:
                result[ID] = vhost
                ID+=1
                enable = False
                vhost = []
                continue
                    
            if enable:
                vhost.append(out)
                continue
        parsed_vhosts = []
        for i in result:
            # result[i][0] is an IP
            # result[i][1] is a port
            # another list items are lines in vhost, grep them all
            for line in result[i]:
                if "ServerName" in line:
                    servername = line.split()[1]
                    continue
                if "DocumentRoot" in line:
                    documentroot = line.split()[1]
                    username = documentroot.split('/')[2]
                    continue
            port = result[i][1]
            parsed_vhosts.append({'domain': servername, 'port': port, 'username': username, 'documentroot': documentroot})
        return parsed_vhosts

    def _check_status(self):
        """ Function to check if there is a bolt.con file under the respective domain user data and then check if the file has the string 'Reuire valid-user' in it """
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
                    f = open(file, 'r')
                    data_all = f.readlines()
                    f.close()
                    data = filter( lambda i: re.search('^((?!#).)*$', i), data_all)
                    locked[protocol] = False
                    while len(data) > 0:
                        out = data.pop(0)
                        if 'Require valid-user' in out:
                            locked[protocol] = True
                            continue
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
        """ Function to run rebuild http config command """
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
        for vhost in self.found_vhosts:
            vhost_protocol = self.protocols[vhost['port']]
            if self.locking_status[vhost_protocol] == False:
                click.secho('[+] Locking %s on port %s' % (self.domain, vhost['port']), fg='green')
                self._update_config_file(vhost['documentroot'],vhost_protocol,vhost['username'],vhost['domain'])
                self._generate_password_file(vhost['documentroot'],vhost_protocol,vhost['username'],vhost['domain'])
                self._rebuild_httpd_config()
                self._reload_apache()
            else:
                click.secho('[+] Domain %s is already locked on port %s' % (self.domain, vhost['port']), fg='green')
        if self.password_generated:
            click.secho('*************************************', fg='green')
            click.secho('[+] Username: %s' % vhost['username'], fg='green')
            click.secho('[+] Password: %s' % self.password, fg='green')
            click.secho('*************************************', fg='green')

    def unlock(self):
        for vhost in self.found_vhosts:
            vhost_protocol = self.protocols[vhost['port']]
            if self.locking_status[vhost_protocol] == True:
                click.secho('[+] Unlocking %s on port %s' % (self.domain, vhost['port']), fg='green')
                self._truncate_config_file(vhost['documentroot'],vhost_protocol,vhost['username'],vhost['domain'])
                self._rebuild_httpd_config()
                self._reload_apache()
            else:
                click.secho('[+] Domain %s is already unlocked on port %s' % (self.domain, vhost['port']), fg='green')

    def status(self):
        if self.locking_status['std'] or self.locking_status['ssl']:
            click.secho('[+] Domain %s is LOCKED' % self.domain, fg='blue')
            if DEBUG:
                click.secho('[D] Domain %s locking status on std is %s' %(self.domain, self.locking_status['std']), fg='yellow')
                click.secho('[D] Domain %s locking status on ssl is %s' %(self.domain, self.locking_status['ssl']), fg='yellow')
        else:
            click.secho('[+] Domain %s is UNLOCKED' % self.domain, fg='green')
            if DEBUG:
                click.secho('[D] Domain %s locking status on std is %s' %(self.domain, self.locking_status['std']), fg='yellow')
                click.secho('[D] Domain %s locking status on ssl is %s' %(self.domain, self.locking_status['ssl']), fg='yellow')            
        # click.echo('[+] Status of %s locking is %s' % (self.domain, self.locking_status))
    def whitelist(self):
        # Validate the provided string is a valid IP address
        if self._validate_ip_address(self.ip_address):
            # Invoke _whitelist_ip function on Locked domains only
            for vhost in self.found_vhosts:
                vhost_protocol = self.protocols[vhost['port']]
                if self.locking_status[vhost_protocol] == True:
                    click.secho('[+] Whitelisting %s for %s on port %s' % (self.ip_address, self.domain, vhost['port']), fg='green')
                    self._whitelist_ip(vhost['documentroot'],vhost_protocol,vhost['username'],vhost['domain'],self.ip_address)
                    self._rebuild_httpd_config()
                    self._reload_apache()
                else:
                    click.secho('[+] Domain %s is unlocked on port %s, cannot whitelist IP address for unlocked domain' % (self.domain, vhost['port']), fg='green')
        else:
            click.secho("[!] Provided string '%s' is invalid IP Address" % self.ip_address, fg='red')


if __name__ == '__main__':
    main()
