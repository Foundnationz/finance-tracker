# Original Google Colab Prototype

This folder contains the original Google Colab implementation of this
project, developed before this GitHub repository was established.

## Authorship

Farrel implemented this original codebase, including its database setup
and application functionality. See the main project
[README's Authors and Contributions section](../../README.md#-authors-and-contributions)
for full attribution.

## Status

This notebook is retained for historical reference. It is not the
maintained application and is not kept functionally up to date.

The current desktop application is described in the main
[README.md](../../README.md) and the
[Post-Submission Desktop Implementation Update](../desktop-implementation-update.md).

## Publication Preparation

Before publication, this copy was:

- Cleared of saved cell outputs and execution counts.
- Cleared of saved widget state and notebook/cell metadata, apart from
  `kernelspec` and `language_info`.
- Reviewed for personal or identifying information in its source and
  Markdown cells.
- Adjusted so it does not automatically mount cloud storage, open a
  database, start the interface, or run its user-management examples.

Cell source code was not functionally rewritten during this review.

## Known Historical Limitations

This prototype predates several improvements made in the current
desktop application. In particular:

- Passwords were stored in plain text rather than hashed.
- Email validation only accepted Gmail addresses.
- Several destructive actions had limited confirmation safeguards.
- Scheduling, duplicate protection, and budget-period handling differ
  from the current desktop implementation.

Do not use this notebook's authentication approach as a security
reference.

## Running This Notebook

This copy's automatic startup and cloud-storage connection are
intentionally disabled.

To run it for historical review:

1. Upload it to Google Colab, or run it with a compatible local
   Jupyter environment that provides `ipywidgets` support.
2. Configure a separate, disposable database location.
3. Manually uncomment the startup lines if you intend to run the
   interface.
4. Do not connect it to the current desktop application's database.
5. Do not use real financial information.