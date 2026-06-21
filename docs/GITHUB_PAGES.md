# GitHub Pages documentation site

Great Generator includes a static documentation landing page at `docs/index.html`.

Recommended public URL:

https://ravikiranpagidi.github.io/great-generator/

## Enable the site

In the GitHub repository:

1. Open **Settings**.
2. Open **Pages**.
3. For **Build and deployment**, choose **Deploy from a branch**.
4. Select branch **main**.
5. Select folder **/docs**.
6. Save.

GitHub will publish the site after the next Pages build.

## What the page is for

The page is a demo-friendly front door for users who want to understand:

- what Great Generator is
- when to use it
- how to install it
- how Pandas and Spark usage differ
- how DataFrame-first output works
- how cloud paths work in Spark environments
- how to find deeper repository documentation

## Maintenance notes

- Keep `docs/index.html` focused on the first user journey.
- Keep deeper technical details in markdown files under `docs/` and the GitHub Wiki.
- Avoid untested performance claims. Use environment-dependent scale language for large datasets.
- Update the Documentation URL in `pyproject.toml` when preparing a future PyPI release.
