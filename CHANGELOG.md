# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

Unreleased Changes
------------------

<!-- insertion marker -->
- Swap out `sh` for `subprocess` module for running pandoc
- Strip extra divs that appear in output

[0.2.0] - 2021-01-06
--------------------
- Initial structure
- Initial CLI structure in place
- Added moin wiki user parser
- Added moin revision parser
- Added basic git fast-import data output - outputs moin markup
- Added fetch cache and initial macro handling
- Directly commit into a new git instance
- Split the wiki translator out into a separate module
- Rebuild the translator to use pandoc on a preprocessed html fragment
- Add a synthetic home page to generated wiki
- Add some docs
