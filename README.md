# Conda rich

This is a plugin for overriding certain elements of the conda CLI with components
from the rich library. To install and configure run the following commands:

```
conda install -c conda-forge conda-rich
conda config --set console rich
```

> [!TIP]
> You must be using conda at version 24.11 or higher to access this feature.

This plugin currently overrides the following display components:

- Loading spinner
- Download progress bars
- Confirmation dialogs
- The `conda info` display

This plugin also serves as a demonstration of how to use the "reporter backend"
plugin hook.
