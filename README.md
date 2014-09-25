# Redirects for the IT Services web migration

This repo contains `.htaccess` files for redirects to be implemented on:

* http://www.oucs.ox.ac.uk/
* http://www.it.ox.ac.uk/
* http://www.ict.ox.ac.uk/
* http://www.admin.ox.ac.uk/bsp/

## Testing

In the root of the repository is a `simulate.py` script that can be used to
test the redirects in the `.htaccess` files. You feed it an Apache log, and it
works out the new target URL for each request, and then checks whether there'll
be something there once the migrations have happened.

The script takes a log on `stdin`, and takes a path to the `.htaccess` file and the base URL as arguments. The result on `stdout` is a multi-whitespace-delimited file containing the expected result of each request, the original path, and the expected target of the redirect.

To use it for `www.oucs.ox.ac.uk`:

    $ zcat www-oucs.access.log.gz | python simulate.py www.oucs.ox.ac.uk/.htaccess http://www.oucs.ox.ac.uk/

To use it for `www.it.ox.ac.uk`:

    $ zcat www.it-access.log.gz | python simulate.py www.it.ox.ac.uk/.htaccess http://www.it.ox.ac.uk/ 5 6

(The `5 6` specifies the field numbers for the request and status codes field in the log -- the logs for www.it.ox.ac.uk don't use the default Apache log fields.)

You might then want to use `sort -k1.13` to sort by original path.

