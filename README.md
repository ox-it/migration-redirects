# Redirects for the IT Services web migration

This repo contains `.htaccess` files for redirects to be implemented on:

* http://www.oucs.ox.ac.uk/
* http://www.it.ox.ac.uk/
* http://www.ict.ox.ac.uk/
* ~~http://www.admin.ox.ac.uk/bsp/~~ (these have been implemented separately)

## Testing

[Note: these tests no longer work for www.oucs as the rewrites are far more complicated than it can handle.]

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

## www.oucs.ox.ac.uk redirects explained

The OUCS website redirects are rather convoluted. They start with a basic redirect for the homepage. Next we have some simple rewrites pulled from the original www.oucs `.htaccess`; these are applied to mirror the pre-existing behaviour of the OUCS website.

After that, we apply some redirects that need to happen before any generic path normalization happens. These include the ITLP course redirects (otherwise they'll get `/` and then `/index` appended) and the `/shared/` and `/teip4/` stuff which still exists on active.oucs and can be redirected en masse.

After that we reverse-proxy the WW1Lit site (again, before normalizations). We also make sure that misspellings of 'one' and 'ell' in the midddle are suitably redirected.

### Normalizing paths

The first step in normalizing is to handle the fragment IDs in the OUCS URLs.
These were used to produce pages that contained portions of the original pages.

The fragments were either passed as query parameters (e.g. `index.xml?ID=foo`)
or strings on the end of the path (e.g. `index.xml.ID=foo`).

For each of these cases, we strip it off and stash it in an environment
variable called `ID`. We can then append it as a proper fragment later:

    # Remove the ID and put it in an environment variable either as a query string ...
    RewriteCond %{QUERY_STRING} ID=(body.1_)?(.*)
    RewriteRule (.*) $1? [DPI,E=ID:%2]
    #   ... or as a part of the path
    RewriteRule ^(.+)\.xml.ID=(body.1_)?(.+)$ $1.xml [DPI,E=ID:$3]

Next, we append missing trailing slashes when the path looks like a directory
(i.e. when the last component doesn't contain a `.`):

    RewriteRule ^(.*/)?([^./]+)$ $1$2/ [DPI]

Then remove `index.xml` from the end if it's there:

    RewriteRule ^(.+)/index\.xml$ $1/ [DPI]

And finally, de-duplicate doubled spaces:

    RewriteRule ^(.+)//(.*) $1/$2 [DPI]

At this stage we have a load of normalized URLs on which to do the bulk of the
rewrites. Some are copied mostly verbatim from the original `.htaccess` files,
whereas others are required to handle content that ended up on the discovery
and engagement (D&E) site.

Finally, we have the generic rules for things that redirect to the help site.
Anything ending in `.xml` is rewritten to remove the extension, and anything
with a trailing slash has `index` appended again. Both of these rules set an
environment variable to signal that the final redirect to the help site should
happen:

    # Catch-alls for the help site
    RewriteRule ^(.+)\.xml$ http://help.it.ox.ac.uk/$1 [E=TOHELPSITE:Y]
    RewriteRule ^(.+)/$ http://help.it.ox.ac.uk/$1/index [E=TOHELPSITE:Y]

Before it does, we pull the fragment ID out of the `ID` variable and append it
after a hash:

    # Append the fragment if we picked one up from earlier
    RewriteCond %{ENV:ID} (.+)
    RewriteRule (.*) $1#%1 [NE]

Finally, we redirect to the help site, using the `TOHELPSITE` environment
variable as a condition:

    RewriteCond %{ENV:TOHELPSITE} ^Y$
    RewriteRule .* - [R=307,L]

### Images and documents

These are handled at the very bottom of the `.htaccess` file in a particularly
untidy way.

