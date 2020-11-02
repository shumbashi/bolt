# Bolt 

Bolt is a command-line tool to help WHM system administrators quickly protect (lock) and un-protect (unlock) a Website public_html directory.

Bolt works by creating the necessary Apache config files and placing them in apache userdata folders, this includes generating a random password and reloading apache service. Placing those files outside the user ccount prevents the user from unlocking the website on his own.

Bolt also allows you to whitelist an IP address to be allowed to access a protected website without password authentication.

Developed by: [Libyan Spider](https://libyanspider.com)
License:Apache License Version 2.0
