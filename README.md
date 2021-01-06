# MoinMoin To Git (Markdown) Wiki Converter

App to convert a MoinMoin wiki file tree into a git based wiki as used on
github, gitlab or gitea.

## Current Version

Version: `0.2.0`

## Translation Method

Originally the intention was to translate purely by converting the MoinMoin
markup to markdown markup - using the MoinMoin data retrieved from the
filesystem.

However, although it makes determining the overall page list and revision list
much easier, it was found that translating the wiki markup at this level was
too complex and fragile for this to work without a huge amount of special
casing.

So, after the revision structure is derived from the filesystem, each page
revision is retrieved by http requests to the running MoinMoin wiki.  This is
then reduced to just the page content (by picking out the content div from the
html), and some light editing applied to simplify the HTML - specifically:-

- Remove the anchor spans that MoinMoin adds - these add no visual or
  readable content, but confuse the translator
- Remove paragraph entries with CSS classes that start `line` - these
  again appear to be for non-required purposes (likely for showing diffs
  between revisions) - and they break the translator
- Fix links that point within the wiki - if the target does not exist
  then the text is left but the link removed.
- Strips CSS classes off links - again these upset the translator
- Translate any images that appear to be MoinMoin emoji characters (which
  are rendered as images) into gollum emoji characters

This simplified HTML is then passed through the pandoc command:-

    pandoc -f html -t gfm

And the resulting Github flavoured Markdown is taken as the new form.

This handles the vast majority of normal markup correctly, including lists and
many types of tables.  Some complicated markup or complex tables end up being
passed through as HTML - which displays correctly but is less easy to parse
and edit.

## Issues

The overall process is not particularly fast.  But this should be something
you only do once (or a few attempts) so raw speed is not needed.

## Installation

I have not at this point made this available as a pypi package, although there
should be a package file in the releases set on github.

However it can be installed from the repo - it uses
[`poetry`](https://python-poetry.org/) to manage dependancies etc, so the best
way to make use of this is to install [`poetry`](https://python-poetry.org/)
for your python version and then:-

    poetry install

the command can then be run as

    poetry run moin2gitwiki ...



----
